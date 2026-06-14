from __future__ import annotations

from typing import Any

from app.schemas.ask import AskResponse


FORBIDDEN_ANSWER_FRAGMENTS = (
    "no hay filas",
    "no encuentro una metrica",
    "no encuentro una métrica",
    "no encuentro una operacion",
    "no encuentro una operación",
    "falta una metrica",
    "falta una métrica",
    "semantic layer",
    "catalogo semantico",
    "catálogo semántico",
    "operacion analitica aprobada",
    "operación analítica aprobada",
    "sqlalchemy",
    "psycopg",
    "relation does not exist",
    "no he podido acceder temporalmente",
)


def response_rows(response: AskResponse) -> list[dict[str, Any]]:
    data = response.data if isinstance(response.data, dict) else {}
    rows = data.get("rows")
    return rows if isinstance(rows, list) else []


def response_tool(response: AskResponse) -> str | None:
    data = response.data if isinstance(response.data, dict) else {}
    tool = data.get("tool")
    return str(tool) if tool else None


def has_non_empty_payload(response: AskResponse) -> bool:
    if response_rows(response):
        return True
    data = response.data if isinstance(response.data, dict) else {}
    summary = data.get("summary")
    if isinstance(summary, dict) and any(value not in (None, "", [], {}) for value in summary.values()):
        return True
    if response.table and response.table.get("rows"):
        return True
    if response.chartSpec:
        rows = response.chartSpec.get("rows") if isinstance(response.chartSpec, dict) else None
        if rows or response.chartSpec.get("value") is not None:
            return True
    return bool((response.answer or "").strip()) and bool(response.methodology or response.sources)


def forbidden_answer_reason(answer: str) -> str | None:
    lowered = answer.casefold()
    for fragment in FORBIDDEN_ANSWER_FRAGMENTS:
        if fragment.casefold() in lowered:
            return f"fallback text: {fragment}"
    return None


def useful_spanish_answer(response: AskResponse) -> bool:
    answer = (response.answer or "").strip()
    if len(answer) < 60:
        return False
    spanish_markers = ("seccion", "sección", "zona", "mijas", "resultados", "interpretacion", "interpretación")
    return any(marker in answer.casefold() for marker in spanish_markers)


def validate_available_response(response: AskResponse, *, expected_tool: str | None = None) -> tuple[bool, str]:
    tool = response_tool(response)
    if expected_tool and tool and tool != expected_tool:
        return False, f"tool mismatch: expected {expected_tool}, got {tool}"
    if not tool:
        return False, "no tool selected"
    reason = forbidden_answer_reason(response.answer)
    if reason:
        return False, reason
    if not has_non_empty_payload(response):
        return False, "empty result payload"
    if not useful_spanish_answer(response):
        return False, "answer is too thin or not useful"
    if "error" in (response.confidence or "").casefold():
        return False, "technical error confidence"
    return True, "passed"

