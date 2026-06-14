import unittest

from app.ask.semantic_layer import SemanticCatalog, SemanticOperationInterpreter
from app.ask.sql import SqlGenerator, SqlValidator
from app.ask.service import AskSocTraceService


class SemanticLayerProfessionalPerspectivesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = SemanticCatalog()
        self.interpreter = SemanticOperationInterpreter(self.catalog)
        self.generator = SqlGenerator()
        self.validator = SqlValidator(self.generator.approved_relations)

    def _operation(self, question: str):
        operation = self.interpreter.interpret(question, municipio_id="29070")
        self.assertIsNotNone(operation, question)
        return operation

    def test_political_spin_doctor_questions_map_to_operations(self) -> None:
        cases = {
            "¿Dónde es más fuerte el PP?": ("party_strength", "vote_pct", "PP"),
            "¿Dónde es más fuerte el PSOE?": ("party_strength", "vote_pct", "PSOE"),
            "¿En qué secciones gana siempre el PP?": ("persistent_winner", "winner_party", "PP"),
            "¿En qué secciones gana siempre el PSOE?": ("persistent_winner", "winner_party", "PSOE"),
            "¿Qué secciones tienen más abstención?": ("rank_sections", "abstention_pct", None),
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                operation = self._operation(question)
                self.assertEqual(operation.operation, expected[0])
                self.assertEqual(operation.metric, expected[1])
                if expected[2]:
                    self.assertEqual(operation.party, expected[2])

    def test_sociologist_questions_map_to_demographic_metrics(self) -> None:
        cases = {
            "¿Cuál es la sección más joven?": ("average_age", "asc"),
            "¿Cuál es la sección más envejecida?": ("average_age", "desc"),
            "¿Qué secciones tienen más población menor de 30 años?": ("population_under_30", "desc"),
            "¿Qué secciones tienen más personas mayores de 65?": ("population_over_65", "desc"),
            "¿Qué secciones tienen mayor densidad de población?": ("population_density", "desc"),
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                operation = self._operation(question)
                self.assertEqual(operation.operation, "rank_sections")
                self.assertEqual(operation.metric, expected[0])
                self.assertEqual(operation.order, expected[1])

    def test_economist_and_real_estate_questions_use_approved_metrics(self) -> None:
        cases = {
            "¿Cuál es la sección con mayor renta individual?": "income_individual",
            "¿Cuál es la sección con menor renta?": "income_individual",
            "¿Qué secciones tienen mayor valor inmobiliario estimado?": "market_price_estimated_m2",
            "¿Qué secciones tienen mayor presión residencial?": "residential_pressure_index",
            "¿Qué zonas tienen mayor intensidad construida?": "building_intensity",
        }
        for question, metric in cases.items():
            with self.subTest(question=question):
                operation = self._operation(question)
                self.assertEqual(operation.operation, "rank_sections")
                self.assertEqual(operation.metric, metric)

    def test_generated_sql_uses_only_approved_agent_views_for_common_questions(self) -> None:
        questions = [
            "¿Cuál es la sección con mayor población?",
            "¿Cuál es la sección más joven?",
            "¿Dónde es más fuerte el PP?",
            "¿En qué secciones gana siempre el PSOE?",
            "¿Qué secciones tienen más abstención?",
            "¿Qué secciones tienen mayor presión residencial?",
        ]
        for question in questions:
            with self.subTest(question=question):
                plan = self.generator.generate(question, active_municipality="29070")
                self.assertIsNotNone(plan)
                assert plan is not None
                self.assertIn("marts.agent_", plan.sql)
                self.assertNotIn("core.", plan.sql)
                self.assertTrue(self.validator.validate(plan.sql).ok)

    def test_population_growth_question_maps_to_lineage_growth_operation(self) -> None:
        operation = self._operation("¿Qué zonas han crecido más?")
        self.assertEqual(operation.operation, "population_growth")
        self.assertEqual(operation.metric, "population_total")
        self.assertEqual(operation.rank_by, "growth_abs")

        plan = self.generator.generate("¿Qué zonas han crecido más?", active_municipality="29070")
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.intent, "section_population_growth")
        self.assertIn("manual_lineage", plan.sql)
        self.assertIn("2907001037", plan.sql)
        self.assertIn("2907001025", plan.sql)
        self.assertIn("current_sections", plan.sql)
        self.assertNotIn("ORDER BY population_total", plan.sql)
        self.assertTrue(self.validator.validate(plan.sql).ok)

    def test_future_first_time_voters_maps_to_cohort_projection(self) -> None:
        operation = self._operation("¿Cuántas personas aproximadamente tendrán 18 años en 2027?")
        self.assertEqual(operation.operation, "age_cohort_projection")
        self.assertEqual(operation.metric, "population_total")
        self.assertEqual(operation.filters["sourceYear"], 2025)
        self.assertEqual(operation.filters["sourceAge"], 16)
        self.assertEqual(operation.filters["targetYear"], 2027)
        self.assertEqual(operation.filters["targetAge"], 18)

        plan = self.generator.generate("¿Cuántas personas aproximadamente tendrán 18 años en 2027?", active_municipality="29070")
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan.intent, "future_age_cohort_projection")
        self.assertIn("marts.agent_population_age", plan.sql)
        self.assertNotIn("core.poblacion_edad", plan.sql)
        self.assertNotIn("marts.dim_seccion_display", plan.sql)
        self.assertIn("age_cohort = '15-19'", plan.sql)
        self.assertIn("year = 2025", plan.sql)
        self.assertIn("ROUND(source_age_band_population / 5.0)", plan.sql)
        self.assertNotIn("population_under_30", plan.sql)
        self.assertTrue(self.validator.validate(plan.sql).ok)

    def test_future_first_time_voters_routing_guard_beats_youth_share(self) -> None:
        for question in [
            "¿Qué secciones tendrán más nuevos votantes en 2027?",
            "¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027?",
        ]:
            with self.subTest(question=question):
                plan = self.generator.generate(question, active_municipality="29070")
                self.assertIsNotNone(plan)
                assert plan is not None
                self.assertEqual(plan.intent, "future_age_cohort_projection")
                self.assertNotIn("population_under_30", plan.sql)

    def test_population_growth_answer_explains_section_split_plainly(self) -> None:
        service = AskSocTraceService.__new__(AskSocTraceService)
        plan = self.generator.generate("¿Qué zonas han crecido más?", active_municipality="29070")
        self.assertIsNotNone(plan)
        assert plan is not None
        answer = service._population_growth_answer(
            [
                {
                    "lineage_group_name": "Zona historica Seccion 25 / Maria Zambrano",
                    "section_name": "Zona historica Seccion 25 / Maria Zambrano",
                    "start_year": 2021,
                    "end_year": 2025,
                    "base_sections": "Sección 25",
                    "current_sections": "Sección 25 + Sección 37",
                    "population_start": 1000,
                    "population_end": 1400,
                    "growth_abs": 400,
                    "growth_pct": 40.0,
                    "includes_split": True,
                }
            ],
            plan,
        )
        self.assertIn("división administrativa de secciones censales", answer)
        self.assertIn("Sección 37", answer)
        self.assertIn("Sección 25 + Sección 37", answer)
        self.assertIn("Inicio: 1.000 habitantes", answer)
        self.assertIn("Final: 1.400 habitantes", answer)
        self.assertIn("+400 habitantes", answer)

    def test_multi_municipality_filter_is_not_mijas_hardcoded(self) -> None:
        plan = self.generator.generate("¿Cuál es la sección con mayor población?", active_municipality="29640")
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertIn("municipio_id = '29640'", plan.sql)
        self.assertNotIn("Mijas", plan.sql)

    def test_conversation_memory_can_change_previous_metric_to_percentage(self) -> None:
        operation = self.interpreter.interpret(
            "¿Y en porcentaje?",
            municipio_id="29070",
            last_metric="population_under_30",
        )
        self.assertIsNotNone(operation)
        assert operation is not None
        self.assertEqual(operation.metric, "population_under_30_pct")

    def test_specific_fallback_explains_missing_catalog_area(self) -> None:
        answer = self.interpreter.fallback_message("¿Dónde se concentra más población extranjera?")
        self.assertIn("población extranjera", answer)
        self.assertIn("Semantic Layer v2", answer)


if __name__ == "__main__":
    unittest.main()
