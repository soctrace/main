import unittest

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.sql import SqlValidator
from app.ask.tools_v2 import ToolRegistryV2, tool_call_from_operation

from tests.ask.test_tools_v2 import FakeQueryExecutor


class SemanticToToolsV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.interpreter = SemanticOperationInterpreter(self.catalog)
        self.executor = FakeQueryExecutor()
        self.registry = ToolRegistryV2(self.executor, SqlValidator(self.catalog.approved_relations), self.catalog)

    def assert_question_runs(self, question: str, expected_tool: str) -> None:
        operation = self.interpreter.interpret(question, municipio_id="29070")
        self.assertIsNotNone(operation, question)
        assert operation is not None
        tool_call = tool_call_from_operation(operation)
        self.assertIsNotNone(tool_call, question)
        assert tool_call is not None
        tool_name, args = tool_call
        self.assertEqual(tool_name, expected_tool, question)
        tool = self.registry.get(tool_name)
        self.assertIsNotNone(tool, question)
        assert tool is not None
        result = tool.execute(tool.input_schema.model_validate(args))
        self.assertEqual(result.status, "ok", question)
        self.assertTrue(result.rows, question)
        self.assertFalse(any("marts.ask_" in sql for sql in self.executor.sql))

    def test_required_questions_route_to_tools(self) -> None:
        cases = {
            "¿Cuál es la sección con mayor población?": "rank_sections",
            "¿Qué secciones concentran más jubilados?": "rank_sections",
            "¿Qué sección ha rejuvenecido más desde 2021?": "compare_years",
            "¿Cuántas personas tendrán 18 años en 2027?": "age_cohort_projection",
            "¿Dónde gana siempre el PP?": "persistent_winner",
            "¿Qué secciones combinan renta baja y alta abstención?": "cross_metric_ranking",
            "¿Existe relación entre renta y abstención?": "correlation_analysis",
            "¿Qué suelen votar las personas mayores de 45 años?": "ecological_vote_profile_by_age_group",
            "¿Qué suelen votar los jóvenes?": "ecological_vote_profile_by_age_group",
            "¿Qué probabilidades de ganar tendría el PP en unas elecciones municipales ahora?": "electoral_viability_estimate",
            "¿Puede ganar el PSOE las municipales?": "electoral_viability_estimate",
            "¿Qué partido tiene más posibilidades ahora?": "electoral_viability_estimate",
            "¿En qué secciones tendría más margen de crecimiento PP?": "electoral_growth_opportunity",
        }
        for question, tool_name in cases.items():
            with self.subTest(question=question):
                self.assert_question_runs(question, tool_name)

    def test_age_group_voting_tool_arguments(self) -> None:
        operation = self.interpreter.interpret("¿Qué suelen votar las personas mayores de 45 años?", municipio_id="29070")
        assert operation is not None
        tool_name, args = tool_call_from_operation(operation) or (None, None)
        self.assertEqual(tool_name, "ecological_vote_profile_by_age_group")
        self.assertEqual(args["min_age"], 45)
        self.assertIsNone(args["max_age"])

        operation = self.interpreter.interpret("¿Qué suelen votar los jóvenes?", municipio_id="29070")
        assert operation is not None
        tool_name, args = tool_call_from_operation(operation) or (None, None)
        self.assertEqual(tool_name, "ecological_vote_profile_by_age_group")
        self.assertIsNone(args["min_age"])
        self.assertEqual(args["max_age"], 30)

    def test_probability_questions_route_to_viability_tool(self) -> None:
        operation = self.interpreter.interpret("¿Qué probabilidades de ganar tendría el PP en unas elecciones municipales ahora?", municipio_id="29070")
        assert operation is not None
        tool_name, args = tool_call_from_operation(operation) or (None, None)
        self.assertEqual(operation.operation, "electoral_viability_estimate")
        self.assertEqual(tool_name, "electoral_viability_estimate")
        self.assertEqual(args["party"], "PP")

        operation = self.interpreter.interpret("¿Puede ganar el PSOE las municipales?", municipio_id="29070")
        assert operation is not None
        tool_name, args = tool_call_from_operation(operation) or (None, None)
        self.assertEqual(tool_name, "electoral_viability_estimate")
        self.assertEqual(args["party"], "PSOE")

        operation = self.interpreter.interpret("¿Qué partido tiene más posibilidades ahora?", municipio_id="29070")
        assert operation is not None
        tool_name, args = tool_call_from_operation(operation) or (None, None)
        self.assertEqual(tool_name, "electoral_viability_estimate")
        self.assertEqual(args["party"], "ALL")

    def test_explicit_party_growth_question_uses_electoral_opportunity_not_population(self) -> None:
        operation = self.interpreter.interpret("¿En qué secciones tendría más margen de crecimiento PP?", municipio_id="29070")
        assert operation is not None
        tool_name, args = tool_call_from_operation(operation) or (None, None)
        self.assertEqual(tool_name, "electoral_growth_opportunity")
        self.assertNotEqual(tool_name, "population_growth")
        self.assertEqual(args["party"], "PP")


if __name__ == "__main__":
    unittest.main()
