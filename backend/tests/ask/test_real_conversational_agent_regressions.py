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


class FakeProvider(LLMProvider):
    name = "gemini"

    def __init__(self, plans):
        self.plans = list(plans)
        self.plan_calls = []
        self.synthesis_calls = []

    async def plan(self, request):
        self.plan_calls.append(request)
        if not self.plans:
            return LLMPlanResponse(provider="gemini", model="fake", tool_call=None, confidence="low")
        response = self.plans.pop(0)
        if response is None:
            return LLMPlanResponse(provider="gemini", model="fake", tool_call=None, confidence="low")
        return response

    async def synthesize(self, request):
        self.synthesis_calls.append(request)
        rows = request.tool_result.get("rows") or []
        first = rows[0] if rows else {}
        total = first.get("municipality_total")
        if total:
            answer = f"Total municipal estimado: {total}. La sección principal es {first.get('section_name')}."
        else:
            answer = f"La sección destacada es {first.get('section_name')}, con {first.get('value')}."
        return LLMSynthesisResponse(provider="gemini", model="fake", answer=answer)

    def healthcheck(self):
        return {"provider": "gemini", "configured": True}


class FakeRegistry:
    def get(self, name):
        tool_class = TOOL_CLASSES.get(name)
        if tool_class is None:
            return None
        return type(
            "ToolRef",
            (),
            {"name": tool_class.name, "status": getattr(tool_class, "status", "supported"), "input_schema": tool_class.input_schema},
        )()


class ConversationalExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, tool_name, arguments, context=None):
        self.calls.append((tool_name, arguments, context))
        if tool_name == "age_cohort_projection":
            return ToolResult(
                tool_name=tool_name,
                operation=tool_name,
                status="ok",
                rows=[
                    {
                        "section_id": "2907001023",
                        "section_name": "Sección 23 · Riviera Sur",
                        "value": 110,
                        "value_label": "personas",
                        "municipality_total": 740,
                        "source_year": arguments.get("source_year"),
                        "target_year": arguments.get("target_year"),
                        "year": arguments.get("source_year"),
                    }
                ],
                summary={"value_label": "personas", "municipality_total": 740},
                metadata={"metric": "population_total", "source_year": arguments.get("source_year"), "target_year": arguments.get("target_year")},
                methodology_plain="Estimación por cohorte de edad.",
            )
        if tool_name == "ecological_vote_profile_by_age_group":
            return ToolResult(
                tool_name=tool_name,
                operation=tool_name,
                status="ok",
                rows=[{"party": "PP", "weighted_vote_pct": 42.1, "election_year": 2023, "value": 42.1}],
                summary={"value_label": "voto ponderado"},
                metadata={"election_year": 2023, "age_group_label": "mayores de 45"},
            )
        metric = arguments.get("metric", "population_total")
        value_label = {"abstention_pct": "Abstención", "participation_pct": "Participación"}.get(metric, "habitantes")
        return ToolResult(
            tool_name=tool_name,
            operation=tool_name,
            status="ok",
            rows=[
                {
                    "section_id": "2907001023",
                    "section_name": "Sección 23 · Riviera Sur",
                    "value": 5351 if metric == "population_total" else 69.4,
                    "value_label": value_label,
                    "year": arguments.get("year") or arguments.get("election_year") or 2025,
                }
            ],
            summary={"value_label": value_label},
            metadata={"metric": metric, "year": arguments.get("year") or arguments.get("election_year") or 2025},
            methodology_plain="Metodología de prueba.",
        )


def plan(tool_name, arguments):
    return LLMPlanResponse(
        provider="gemini",
        model="fake",
        tool_call=LLMToolCall(tool_name=tool_name, arguments=arguments),
        confidence="medium",
    )


class RealConversationalAgentRegressionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        conversation_store._states.clear()

    def loop(self, provider, executor=None):
        return AskPlannerLoop(
            provider=provider,
            complexity_router=ComplexityRouter(),
            tool_registry=FakeRegistry(),
            tool_executor=executor or ConversationalExecutor(),
            follow_up_resolver=FollowUpResolver(),
            answer_guard=AnswerGuard(),
            settings=Settings(ask_use_llm_planner=True, ask_llm_max_planning_attempts=2),
        )

    async def test_abstention_uses_rank_sections_with_default_municipal_election(self):
        executor = ConversationalExecutor()
        response = await self.loop(FakeProvider([None]), executor).run("¿En qué sección hay menor abstención?", "conv-a")

        self.assertEqual(response.data["tool"], "rank_sections")
        self.assertEqual(response.data["tool_args"]["metric"], "abstention_pct")
        self.assertEqual(response.data["tool_args"]["order"], "asc")
        self.assertTrue(response.data["rows"])
        self.assertIn("Sección", response.answer)

    async def test_most_populated_section_defaults_to_population_total_2025(self):
        executor = ConversationalExecutor()
        response = await self.loop(FakeProvider([None]), executor).run("¿Cuál es la sección más poblada de Mijas?", "conv-pop")

        self.assertEqual(response.data["tool"], "rank_sections")
        self.assertEqual(response.data["tool_args"]["metric"], "population_total")
        self.assertEqual(response.data["tool_args"]["year"], 2025)
        self.assertEqual(response.data["rows"][0]["section_name"], "Sección 23 · Riviera Sur")
        self.assertEqual(response.data["rows"][0]["value"], 5351)
        self.assertIn("Sección 23 · Riviera Sur", response.answer)

    async def test_participation_uses_rank_sections_desc(self):
        executor = ConversationalExecutor()
        response = await self.loop(FakeProvider([None]), executor).run("¿En qué sección hay mayor participación en unas elecciones?", "conv-p")

        self.assertEqual(response.data["tool_args"]["metric"], "participation_pct")
        self.assertEqual(response.data["tool_args"]["order"], "desc")
        self.assertTrue(response.data["rows"])

    async def test_age_18_in_2027_uses_cohort_projection(self):
        response = await self.loop(FakeProvider([None])).run("¿Cuántas personas tendrán 18 años en 2027?", "conv-age")

        self.assertEqual(response.data["tool"], "age_cohort_projection")
        self.assertEqual(response.data["tool_args"]["source_year"], 2025)
        self.assertEqual(response.data["tool_args"]["source_age"], 16)
        self.assertEqual(response.data["tool_args"]["target_year"], 2027)
        self.assertEqual(response.data["tool_args"]["target_age"], 18)
        self.assertIn("Total municipal", response.answer)

    async def test_age_18_to_22_in_2023_uses_cohort_projection_not_participation(self):
        response = await self.loop(FakeProvider([None])).run("¿Cuántas personas tenían entre 18 y 22 años en 2023?", "conv-range")

        self.assertEqual(response.data["tool"], "age_cohort_projection")
        self.assertEqual(response.data["tool_args"]["min_age"], 18)
        self.assertEqual(response.data["tool_args"]["max_age"], 22)
        self.assertEqual(response.data["tool_args"]["source_year"], 2023)
        self.assertNotEqual(response.data["tool_args"].get("metric"), "participation_pct")

    async def test_followup_year_uses_memory_without_gemini(self):
        provider = FakeProvider([plan("rank_sections", {"metric": "population_total", "order": "desc", "limit": 1})])
        loop = self.loop(provider)
        await loop.run("¿Cuál es la sección con mayor población?", "conv-f")

        followup = await loop.run("¿Más poblada en qué año?", "conv-f")

        self.assertIn("2025", followup.answer)
        self.assertEqual(len(provider.plan_calls), 1)

    async def test_wrong_tool_for_age_group_vote_is_rejected_and_fallback_used(self):
        executor = ConversationalExecutor()
        provider = FakeProvider([plan("rank_sections", {"metric": "population_over_65", "order": "desc", "limit": 5}), None])
        response = await self.loop(provider, executor).run("¿Qué suelen votar las personas mayores de 45 años?", "conv-v")

        self.assertEqual(executor.calls[0][0], "ecological_vote_profile_by_age_group")
        self.assertEqual(response.data["tool"], "ecological_vote_profile_by_age_group")


if __name__ == "__main__":
    unittest.main()
