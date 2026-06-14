import unittest

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.service import AskSocTraceService
from app.ask.sql import SqlValidator
from app.ask.tools_v2 import ToolRegistryV2, tool_call_from_operation

from tests.ask.test_tools_v2 import FakeQueryExecutor


class ExplainabilityLayerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.interpreter = SemanticOperationInterpreter(self.catalog)
        self.executor = FakeQueryExecutor()
        self.registry = ToolRegistryV2(self.executor, SqlValidator(self.catalog.approved_relations), self.catalog)

    def _answer_for(self, question: str) -> str:
        operation = self.interpreter.interpret(question, municipio_id="29070")
        self.assertIsNotNone(operation)
        tool_call = tool_call_from_operation(operation)
        self.assertIsNotNone(tool_call)
        tool_name, args = tool_call or ("", {})
        self.assertEqual(tool_name, "cross_metric_ranking")
        tool = self.registry.get(tool_name)
        self.assertIsNotNone(tool)
        result = tool.execute(tool.input_schema.model_validate(args))
        self.assertEqual(result.status, "ok")
        self.assertIsNotNone(result.explanation)
        self.assertTrue(result.metric_explanations)
        self.assertIsNotNone(result.score_explanation)
        return AskSocTraceService._tool_v2_answer(object(), result)

    def test_composite_score_explanation_for_left_vote_and_abstention(self) -> None:
        answer = self._answer_for("¿Qué secciones combinan alta abstención y mucho voto de izquierdas?")
        lower = answer.lower()
        self.assertIn("índice", lower)
        self.assertIn("0 a 1", lower)
        self.assertIn("no es un porcentaje", lower)
        self.assertIn("cuanto más cerca", lower)
        self.assertIn("abstención", lower)
        self.assertIn("voto de izquierdas", lower)

    def test_cross_metric_useful_interpretation(self) -> None:
        answer = self._answer_for("¿Qué secciones combinan alta abstención y mucho voto de izquierdas?")
        lower = answer.lower()
        self.assertIn("movilización", lower)
        self.assertIn("bolsa", lower)
        self.assertIn("lectura territorial", lower)

    def test_cross_metric_caveat(self) -> None:
        answer = self._answer_for("¿Qué secciones combinan alta abstención y mucho voto de izquierdas?")
        lower = answer.lower()
        self.assertIn("no demuestra causalidad", lower)
        self.assertIn("no mide voto individual", lower)

    def test_no_raw_score_only_answer(self) -> None:
        answer = self._answer_for("¿Qué secciones combinan alta abstención y mucho voto de izquierdas?")
        self.assertNotRegex(answer.lower(), r"^secci[oó]n .+ 0[,\.]8 score compuesto$")
        self.assertNotIn("score compuesto", answer.lower())
        self.assertIn("Qué significa", answer)
        self.assertIn("Cómo se ha calculado", answer)

    def test_sample_categories_have_explainability(self) -> None:
        cases = [
            ("population_growth", {"rank_by": "growth_abs"}, "crecimiento de poblacion"),
            ("age_cohort_projection", {"source_year": 2025, "source_age": 16, "target_year": 2027, "target_age": 18}, "personas que tendran"),
            ("rank_sections", {"metric": "abstention_pct"}, "Abstencion"),
            ("rank_sections", {"metric": "income_individual"}, "Renta individual"),
            ("rank_sections", {"metric": "market_price_estimated_m2"}, "Valor inmobiliario"),
            ("correlation_analysis", {"x_metric": "income_individual", "y_metric": "abstention_pct"}, "correlacion"),
        ]
        for tool_name, args, expected_label in cases:
            with self.subTest(tool=tool_name):
                tool = self.registry.get(tool_name)
                self.assertIsNotNone(tool)
                result = tool.execute(tool.input_schema.model_validate(args))
                self.assertEqual(result.status, "ok")
                self.assertTrue(result.explanation or result.metric_explanations or result.score_explanation)
                self.assertIn(expected_label.lower().split()[0], (result.summary.get("value_label") or result.metadata.get("value_label") or "").lower() + str(result.metric_explanations).lower())


if __name__ == "__main__":
    unittest.main()
