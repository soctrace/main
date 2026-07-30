from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.ask import ask_soctrace
from app.core.config import get_settings
from app.main import app
from app.schemas.ask import AskRequest, AskResponse
from app.ask.service import get_ask_soctrace_service
from app.services.orchestrator.methodology_interceptor import methodology_interceptor


class AskSpy:
    def __init__(self) -> None:
        self.payloads: list[AskRequest] = []
        self.response = AskResponse(
            answer="Respuesta analítica existente",
            resultType="entity_list",
            conversation_id="ask-conversation",
            session_id="ask-conversation",
        )

    def ask(self, payload: AskRequest) -> AskResponse:
        self.payloads.append(payload)
        return self.response


def settings(enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(enable_methodology_explanation_layer=enabled)


def request(question: str, conversation_id: str = "ask-conversation") -> AskRequest:
    return AskRequest(
        question=question,
        conversationId=conversation_id,
        session_id=conversation_id,
        activeMunicipality="29070",
        activeYear=2025,
        activeLayer="population",
        selectedSectionId="2907001010",
    )


@pytest.mark.parametrize(
    "question",
    [
        "¿Cómo se calcula la densidad de población?",
        "¿Qué sección tiene mayor densidad en 2025?",
    ],
)
def test_flag_off_preserves_existing_ask_flow(monkeypatch, question):
    def unexpected_interception(_payload):
        raise AssertionError("Capability 01 must not run while disabled")

    monkeypatch.setattr(methodology_interceptor, "try_handle", unexpected_interception)
    spy = AskSpy()
    payload = request(question)

    response = ask_soctrace(payload, service=spy, settings=settings(False))

    assert spy.payloads == [payload]
    assert response is spy.response


@pytest.mark.parametrize(
    "question",
    [
        "¿Cómo se calcula la densidad de población?",
        "¿Qué significa renta media por hogar?",
        "¿Cómo se obtiene la edad media?",
        "¿Qué es la participación electoral?",
        "¿Cómo se calcula el margen entre partidos?",
        "¿Qué significa huella construida?",
    ],
)
def test_flag_on_returns_ask_contract_without_analytical_service(question):
    spy = AskSpy()
    payload = request(question)

    response = ask_soctrace(payload, service=spy, settings=settings(True))

    assert spy.payloads == []
    assert isinstance(response, AskResponse)
    assert response.answer
    assert response.resultType == "methodology"
    assert response.conversation_id == payload.conversationId
    assert response.session_id == payload.session_id
    assert response.entities == []
    assert response.sources == []
    assert response.table is None and response.chartSpec is None
    assert response.data == {"methodology": True, "evidence": []}
    assert "no se consultaron datos" in (response.methodology or "").lower()
    assert "sql" in (response.methodology or "").lower()
    assert "modelos de lenguaje" in (response.methodology or "").lower()


@pytest.mark.parametrize(
    "question",
    [
        "¿Qué sección tiene mayor densidad en 2025?",
        "¿Cuál fue el partido ganador en la sección 18?",
        "Compara la renta de las secciones 10 y 23.",
        "¿Cómo ha evolucionado la participación desde 2019?",
    ],
)
def test_flag_on_delegates_analytical_questions_once_unchanged(question):
    spy = AskSpy()
    payload = request(question)

    response = ask_soctrace(payload, service=spy, settings=settings(True))

    assert spy.payloads == [payload]
    assert response is spy.response


def test_analytical_flow_is_equivalent_with_flag_off_and_on():
    payload = request("¿Qué sección tiene mayor densidad en 2025?")
    disabled_spy = AskSpy()
    enabled_spy = AskSpy()

    disabled = ask_soctrace(payload, service=disabled_spy, settings=settings(False))
    enabled = ask_soctrace(payload, service=enabled_spy, settings=settings(True))

    assert disabled_spy.payloads == [payload]
    assert enabled_spy.payloads == [payload]
    assert disabled is disabled_spy.response
    assert enabled is enabled_spy.response
    assert disabled.model_dump() == enabled.model_dump()


def test_interceptor_error_logs_safely_and_falls_back(monkeypatch, caplog):
    def fail(_payload):
        raise RuntimeError("controlled interceptor failure")

    monkeypatch.setattr(methodology_interceptor, "try_handle", fail)
    spy = AskSpy()
    payload = request("¿Cómo se calcula la densidad de población?")

    with caplog.at_level("ERROR"):
        response = ask_soctrace(payload, service=spy, settings=settings(True))

    assert spy.payloads == [payload]
    assert response is spy.response
    assert "methodology_interception_failed" in caplog.text
    assert payload.question not in caplog.text


def test_frontend_payload_contract_is_accepted_over_http():
    spy = AskSpy()
    app.dependency_overrides[get_ask_soctrace_service] = lambda: spy
    app.dependency_overrides[get_settings] = lambda: settings(True)
    try:
        response = TestClient(app).post(
            "/api/v1/ask",
            json={
                "question": "¿Cómo se calcula la densidad de población?",
                "sessionId": "frontend-session",
                "conversationId": "frontend-conversation",
                "session_id": "frontend-session",
                "conversation_id": "frontend-conversation",
                "activeMunicipality": "29070",
                "activeYear": 2025,
                "activeLayer": "population",
                "selectedSectionId": "2907001010",
            },
        )
    finally:
        app.dependency_overrides.pop(get_ask_soctrace_service, None)
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    body = response.json()
    assert body["resultType"] == "methodology"
    assert body["conversation_id"] == "frontend-conversation"
    assert body["session_id"] == "frontend-session"
    assert spy.payloads == []


def test_frontend_message_and_snake_case_aliases_are_accepted_over_http():
    spy = AskSpy()
    app.dependency_overrides[get_ask_soctrace_service] = lambda: spy
    app.dependency_overrides[get_settings] = lambda: settings(True)
    try:
        response = TestClient(app).post(
            "/api/v1/ask",
            json={
                "message": "¿Qué significa renta media por hogar?",
                "session_id": "snake-session",
                "active_municipality": "29070",
                "active_year": 2025,
                "active_layer": "income",
                "selected_section_id": "2907001010",
            },
        )
    finally:
        app.dependency_overrides.pop(get_ask_soctrace_service, None)
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 200
    body = response.json()
    assert body["resultType"] == "methodology"
    assert body["conversation_id"] == "snake-session"
    assert body["session_id"] == "snake-session"
    assert spy.payloads == []
