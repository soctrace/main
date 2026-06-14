import unittest

from app.ask.conversation.conversational_policy import ConversationalPolicyLayer
from app.ask.service import AskSocTraceService
from app.ask.tools_v2.schemas import ToolResult


class ConversationalPolicyLayerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = ConversationalPolicyLayer()

    def test_pp_probability_question_maps_to_viability_estimate(self) -> None:
        decision = self.policy.resolve(
            "¿Qué probabilidades de ganar tendría el PP en unas elecciones municipales ahora?",
            None,
            {},
        )
        self.assertIn(decision.action, {"scenario_estimate", "proxy_analysis"})
        self.assertEqual(decision.preferred_tool, "electoral_viability_estimate")
        self.assertEqual(decision.preferred_arguments["party"], "PP")
        self.assertNotIn("falta metrica electoral v2", (decision.explanation_to_user or "").lower())

    def test_psoe_can_win_question_maps_to_viability_estimate(self) -> None:
        decision = self.policy.resolve("¿Puede ganar el PSOE las municipales?", None, {})
        self.assertEqual(decision.preferred_tool, "electoral_viability_estimate")
        self.assertEqual(decision.preferred_arguments["party"], "PSOE")

    def test_best_party_question_compares_main_parties(self) -> None:
        decision = self.policy.resolve("¿Qué partido tiene más posibilidades ahora?", None, {})
        self.assertEqual(decision.preferred_tool, "electoral_viability_estimate")
        self.assertEqual(decision.preferred_arguments["party"], "ALL")

    def test_followup_reuses_previous_viability_estimate_type(self) -> None:
        decision = self.policy.resolve(
            "¿Y el PSOE?",
            None,
            {"lastResult": {"summary": {"estimate_type": "electoral_viability"}}},
        )
        self.assertEqual(decision.preferred_tool, "electoral_viability_estimate")
        self.assertEqual(decision.preferred_arguments["party"], "PSOE")

    def test_growth_followup_inherits_electoral_context(self) -> None:
        decision = self.policy.resolve(
            "¿Dónde tiene más margen de crecimiento?",
            None,
            {
                "lastParty": "PP",
                "lastTool": "electoral_viability_estimate",
                "lastResult": {"summary": {"estimate_type": "electoral_viability", "party": "PP"}},
            },
        )
        self.assertEqual(decision.preferred_tool, "electoral_growth_opportunity")
        self.assertEqual(decision.preferred_arguments["party"], "PP")

    def test_viability_answer_contains_required_caveats(self) -> None:
        result = ToolResult(
            tool_name="electoral_viability_estimate",
            operation="electoral_viability_estimate",
            status="ok",
            rows=[
                {
                    "party": "PP",
                    "latest_municipal_vote_pct": 35.4,
                    "latest_municipal_position": 1,
                    "sections_won": 14,
                    "sections_total": 31,
                    "margin_vs_main_opponent": 3.6,
                    "average_historical_vote_pct": 31.2,
                    "trend_direction": "ascendente",
                    "competitive_sections": 9,
                    "viability_index": 68.2,
                    "viability_label": "media-alta",
                }
            ],
            metadata={"party": "PP"},
            summary={"estimate_type": "electoral_viability"},
        )
        answer = AskSocTraceService._tool_v2_answer(object(), result)
        lower = answer.lower()
        self.assertIn("no es una probabilidad estadística real", lower)
        self.assertIn("estimación orientativa", lower)
        self.assertIn("datos históricos y territoriales", lower)
        self.assertIn("\n\n", answer)
        self.assertIn("•", answer)
        self.assertIn("Conclusión", answer)
        self.assertIn("Puedo identificar las secciones", answer)

    def test_growth_answer_has_conversational_structure(self) -> None:
        result = ToolResult(
            tool_name="electoral_growth_opportunity",
            operation="electoral_growth_opportunity",
            status="ok",
            rows=[
                {
                    "section_name": "Sección 11 · Las Lagunas Norte",
                    "party": "PP",
                    "margin_to_first_place": 3.6,
                    "abstention_pct": 38.5,
                    "opportunity_explanation": "sección competitiva",
                }
            ],
            metadata={"party": "PP"},
            summary={"analysis_type": "electoral_growth_opportunity"},
        )
        answer = AskSocTraceService._tool_v2_answer(object(), result)
        self.assertIn("no como crecimiento de población", answer)
        self.assertIn("•", answer)
        self.assertIn("Conclusión", answer)
        self.assertIn("Puedo estimar el impacto", answer)

    def test_strategic_tools_emit_ctas(self) -> None:
        result = ToolResult(
            tool_name="electoral_growth_opportunity",
            operation="electoral_growth_opportunity",
            status="ok",
            rows=[],
            metadata={"party": "PP"},
        )
        ctas = AskSocTraceService._tool_v2_ctas(object(), result)
        self.assertTrue(ctas)
        self.assertIn("label", ctas[0])
        self.assertIn("question", ctas[0])


if __name__ == "__main__":
    unittest.main()
