import unittest

from sqlalchemy import text

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.sql import SqlGenerator, SqlValidator
from app.ask.service import AskSocTraceService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


class AskPopulationSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = SessionLocal()
        try:
            cls.session.execute(text("SELECT 1 FROM marts.agent_section_profile LIMIT 1")).first()
        except Exception as exc:  # pragma: no cover - only used when local DB is absent
            raise unittest.SkipTest(f"Local test database is not ready: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        cls.session.close()

    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.interpreter = SemanticOperationInterpreter(self.catalog)
        self.generator = SqlGenerator()
        self.validator = SqlValidator(self.generator.approved_relations)
        self.service = AskSocTraceService(self.session, get_settings())

    def test_population_rank_interpretation_uses_real_profile_view(self) -> None:
        cases = [
            ("¿Cuál es la sección con mayor población?", "desc"),
            ("¿Cuál es la sección con menor población?", "asc"),
        ]
        for question, order in cases:
            with self.subTest(question=question):
                operation = self.interpreter.interpret(question, municipio_id="29070")
                self.assertIsNotNone(operation)
                assert operation is not None
                self.assertEqual(operation.operation, "rank_sections")
                self.assertEqual(operation.metric, "population_total")
                self.assertEqual(operation.order, order)

                plan = self.generator.generate(question, active_municipality="29070")
                self.assertIsNotNone(plan)
                assert plan is not None
                self.assertIn("marts.agent_section_profile", plan.sql)
                self.assertNotIn("marts.ask_section_profile", plan.sql)
                self.assertTrue(self.validator.validate(plan.sql).ok)

    def test_population_questions_execute_and_render_naturally(self) -> None:
        cases = [
            ("¿Cuál es la sección con mayor población?", "sección más poblada", "Riviera Sur"),
            ("¿Cuál es la sección con menor población?", "sección menos poblada", "888"),
            ("¿Qué secciones superan los 5.000 habitantes?", "5.000 habitantes", "Riviera Sur"),
            ("¿Cuál es la población total de Mijas?", "último año disponible", "94.320"),
            ("¿Cómo ha evolucionado la población desde 2021?", "ha pasado de", "2021"),
        ]
        for question, expected_text, expected_value in cases:
            with self.subTest(question=question):
                response = self.service.ask(AskRequest(question=question, activeMunicipality="29070"))
                self.assertIn(expected_text, response.answer)
                self.assertIn(expected_value, response.answer + str(response.entities) + str(response.data))
                self.assertTrue(response.suggestedFollowUps)
                self.assertNotIn("relation", response.answer.lower())
                self.assertNotIn("sqlalchemy", response.answer.lower())
                self.assertNotIn("psycopg", response.answer.lower())

    def test_population_threshold_returns_entity_list(self) -> None:
        response = self.service.ask(AskRequest(question="¿Qué secciones superan los 5.000 habitantes?", activeMunicipality="29070"))
        self.assertEqual(response.resultType, "entity_list")
        self.assertGreaterEqual(len(response.entities), 1)
        self.assertEqual(response.entities[0]["name"], "Sección 23 · Riviera Sur")

    def test_population_trend_returns_line_chart(self) -> None:
        response = self.service.ask(AskRequest(question="¿Cómo ha evolucionado la población desde 2021?", activeMunicipality="29070"))
        self.assertIsNotNone(response.chartSpec)
        assert response.chartSpec is not None
        self.assertEqual(response.chartSpec["type"], "line")
        self.assertEqual(response.chartSpec["x"], "year")
        self.assertEqual(response.chartSpec["y"], "population_total")
        self.assertGreaterEqual(len(response.chartSpec["rows"]), 5)

    def test_population_growth_interpretation_and_sql(self) -> None:
        cases = [
            ("¿Qué zonas han crecido más?", None, None, "growth_abs", "desc"),
            ("¿Qué secciones han crecido más desde 2021?", 2021, None, "growth_abs", "desc"),
            ("¿Qué secciones han crecido más entre 2021 y 2025?", 2021, 2025, "growth_abs", "desc"),
            ("¿Qué zonas han crecido más en porcentaje?", None, None, "growth_pct", "desc"),
            ("¿Qué zonas han perdido población?", None, None, "growth_abs", "asc"),
        ]
        for question, start_year, end_year, rank_by, order in cases:
            with self.subTest(question=question):
                operation = self.interpreter.interpret(question, municipio_id="29070")
                self.assertIsNotNone(operation)
                assert operation is not None
                self.assertEqual(operation.operation, "population_growth")
                self.assertEqual(operation.metric, "population_total")
                self.assertEqual(operation.start_year, start_year)
                self.assertEqual(operation.end_year, end_year)
                self.assertEqual(operation.rank_by, rank_by)
                self.assertEqual(operation.order, order)

                plan = self.generator.generate(question, active_municipality="29070")
                self.assertIsNotNone(plan)
                assert plan is not None
                self.assertEqual(plan.intent, "section_population_growth")
                self.assertIn("marts.agent_section_profile", plan.sql)
                self.assertNotIn("marts.ask_section_profile", plan.sql)
                self.assertTrue(self.validator.validate(plan.sql).ok)

    def test_population_growth_executes_and_returns_bar_chart(self) -> None:
        response = self.service.ask(AskRequest(question="¿Qué zonas han crecido más?", activeMunicipality="29070"))
        self.assertIn("comparando 2021 con 2025", response.answer)
        self.assertIn("división administrativa de secciones censales", response.answer)
        self.assertIn("Inicio:", response.answer)
        self.assertIn("Final:", response.answer)
        self.assertIn("habitantes", response.answer)
        self.assertIn("%", response.answer)
        self.assertIsNotNone(response.chartSpec)
        assert response.chartSpec is not None
        self.assertEqual(response.chartSpec["type"], "bar")
        self.assertEqual(response.chartSpec["x"], "lineage_group_name")
        self.assertEqual(response.chartSpec["y"], "growthAbs")
        self.assertEqual(response.chartSpec["secondaryValue"], "growthPct")

    def test_future_first_time_voters_executes_and_explains_projection(self) -> None:
        response = self.service.ask(AskRequest(question="¿Cuántas personas aproximadamente tendrán 18 años en 2027?", activeMunicipality="29070"))
        self.assertIn("personas tendrán 18 años en Mijas en 2027", response.answer)
        self.assertIn("16 años en 2025", response.answer)
        self.assertIn("una quinta parte del tramo 15-19", response.answer)
        self.assertIn("votar por primera vez", response.answer)
        self.assertIn("no predice participación electoral", response.answer)
        self.assertNotIn("menor de 30", response.answer)
        self.assertIsNotNone(response.chartSpec)
        assert response.chartSpec is not None
        self.assertEqual(response.chartSpec["type"], "bar")
        self.assertEqual(response.chartSpec["y"], "estimated_future_age_population")
        self.assertTrue(response.suggestedFollowUps)

    def test_population_followups_are_formatted_and_executable(self) -> None:
        response = self.service.ask(AskRequest(question="¿Cuál es la sección con mayor población?", activeMunicipality="29070"))
        self.assertTrue(response.suggestedFollowUps)
        for suggestion in response.suggestedFollowUps:
            with self.subTest(suggestion=suggestion):
                self.assertTrue(suggestion.startswith("¿"))
                self.assertTrue(suggestion.endswith("?"))
                self.assertIsNotNone(self.generator.generate(suggestion, active_municipality="29070"))


if __name__ == "__main__":
    unittest.main()
