import unittest

from app.ask.answer_guard import AnswerGuard
from app.ask.conversation import conversation_store
from app.ask.conversation.follow_up_resolver import FollowUpResolver
from app.ask.llm.complexity_router import ComplexityRouter
from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import LLMPlanResponse, LLMToolCall, LLMSynthesisResponse
from app.ask.planner_loop import AskPlannerLoop
from app.ask.tools_v2.registry import TOOL_CLASSES
from app.ask.tools_v2.schemas import ToolResult
from app.core.config import Settings


class FakeGeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, plan_responses, synthesis_responses=None):
        self.plan_responses = list(plan_responses)
        self.synthesis_responses = list(synthesis_responses or [])
        self.plan_calls = []
        self.synthesis_calls = []

    async def plan(self, request):
        self.plan_calls.append(request)
        if not self.plan_responses:
            return LLMPlanResponse(provider="gemini", model="fake-model", tool_call=None, confidence="low")
        response = self.plan_responses.pop(0)
        if response is None:
            return LLMPlanResponse(provider="gemini", model="fake-model", tool_call=None, confidence="low")
        return response

    async def synthesize(self, request):
        self.synthesis_calls.append(request)
        if self.synthesis_responses:
            return self.synthesis_responses.pop(0)
        rows = request.tool_result.get("rows") or []
        section = rows[0].get("section_name") if rows else "el resultado"
        value = rows[0].get("value") if rows else None
        return LLMSynthesisResponse(
            provider="gemini",
            model="fake-model",
            answer=f"El resultado principal es {section}, con valor {value}.",
            suggested_followups=["¿Y en porcentaje?"],
        )

    def healthcheck(self):
        return {"provider": "gemini", "configured": True, "models": {}}


class FakeRegistry:
    def get(self, name):
        tool_class = TOOL_CLASSES.get(name)
        if tool_class is None:
            return None
        return type(
            "ToolRef",
            (),
            {
                "name": tool_class.name,
                "status": getattr(tool_class, "status", "supported"),
                "input_schema": tool_class.input_schema,
            },
        )()


class FakeExecutor:
    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def execute(self, tool_name, arguments, context=None):
        self.calls.append((tool_name, arguments, context))
        if tool_name in self.results:
            return self.results[tool_name]
        return ToolResult(
            tool_name=tool_name,
            operation=tool_name,
            status="ok",
            rows=[
                {
                    "section_id": "2907001001",
                    "section_name": "Sección 1",
                    "value": 1234,
                    "value_label": "habitantes",
                    "year": 2025,
                }
            ],
            summary={"value_label": "habitantes"},
            metadata={"year": 2025},
            chart_spec={"type": "bar", "rows": []},
            methodology_plain="Metodología de prueba.",
            suggested_followups=["¿Y en 2023?"],
        )


def plan(tool_name, arguments):
    return LLMPlanResponse(
        provider="gemini",
        model="fake-model",
        tool_call=LLMToolCall(tool_name=tool_name, arguments=arguments),
        confidence="medium",
    )


class GeminiPlannerLoopTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        conversation_store._states.clear()

    def loop(self, provider, executor=None):
        return AskPlannerLoop(
            provider=provider,
            complexity_router=ComplexityRouter(),
            tool_registry=FakeRegistry(),
            tool_executor=executor or FakeExecutor(),
            follow_up_resolver=FollowUpResolver(),
            answer_guard=AnswerGuard(),
            settings=Settings(ask_use_llm_planner=True, ask_llm_max_planning_attempts=2),
        )

    async def test_simple_planning_executes_tool_and_updates_memory(self):
        provider = FakeGeminiProvider([
            plan("rank_sections", {"metric": "population_total", "order": "desc", "limit": 1})
        ])
        loop = self.loop(provider)

        response = await loop.run("¿Cuál es la sección con mayor población?", "conv-1")

        self.assertIn("Sección 1", response.answer)
        self.assertEqual(response.data["tool"], "rank_sections")
        state = conversation_store.get("conv-1")
        self.assertEqual(state.last_tool_name, "rank_sections")
        self.assertEqual(state.lastMetric, "population_total")
        self.assertEqual(state.lastAnswerContext.provider, "gemini")

    async def test_no_tool_call_for_numeric_question_retries_and_returns_none(self):
        provider = FakeGeminiProvider([None, None])
        loop = self.loop(provider)

        response = await loop.run("¿Cuál es la sección con mayor población?", "conv-2")

        self.assertIsNone(response)
        self.assertEqual(len(provider.plan_calls), 2)
        self.assertEqual(len(provider.synthesis_calls), 0)

    async def test_invalid_tool_name_falls_back_without_crash(self):
        provider = FakeGeminiProvider([plan("unknown_tool", {})])
        loop = self.loop(provider)

        response = await loop.run("¿Cuál es la sección con mayor población?", "conv-3")

        self.assertIsNone(response)

    async def test_invalid_arguments_fail_validation_and_fallback(self):
        provider = FakeGeminiProvider([plan("rank_sections", {"order": "desc"})])
        loop = self.loop(provider)

        response = await loop.run("¿Cuál es la sección con mayor población?", "conv-4")

        self.assertIsNone(response)

    async def test_tool_result_empty_returns_clean_empty_response(self):
        empty = ToolResult(tool_name="rank_sections", operation="rank_sections", status="empty")
        provider = FakeGeminiProvider([plan("rank_sections", {"metric": "population_total", "order": "desc", "limit": 1})])
        loop = self.loop(provider, FakeExecutor({"rank_sections": empty}))

        response = await loop.run("¿Cuál es la sección con mayor población?", "conv-5")

        self.assertIn("no hay datos", response.answer.lower())
        self.assertEqual(len(provider.synthesis_calls), 0)

    async def test_synthesis_contradiction_uses_deterministic_renderer(self):
        provider = FakeGeminiProvider(
            [plan("rank_sections", {"metric": "population_total", "order": "desc", "limit": 1})],
            [LLMSynthesisResponse(provider="gemini", model="fake-model", answer="La primera es Otra Sección, con valor 9999.")],
        )
        loop = self.loop(provider)

        response = await loop.run("¿Cuál es la sección con mayor población?", "conv-6")

        self.assertIn("Sección 1", response.answer)
        self.assertNotIn("Otra Sección", response.answer)

    async def test_followup_resolver_avoids_gemini_call(self):
        provider = FakeGeminiProvider([
            plan("rank_sections", {"metric": "population_total", "order": "desc", "limit": 1})
        ])
        loop = self.loop(provider)
        await loop.run("¿Cuál es la sección con mayor población?", "conv-7")

        followup = await loop.run("¿Son datos de 2025?", "conv-7")

        self.assertIn("Sí", followup.answer)
        self.assertEqual(len(provider.plan_calls), 1)

    async def test_persistent_winner_tool_called(self):
        provider = FakeGeminiProvider([plan("persistent_winner", {"party": "PP", "limit": 20})])
        loop = self.loop(provider)

        response = await loop.run("¿Dónde gana siempre el PP?", "conv-8")

        self.assertEqual(response.data["tool"], "persistent_winner")
        self.assertEqual(response.data["tool_args"]["party"], "PP")

    async def test_age_cohort_projection_tool_called(self):
        provider = FakeGeminiProvider([
            plan(
                "age_cohort_projection",
                {"source_year": 2025, "source_age": 16, "target_year": 2027, "target_age": 18},
            )
        ])
        loop = self.loop(provider)

        response = await loop.run("¿Cuántas personas tendrán 18 años en 2027?", "conv-9")

        self.assertEqual(response.data["tool"], "age_cohort_projection")
        self.assertEqual(response.data["tool_args"]["target_age"], 18)


if __name__ == "__main__":
    unittest.main()
