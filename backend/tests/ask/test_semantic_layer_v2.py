import unittest

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.sql import SqlGenerator, SqlValidator


class SemanticLayerV2Test(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.interpreter = SemanticOperationInterpreter(self.catalog)
        self.generator = SqlGenerator()
        self.validator = SqlValidator(self.generator.approved_relations)

    def assert_maps(self, question: str, operation: str, metric: str | None = None) -> None:
        interpretation = self.interpreter.interpret(question, municipio_id="29070")
        self.assertIsNotNone(interpretation, question)
        assert interpretation is not None
        self.assertTrue(interpretation.supported, interpretation.reason)
        self.assertEqual(interpretation.operation, operation, question)
        if metric:
            self.assertEqual(interpretation.metric, metric, question)
        self.assertIn("answer_type", interpretation.response_hint)

        plan = self.generator.generate(question, active_municipality="29070")
        self.assertIsNotNone(plan, question)
        assert plan is not None
        self.assertNotIn("marts.ask_", plan.sql)
        self.assertTrue(self.validator.validate(plan.sql).ok, question)

    def test_population_questions(self) -> None:
        cases = [
            ("¿Cuál es la sección con mayor población?", "rank_sections", "population_total"),
            ("¿Cuál es la sección con menor población?", "rank_sections", "population_total"),
            ("¿Qué secciones superan los 5.000 habitantes?", "filter_sections", None),
            ("¿Cuál es la población total de Mijas?", "aggregate_municipality", "population_total"),
            ("¿Qué zonas han crecido más?", "population_growth", "population_total"),
        ]
        for question, operation, metric in cases:
            with self.subTest(question=question):
                if operation == "filter_sections":
                    plan = self.generator.generate(question, active_municipality="29070")
                    self.assertIsNotNone(plan)
                    assert plan is not None
                    self.assertEqual(plan.intent, "population_threshold_sections")
                    self.assertNotIn("marts.ask_", plan.sql)
                    self.assertTrue(self.validator.validate(plan.sql).ok)
                else:
                    self.assert_maps(question, operation, metric)

    def test_age_questions(self) -> None:
        cases = [
            ("¿Cuál es la sección más joven?", "rank_sections", "average_age"),
            ("¿Cuál es la sección más envejecida?", "rank_sections", "average_age"),
            ("¿Qué secciones concentran más población joven?", "rank_sections", "population_under_30"),
            ("¿Qué secciones concentran más jubilados?", "rank_sections", "population_over_65"),
            ("¿Qué sección ha rejuvenecido más desde 2021?", "compare_years", "average_age"),
            ("¿Qué sección ha envejecido más desde 2021?", "compare_years", "average_age"),
        ]
        for question, operation, metric in cases:
            with self.subTest(question=question):
                self.assert_maps(question, operation, metric)

    def test_age_group_voting_questions_use_ecological_profile(self) -> None:
        cases = [
            ("¿Qué suelen votar las personas mayores de 45 años?", 45, None),
            ("¿Qué suelen votar los jóvenes?", None, 30),
            ("¿Qué partido domina en las secciones con más mayores de 65?", 65, None),
        ]
        for question, min_age, max_age in cases:
            with self.subTest(question=question):
                operation = self.interpreter.interpret(question, municipio_id="29070")
                self.assertIsNotNone(operation, question)
                assert operation is not None
                self.assertEqual(operation.operation, "ecological_vote_profile_by_age_group")
                self.assertEqual(operation.filters.get("age_min"), min_age)
                self.assertEqual(operation.filters.get("age_max"), max_age)
                self.assertNotEqual(operation.operation, "rank_sections")

    def test_cohort_questions(self) -> None:
        cases = [
            ("¿Cuántas personas aproximadamente tendrán 18 años en 2027?", "age_cohort_projection", "population_total"),
            ("¿Qué secciones tendrán más nuevos votantes en 2027?", "age_cohort_projection", "population_total"),
            ("¿Cuántas personas tenían entre 18 y 22 años en 2023?", "aggregate_municipality", "population_total"),
        ]
        for question, operation, metric in cases:
            with self.subTest(question=question):
                self.assert_maps(question, operation, metric)

    def test_electoral_questions(self) -> None:
        cases = [
            ("¿Dónde gana siempre el PP?", "persistent_winner", "winner_party"),
            ("¿Dónde gana siempre el PSOE?", "persistent_winner", "winner_party"),
            ("¿Dónde es más fuerte el PP?", "party_strength", "vote_pct"),
            ("¿Qué sección tiene más abstención?", "rank_sections", "abstention_pct"),
            ("¿Qué sección tiene más participación?", "rank_sections", "participation_pct"),
            ("¿Cuáles son las secciones más disputadas?", "rank_sections", "margin_pct"),
        ]
        for question, operation, metric in cases:
            with self.subTest(question=question):
                self.assert_maps(question, operation, metric)

    def test_income_and_housing_questions(self) -> None:
        cases = [
            ("¿Cuál es la sección más rica?", "rank_sections", "income_individual"),
            ("¿Cuál es la sección más pobre?", "rank_sections", "income_individual"),
            ("¿Qué secciones tienen mayor peso de pensiones?", "rank_sections", "pension_share"),
            ("¿Qué secciones tienen mayor valor inmobiliario?", "rank_sections", "market_price_estimated_m2"),
            ("¿Qué zonas tienen mayor presión residencial?", "rank_sections", "residential_pressure_index"),
            ("¿Qué zonas tienen mayor intensidad construida?", "rank_sections", "building_intensity"),
        ]
        for question, operation, metric in cases:
            with self.subTest(question=question):
                self.assert_maps(question, operation, metric)

    def test_cross_metric_beta_questions(self) -> None:
        cases = [
            "¿Qué secciones combinan renta baja y alta abstención?",
            "¿Qué zonas tienen más jóvenes y menos renta?",
            "¿Qué secciones combinan renta alta y voto al PP?",
        ]
        for question in cases:
            with self.subTest(question=question):
                self.assert_maps(question, "cross_metric_ranking")

    def test_catalog_is_agent_only(self) -> None:
        for metric in self.catalog.metrics.values():
            self.assertIn(metric.view, self.catalog.approved_relations)
            self.assertIn("marts.agent_", metric.view)
            self.assertNotIn("marts.ask_", metric.view)


if __name__ == "__main__":
    unittest.main()
