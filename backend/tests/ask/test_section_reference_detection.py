import logging

import pytest

from app.ask.section_reference import detect_section_references
from app.schemas.ask import AskRequest
from app.services.local_analyst_service import extract_section_hint


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("sección 18", "18"),
        ("Sección 18", "18"),
        ("SECCIÓN 18", "18"),
        ("sec 18", "18"),
        ("s18", "18"),
        ("18", "18"),
        ("sección nº18", "18"),
        ("la sección 18", "18"),
        ("sección 7", "7"),
        ("sección 37", "37"),
        ("¿Cuál ganó en la sección 23?", "23"),
    ],
)
def test_detects_supported_single_section_forms(query: str, expected: str) -> None:
    detection = detect_section_references(query)

    assert detection.section_ids == (expected,)
    assert detection.selected_section_id == expected
    assert detection.confidence == 1.0
    assert detection.entities == ({"type": "section", "id": expected},)


@pytest.mark.parametrize("section_number", range(1, 38))
def test_accepts_all_supported_section_numbers(section_number: int) -> None:
    detection = detect_section_references(f"sección {section_number}")

    assert detection.selected_section_id == str(section_number)


def test_marks_multiple_sections_without_resolving_them() -> None:
    detection = detect_section_references("Compara las secciones 10 y 23")

    assert detection.section_ids == ("10", "23")
    assert detection.selected_section_id is None
    assert detection.entities == (
        {"type": "section", "id": "10"},
        {"type": "section", "id": "23"},
    )


def test_query_without_section_does_not_change_request_context() -> None:
    request = AskRequest(question="¿Qué partido obtuvo más votos en Mijas?")

    assert request.selectedSectionId is None
    assert request.selected_section_id is None


def test_single_section_reaches_pipeline_context(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.schemas.ask"):
        request = AskRequest(question="¿Cuál fue el partido ganador en la sección 18?")

    assert request.selectedSectionId == "18"
    assert request.selected_section_id == "18"
    assert "selected_section_id=18" in caplog.text
    assert "confidence=1.00" in caplog.text


@pytest.mark.parametrize("query", ["sec 18", "s18", "sección nº18", "18"])
def test_existing_analyst_entrypoint_uses_shared_detection(query: str) -> None:
    assert extract_section_hint(query) == "18"


def test_explicit_api_context_is_not_overwritten() -> None:
    request = AskRequest(
        question="¿Cuál fue el partido ganador en la sección 18?",
        selectedSectionId="23",
    )

    assert request.selectedSectionId == "23"
