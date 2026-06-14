from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.service import AskSocTraceService
from app.ask.tests.validation_rules import response_rows, response_tool, validate_available_response
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CATALOG = ROOT / "soctrace-web/src/features/ask-soctrace/config/askSocTraceTests.ts"
REPORT_PATH = ROOT / "docs/test_library_validation_report.md"
VALIDATED_CATALOG_PATH = ROOT / "backend/app/ask/tests/validated_test_catalog.json"
FRONTEND_VALIDATED_CATALOG_PATH = ROOT / "soctrace-web/src/features/ask-soctrace/config/validated_test_catalog.json"


@dataclass(frozen=True)
class VisibleTest:
    id: str
    category: str
    question: str
    expected_chart_type: str | None
    ui_status: str
    required_tool: str | None


def slugify(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFD", value)
    ascii_text = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return ascii_text


def load_visible_tests() -> list[VisibleTest]:
    source = FRONTEND_CATALOG.read_text(encoding="utf-8")
    previous_rows: list[dict[str, Any]] = []
    if VALIDATED_CATALOG_PATH.exists():
        previous_rows = json.loads(VALIDATED_CATALOG_PATH.read_text(encoding="utf-8"))
    previous_by_question = {str(row.get("question")): row for row in previous_rows if row.get("question")}
    block_match = re.search(r"const testsByCategory:.*?=\s*\[(.*)\];\s*function slugify", source, flags=re.DOTALL)
    if not block_match:
        raise RuntimeError("Could not locate testsByCategory in frontend catalog.")
    block = block_match.group(1)
    category_pattern = re.compile(r'\["([^"]+)",\s*\[(.*?)\]\]', re.DOTALL)
    tests: list[VisibleTest] = []
    for category, raw_items in category_pattern.findall(block):
        prompts = re.findall(r'\["([^"]+)"(?:,\s*"([^"]+)")?\]', raw_items)
        for index, (question, chart_type) in enumerate(prompts, start=1):
            previous = previous_by_question.get(question, {})
            required_tool = previous.get("selected_tool") or previous.get("required_tool")
            ui_status = previous.get("status") or "coming_soon"
            tests.append(
                VisibleTest(
                    id=f"{slugify(category)}-{index}",
                    category=category,
                    question=question,
                    expected_chart_type=chart_type or None,
                    ui_status=ui_status,
                    required_tool=required_tool,
                )
            )
    return tests


def preview(value: str, limit: int = 140) -> str:
    cleaned = " ".join((value or "").split())
    return cleaned[: limit - 1] + "…" if len(cleaned) > limit else cleaned


def markdown_escape(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def inferred_required_tool(question: str) -> str | None:
    text = question.casefold()
    if "personas entre" in text and "riviera sur" in text:
        return "section_age_range"
    if "partido domina la sección más joven" in text or "partido domina la seccion mas joven" in text:
        return "chained_youngest_section_party_dominance"
    if "partido es históricamente más fuerte en la sección más joven" in text or "partido es historicamente mas fuerte en la seccion mas joven" in text:
        return "chained_youngest_section_party_dominance"
    if "reducido más la participación" in text or "reducido mas la participacion" in text:
        return "participation_decline"
    if "cambian de partido ganador según la elección" in text or "cambian de partido ganador segun la eleccion" in text:
        return "winner_switch_by_election_type"
    if "podrían aumentar la abstención" in text or "podrian aumentar la abstencion" in text:
        return "abstention_increase_risk"
    if "perdió más apoyo" in text or "perdio mas apoyo" in text or "ganó más apoyo" in text or "gano mas apoyo" in text or "creció más vox" in text or "crecio mas vox" in text:
        return "electoral_vote_evolution"
    if "relacionan más" in text or "relacionan mas" in text or "existe relación" in text or "existe relacion" in text:
        return "correlation_analysis"
    if "siempre ha sido" in text:
        return "compare_years"
    if "combinan" in text or "combina" in text:
        if "crecimiento" not in text:
            return "cross_metric_ranking"
    if "parecen infravaloradas" in text or "oportunidad inmobiliaria" in text or "potencial de revalorización" in text or "potencial de revalorizacion" in text:
        return "cross_metric_ranking"
    if "qué partido es históricamente más fuerte allí" in text or "que partido es historicamente mas fuerte alli" in text:
        return "historical_party_average"
    if "¿y qué renta tiene?" in text or "¿y que renta tiene?" in text:
        return "section_profile"
    if "podrían cambiar de ganador" in text or "podrian cambiar de ganador" in text:
        return "__unsupported_until_forecast_tool__"
    return None


def validate_test(service: AskSocTraceService, test: VisibleTest, validated_at: str) -> dict[str, Any]:
    response = service.ask(
        AskRequest(
            question=test.question,
            activeMunicipality="29070",
            conversationId=f"test-library-{uuid4()}",
            mode="debug",
        )
    )
    tool = response_tool(response)
    rows = response_rows(response)
    expected_tool = inferred_required_tool(test.question) or test.required_tool
    passed, reason = validate_available_response(response, expected_tool=expected_tool if expected_tool and not expected_tool.startswith("__") else None)
    if passed and expected_tool and expected_tool.startswith("__"):
        passed, reason = False, "no supported executable tool for this forecast-style question"
    real_result = "passed" if passed else "failed"
    recommended = "keep_available" if passed else ("downgrade_to_coming_soon" if test.ui_status == "available" else "keep_coming_soon")
    return {
        "id": test.id,
        "category": test.category,
        "question": test.question,
        "status": "available" if passed else "coming_soon",
        "ui_status": test.ui_status,
        "required_tool": expected_tool if expected_tool and not expected_tool.startswith("__") else test.required_tool,
        "selected_tool": tool,
        "arguments": getattr(service, "_tool_inputs", [])[-1] if getattr(service, "_tool_inputs", []) else {},
        "validation_status": "passed" if passed else "failed",
        "real_result": real_result,
        "tool_result_status": "ok" if rows or response.table or response.chartSpec else "empty_or_unknown",
        "row_count": len(rows),
        "answer_preview": preview(response.answer),
        "chartSpec_status": "present" if response.chartSpec else "missing",
        "failure_reason": "passed" if passed else reason,
        "action_recommended": recommended,
        "last_validated_at": validated_at,
    }


def write_report(rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Ask SocTrace Test Library Validation Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "| Categoría | Pregunta | Estado UI | Resultado real | Tool | Motivo | Acción recomendada |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                markdown_escape(value)
                for value in (
                    row["category"],
                    row["question"],
                    "Disponible" if row["ui_status"] == "available" else "Próximamente",
                    row["real_result"],
                    row.get("selected_tool") or "",
                    row["failure_reason"],
                    row["action_recommended"],
                )
            )
            + " |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_catalog(rows: list[dict[str, Any]]) -> None:
    payload = json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
    VALIDATED_CATALOG_PATH.write_text(payload, encoding="utf-8")
    FRONTEND_VALIDATED_CATALOG_PATH.write_text(payload, encoding="utf-8")


def main() -> int:
    os.environ.setdefault("ASK_USE_LLM_PLANNER", "false")
    tests = load_visible_tests()
    validated_at = datetime.now(timezone.utc).isoformat()
    settings = get_settings()
    settings.ask_use_llm_planner = False
    rows = []
    for test in tests:
        session = SessionLocal()
        try:
            service = AskSocTraceService(session, settings)
            rows.append(validate_test(service, test, validated_at))
        finally:
            session.rollback()
            session.close()
    write_report(rows)
    write_catalog(rows)
    failed_available = [row for row in rows if row["ui_status"] == "available" and row["validation_status"] != "passed"]
    passed = sum(1 for row in rows if row["validation_status"] == "passed")
    print(f"Validated {len(rows)} visible tests: {passed} passed, {len(rows) - passed} unavailable.")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(f"Wrote {VALIDATED_CATALOG_PATH.relative_to(ROOT)}")
    print(f"Wrote {FRONTEND_VALIDATED_CATALOG_PATH.relative_to(ROOT)}")
    if failed_available:
        print("Previously visible Disponible tests now downgraded in validated catalog:")
        for row in failed_available:
            print(f"- {row['question']}: {row['failure_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
