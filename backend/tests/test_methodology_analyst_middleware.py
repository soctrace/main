import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.analyst import chat_political_analyst
from app.core.config import Settings, get_settings
from app.main import app
from app.services.analyst import get_political_analyst_agent
from app.services.analyst.schemas import AnalystChatRequest, AnalystChatResponse
from app.services.orchestrator.context_store import context_store
from app.services.orchestrator.methodology_interceptor import (
    METHODOLOGY_CATALOG,
    classify_methodology_question,
    methodology_interceptor,
)


class LegacySpy:
    def __init__(self, response=None):
        self.payloads = []
        self.response = response or AnalystChatResponse(
            answer="Legacy analytical response",
            methodology="Ranking de densidad validado.",
            confidence="high",
            data_used=["marts.agent_section_profile"],
            data_layers_used=["Population Intelligence"],
            tools_used=["get_population_ranking"],
            variables_used=["population_density"],
            conversation_id="middleware-conversation",
        )

    async def chat(self, payload):
        self.payloads.append(payload)
        self.response.conversation_id = payload.conversation_id
        return self.response


def payload(message, conversation_id="middleware-conversation"):
    return AnalystChatRequest(
        message=message,
        conversation_id=conversation_id,
        municipality_id="29070",
        context={"active_year": 2025, "selected_section_id": ""},
    )


def run_route(message, enabled, spy=None, conversation_id="middleware-conversation"):
    spy = spy or LegacySpy()
    request = payload(message, conversation_id)
    response = asyncio.run(chat_political_analyst(
        request,
        analyst=spy,
        settings=SimpleNamespace(enable_methodology_explanation_layer=enabled),
    ))
    return request, response, spy


def test_flag_off_always_calls_legacy_once_with_original_payload():
    for question in ("¿Cómo se calcula la densidad de población?", "¿Qué sección tiene mayor densidad en 2025?"):
        request, response, spy = run_route(question, False)
        assert spy.payloads == [request]
        assert response is spy.response


@pytest.mark.parametrize("question", [
    "¿Qué es la densidad de población?",
    "¿Cómo se calcula la densidad de población?",
    "¿Qué significa renta media por hogar?",
    "¿Cómo se obtiene la edad media?",
    "¿Qué es la participación electoral?",
    "¿Cómo se calcula el margen entre partidos?",
    "¿Qué significa huella construida?",
    "¿Qué es la intensidad edificatoria?",
])
def test_standalone_definitions_bypass_legacy_and_return_compatible_response(question):
    request, response, spy = run_route(question, True)
    assert spy.payloads == []
    assert isinstance(response, AnalystChatResponse)
    assert response.display_mode == "chat"
    assert response.conversation_id == request.conversation_id
    assert response.audit_id == "methodology_explanation_layer"
    assert response.data_used == [] and response.tools_used == []
    assert response.tables == [] and response.charts == [] and response.sections == []
    assert "no se consultaron datos" in response.methodology.lower()


@pytest.mark.parametrize("question", [
    "¿Qué sección tiene mayor densidad en 2025?",
    "¿Cuál fue el partido ganador en la sección 18?",
    "Compara la renta de las secciones 10 y 23.",
    "¿Dónde obtuvo el PP su mejor resultado en 2023?",
    "¿Cómo ha evolucionado la participación desde 2019?",
    "¿Por qué la sección 10 tiene más renta que la 23?",
    "¿Cómo se calcula la densidad de la sección 18 en 2025?",
])
def test_analytical_questions_use_legacy_once_unchanged(question):
    request, response, spy = run_route(question, True)
    assert spy.payloads == [request]
    assert response is spy.response


def test_followup_uses_minimal_context_without_second_legacy_call():
    conversation_id = "methodology-after-legacy"
    context_store._states.pop(conversation_id, None)
    spy = LegacySpy(response=AnalystChatResponse(
        answer="Sección 23",
        methodology="Se ordenó population_density de mayor a menor para 2025.",
        confidence="high",
        data_used=["marts.agent_section_profile"],
        data_layers_used=["Population Intelligence"],
        tools_used=["get_population_ranking"],
        variables_used=["population_density"],
        conversation_id=conversation_id,
    ))

    first_request, first_response, _ = run_route("¿Qué sección tiene mayor densidad en 2025?", True, spy, conversation_id)
    second_request, second_response, _ = run_route("¿Cómo has calculado ese resultado?", True, spy, conversation_id)

    assert len(spy.payloads) == 1 and spy.payloads[0] is first_request
    assert first_response is spy.response
    assert second_response.audit_id == "methodology_explanation_layer"
    assert second_response.tools_used == []
    assert second_response.conversation_id == second_request.conversation_id
    state = context_store.get(conversation_id)
    assert state.last_variables_used == ["population_density"]
    assert state.methodology_explanation.year == 2025
    assert "Sección 23" not in state.last_answer_summary


def test_ambiguous_followup_without_context_delegates_to_legacy():
    conversation_id = "methodology-no-context"
    context_store._states.pop(conversation_id, None)
    request, response, spy = run_route("¿Cómo has calculado eso?", True, conversation_id=conversation_id)
    assert spy.payloads == [request]
    assert response is spy.response


def test_interceptor_exception_falls_back_to_legacy(monkeypatch):
    def fail(_payload):
        raise RuntimeError("interceptor failure")

    monkeypatch.setattr(methodology_interceptor, "try_handle", fail)
    request, response, spy = run_route("¿Cómo se calcula la densidad de población?", True)
    assert spy.payloads == [request]
    assert response is spy.response


def test_legacy_equivalence_with_flag_off_and_on():
    question = "¿Qué sección de Mijas tiene mayor densidad de población en 2025?"
    request_off, response_off, spy_off = run_route(question, False)
    request_on, response_on, spy_on = run_route(question, True)
    assert spy_off.payloads == [request_off]
    assert spy_on.payloads == [request_on]
    assert request_off == request_on
    assert response_off.model_dump() == response_on.model_dump()


def test_catalog_contains_every_required_domain():
    expected = {
        "densidad de poblacion", "edad media", "poblacion menor de 30 anos", "poblacion mayor de 65 anos",
        "crecimiento de poblacion", "distribucion por sexo", "participacion electoral", "abstencion",
        "margen electoral", "partido ganador", "bloque izquierda derecha", "voto local nacional",
        "fragmentacion electoral", "ley dhondt", "renta media individual", "renta media por hogar",
        "quintiles de renta", "ocupacion", "nivel de estudios", "actividad economica", "densidad de parcelas",
        "huella construida", "parcela media", "intensidad edificatoria", "valor catastral estimado por m2",
        "precio de mercado estimado por m2", "ratio mercado catastro",
    }
    assert expected <= set(METHODOLOGY_CATALOG)


def test_detector_is_conservative_without_side_effects():
    assert classify_methodology_question("¿Cómo se calcula la densidad?").handled
    assert classify_methodology_question("¿Cómo se calcula el porcentaje de población mayor de 65 años?").handled
    assert not classify_methodology_question("¿Cómo se calcula la densidad de la sección 18 en 2025?").handled


def test_standalone_definition_generates_conversation_id_when_missing():
    request = AnalystChatRequest(message="¿Qué es la densidad de población?")
    response, classification = methodology_interceptor.try_handle(request)
    assert classification.handled
    assert response is not None and response.conversation_id


def test_http_contract_flag_on_and_off():
    try:
        for enabled in (False, True):
            spy = LegacySpy()
            app.dependency_overrides[get_political_analyst_agent] = lambda: spy
            app.dependency_overrides[get_settings] = lambda: Settings(
                _env_file=None, enable_methodology_explanation_layer=enabled, llm_provider="mock"
            )
            for question in (
                "¿Cómo se calcula la densidad de población?",
                "¿Qué sección tiene mayor densidad en 2025?",
                "¿Qué significa renta media por hogar?",
                "¿Cuál fue el partido ganador en la sección 18?",
            ):
                response = TestClient(app).post("/api/v1/analyst/chat", json={
                    "message": question, "conversation_id": "http-methodology",
                    "context": {"active_year": 2025, "selected_section_id": ""},
                })
                assert response.status_code == 200
                assert response.json()["conversation_id"] == "http-methodology"
    finally:
        app.dependency_overrides.pop(get_political_analyst_agent, None)
        app.dependency_overrides.pop(get_settings, None)
