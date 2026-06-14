from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.ask.service import AskSocTraceService
from app.ask.tests.validation_rules import forbidden_answer_reason, has_non_empty_payload, response_tool, useful_spanish_answer
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


CATALOG_PATH = Path(__file__).resolve().parents[2] / "app/ask/tests/validated_test_catalog.json"


def _available_tests() -> list[dict]:
    if not CATALOG_PATH.exists():
        return []
    return [
        row
        for row in json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if row.get("status") == "available"
    ]


def test_every_available_visible_test_executes_successfully():
    tests = _available_tests()
    assert tests, "validated_test_catalog.json must contain available tests"
    settings = get_settings()
    settings.ask_use_llm_planner = False
    failures: list[str] = []
    for item in tests:
        session = SessionLocal()
        try:
            service = AskSocTraceService(session, settings)
            response = service.ask(
                AskRequest(
                    question=item["question"],
                    activeMunicipality="29070",
                    conversationId=f"regression-{item['id']}-{uuid4()}",
                    mode="debug",
                )
            )
            expected_tool = item.get("selected_tool") or item.get("required_tool")
            actual_tool = response_tool(response)
            if expected_tool and actual_tool != expected_tool:
                failures.append(f"{item['question']}: expected {expected_tool}, got {actual_tool}")
            if reason := forbidden_answer_reason(response.answer):
                failures.append(f"{item['question']}: {reason}")
            if not useful_spanish_answer(response):
                failures.append(f"{item['question']}: answer is not useful enough")
            if not has_non_empty_payload(response):
                failures.append(f"{item['question']}: empty payload")
        finally:
            session.rollback()
            session.close()
    assert not failures, "\n".join(failures)


def test_reported_failures_are_available_and_pass():
    available_questions = {item["question"] for item in _available_tests()}
    expected = {
        "¿Qué zonas muestran mejor oportunidad inmobiliaria?",
        "¿Dónde existe mayor polarización demográfica?",
        "Ordena las secciones por edad media.",
    }
    assert expected <= available_questions
