import asyncio

from app.ask.tools_v2 import ToolResult
from app.core.config import Settings
from app.services.orchestrator.context_store import context_store
from app.services.orchestrator.context_store import AnalyticalExplanationContext, OrchestratorConversationContext
from app.services.orchestrator.methodology_explanation import should_handle_methodology_question
from app.services.orchestrator.orchestrator import SocTraceOrchestrator
from app.services.orchestrator.response_schema import OrchestratorChatRequest
from app.ask.llm.schemas import LLMToolCall


class DummySession:
    pass


class CountingExecutor:
    def __init__(self):
        self.calls = []

    async def execute(self, tool_name, arguments, context):
        self.calls.append((tool_name, arguments))
        return ToolResult(
            tool_name=tool_name,
            operation="rank_sections",
            status="ok",
            rows=[
                {"section_id": "2907001023", "section_name": "Sección 23", "year": 2025, "value": 5351, "value_label": "habitantes"},
                {"section_id": "2907001030", "section_name": "Sección 30", "year": 2025, "value": 4268, "value_label": "habitantes"},
                {"section_id": "2907001022", "section_name": "Sección 22", "year": 2025, "value": 4009, "value_label": "habitantes"},
            ],
            methodology_plain="Consulté la población validada de cada sección en 2025 y la ordené de mayor a menor.",
            sources=["validated_population_sections"],
            metadata={
                "data_layer": "Population Intelligence",
                "variables_used": ["population_total"],
                "source_view": "validated_population_sections",
            },
        )


def ask(agent, message, conversation_id):
    return asyncio.run(agent.chat(OrchestratorChatRequest(
        message=message, conversation_id=conversation_id, municipality_id="29070", context={"active_year": 2025}
    )))


def test_three_methodology_followups_reuse_previous_analysis_without_any_tool_call():
    conversation_id = "methodology-sequence"
    context_store._states.pop(conversation_id, None)
    agent = SocTraceOrchestrator(DummySession(), Settings(llm_provider="mock"))
    executor = CountingExecutor()
    agent.tool_executor = executor

    analytical = ask(agent, "¿Cuáles son las tres secciones con mayor población en 2025?", conversation_id)
    calculation = ask(agent, "How did you calculate that?", conversation_id)
    estimate = ask(agent, "Is it an estimate?", conversation_id)
    lineage = ask(agent, "What does lineage mean?", conversation_id)

    assert analytical.tools_called
    assert len(executor.calls) == 1
    assert calculation.tools_called == [] and calculation.llm_called is False
    assert "2025" in calculation.answer and "mayor a menor" in calculation.answer
    assert estimate.tools_called == [] and "estimación" in estimate.answer.lower()
    assert lineage.tools_called == [] and "relación histórica" in lineage.answer.lower()


def test_methodology_language_without_previous_analysis_continues_normal_flow():
    conversation_id = "methodology-no-history"
    context_store._states.pop(conversation_id, None)
    agent = SocTraceOrchestrator(DummySession(), Settings(llm_provider="mock"))
    executor = CountingExecutor()
    agent.tool_executor = executor

    response = ask(agent, "¿Cómo calculas la población?", conversation_id)

    assert response.methodology != "Explicación del análisis anterior a partir del contexto ya disponible."


def explanatory_context():
    return OrchestratorConversationContext(
        last_tools_used=["get_population_profile"],
        last_variables_used=["population_total"],
        last_source_views=["validated_population_sections"],
        last_answer_summary="Ranking de población de 2025",
        methodology_explanation=AnalyticalExplanationContext(
            methodology="Población validada por sección, ordenada de mayor a menor.",
            warnings=[],
        ),
    )


def test_conservative_guard_accepts_only_clear_explanations():
    context = explanatory_context()
    accepted = [
        "¿Cómo has calculado eso?",
        "¿Qué metodología has usado?",
        "¿De dónde procede el dato?",
        "¿Es una estimación?",
        "¿Por qué usaste 2025?",
        "¿Qué significa lineage?",
        "¿Qué limitaciones tiene el resultado?",
        "¿Cómo debo interpretar ese porcentaje?",
    ]
    assert all(should_handle_methodology_question(question, context) for question in accepted)


def test_conservative_guard_rejects_new_or_ambiguous_analysis():
    context = explanatory_context()
    rejected = [
        "¿Y en 2023?",
        "¿Y cuál es la menos poblada?",
        "Haz lo mismo con renta",
        "Compáralas con Riviera",
        "Recalcula el ranking",
        "Dame otra sección",
        "Ordénalas de menor a mayor",
    ]
    assert all(not should_handle_methodology_question(question, context) for question in rejected)
    assert not should_handle_methodology_question("¿Cómo has calculado eso?", None)
    assert not should_handle_methodology_question("¿Por qué?", OrchestratorConversationContext())


def test_explanation_turn_does_not_block_followup_year_analysis_or_rewrite_question():
    conversation_id = "methodology-exit-year"
    context_store._states.pop(conversation_id, None)
    agent = SocTraceOrchestrator(DummySession(), Settings(llm_provider="mock"))
    executor = CountingExecutor()
    agent.tool_executor = executor
    ask(agent, "¿Cuáles son las tres secciones con mayor población en 2025?", conversation_id)
    ask(agent, "¿Cómo has calculado eso?", conversation_id)
    received = []

    async def previous_flow(message, payload, state):
        received.append(message)
        return [LLMToolCall(tool_name="get_population_profile", arguments={
            "municipio_id": "29070", "year": 2023, "limit": 3,
        })]

    agent._select_tool_calls = previous_flow
    response = ask(agent, "¿Y en 2023?", conversation_id)

    assert received == ["¿Y en 2023?"]
    assert len(executor.calls) == 2
    assert executor.calls[-1][1]["year"] == 2023
    assert response.methodology != "Explicación del análisis anterior a partir del contexto ya disponible."


def test_explanation_turn_does_not_intercept_change_to_less_populated():
    conversation_id = "methodology-exit-metric"
    context_store._states.pop(conversation_id, None)
    agent = SocTraceOrchestrator(DummySession(), Settings(llm_provider="mock"))
    executor = CountingExecutor()
    agent.tool_executor = executor
    ask(agent, "¿Cuál es la sección más poblada?", conversation_id)
    ask(agent, "¿Cómo lo has calculado?", conversation_id)

    async def previous_flow(message, payload, state):
        return [LLMToolCall(tool_name="rank_sections", arguments={
            "municipio_id": "29070", "metric": "population_total", "order": "asc", "limit": 1,
        })]

    agent._select_tool_calls = previous_flow
    response = ask(agent, "¿Y cuál es la menos poblada?", conversation_id)

    assert not should_handle_methodology_question("¿Y cuál es la menos poblada?", context_store.get(conversation_id))
    assert response.methodology != "Explicación del análisis anterior a partir del contexto ya disponible."
