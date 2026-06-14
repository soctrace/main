from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.ask.planning.intent_guard import GuardResult
from app.ask.tools_v2.schemas import ToolResult


class ResultAnswerabilityGuard:
    def validate(
        self,
        question: str,
        tool_name: str,
        arguments: dict[str, Any],
        tool_result: ToolResult,
    ) -> GuardResult:
        text = _normalize(question)
        reasons: list[str] = []

        if tool_result.status == "empty":
            return GuardResult(
                ok=False,
                reasons=["tool returned empty result"],
                repair_hint=self._empty_repair_hint(question, tool_name, arguments, tool_result),
            )
        if tool_result.status != "ok":
            return GuardResult(ok=False, reasons=[f"tool status is {tool_result.status}"])

        metric = arguments.get("metric") or tool_result.metadata.get("metric")
        if _asks_age_18_in_2027(text) and metric in {"participation_pct", "abstention_pct", "population_over_65"}:
            return GuardResult(
                ok=False,
                reasons=[f"wrong metric `{metric}` for age cohort question"],
                repair_hint=(
                    "El resultado no responde a la pregunta de personas que tendrán 18 años en 2027. "
                    "Replanifica con age_cohort_projection: source_year=2025, source_age=16, target_year=2027, target_age=18."
                ),
            )

        if _requires_year_metadata(text, tool_name, arguments) and not _has_any_year(tool_result):
            reasons.append("result is missing year metadata")

        if _asks_section_ranking(text):
            rows = tool_result.rows or []
            if not rows:
                reasons.append("section question returned no rows")
            elif not all(row.get("section_name") and row.get("value") is not None for row in rows[:1]):
                reasons.append("section ranking result lacks section_name/value")

        return GuardResult(ok=not reasons, reasons=reasons, repair_hint="; ".join(reasons) if reasons else None)

    def _empty_repair_hint(self, question: str, tool_name: str, arguments: dict[str, Any], tool_result: ToolResult) -> str:
        metric = arguments.get("metric") or tool_result.metadata.get("metric")
        if metric in {"abstention_pct", "participation_pct"}:
            return (
                "El resultado electoral vino vacío. Reintenta rank_sections con election_type=MUNICIPALES, "
                "sin year, usando election_year solo si el usuario lo especifica, para tomar la última elección municipal disponible."
            )
        return (
            "He entendido la consulta, pero no he encontrado datos para ese filtro concreto. "
            "Puedo probar con la última elección municipal disponible o con todas las elecciones disponibles."
        )


def _normalize(value: str) -> str:
    value = value.lower()
    value = "".join(ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn")
    return value


def _asks_age_18_in_2027(text: str) -> bool:
    return bool(re.search(r"18 anos en 2027|personas tendran 18", text))


def _requires_year_metadata(text: str, tool_name: str, arguments: dict[str, Any]) -> bool:
    if re.search(r"\b20\d{2}\b|ultimo|ultima|año|ano|eleccion|elecciones", text):
        return True
    return tool_name in {"rank_sections", "age_cohort_projection"} and bool(
        arguments.get("year") or arguments.get("source_year") or arguments.get("target_year") or arguments.get("election_year")
    )


def _has_any_year(tool_result: ToolResult) -> bool:
    keys = {"year", "start_year", "end_year", "election_year", "source_year", "target_year"}
    metadata = tool_result.metadata or {}
    if any(metadata.get(key) is not None for key in keys):
        return True
    return any(any(row.get(key) is not None for key in keys) for row in tool_result.rows or [])


def _asks_section_ranking(text: str) -> bool:
    return bool(re.search(r"en que seccion|cual es la seccion|que secciones|seccion con|donde", text))
