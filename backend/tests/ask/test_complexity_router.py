import unittest

from app.ask.llm.complexity_router import ComplexityRouter, ComplexityRouterInput


class ComplexityRouterTest(unittest.TestCase):
    def setUp(self):
        self.router = ComplexityRouter()

    def assert_complexity(self, question: str, expected: str):
        result = self.router.classify(ComplexityRouterInput(question=question))

        self.assertEqual(result.complexity, expected, f"{question}: {result.model_dump()}")
        self.assertNotIn("gemini", result.recommended_provider_notes.values())
        self.assertNotIn("model", result.model_dump())

    def test_simple_questions(self):
        examples = [
            "¿Cuál es la sección con mayor población?",
            "¿Cuál es la sección más joven?",
            "¿Qué secciones concentran más jubilados?",
            "¿Cuál es la sección más rica?",
            "¿Dónde gana siempre el PP?",
            "¿Qué sección tiene más abstención?",
            "¿Cuál es la población total de Mijas?",
            "¿Son datos de 2025?",
            "¿Cómo lo has calculado?",
        ]

        for question in examples:
            with self.subTest(question=question):
                self.assert_complexity(question, "simple")

    def test_semi_complex_questions(self):
        examples = [
            "¿Qué zonas han crecido más?",
            "¿Qué sección ha rejuvenecido más desde 2021?",
            "¿Cuántas personas tendrán 18 años en 2027?",
            "¿Cuántas personas de 18 a 22 años se abstuvieron en las municipales de 2023?",
            "¿Qué secciones combinan renta baja y alta abstención?",
            "¿Qué secciones superan los 5.000 habitantes?",
            "¿Cómo ha evolucionado la población desde 2021?",
            "Calcula el reparto D’Hondt de las municipales de 2023.",
        ]

        for question in examples:
            with self.subTest(question=question):
                self.assert_complexity(question, "semi_complex")

    def test_complex_questions(self):
        examples = [
            "¿Qué estrategia debería seguir el PSOE para movilizar voto joven?",
            "¿Qué variables se relacionan más con la abstención?",
            "¿Existe relación entre renta y participación electoral?",
            "Agrupa secciones con perfiles similares.",
            "Detecta secciones atípicas por renta, edad y participación.",
            "Crea un índice de vulnerabilidad.",
            "Crea un índice de oportunidad electoral.",
            "¿Qué secciones podrían cambiar de ganador?",
            "Haz un diagnóstico político de Riviera Sur.",
        ]

        for question in examples:
            with self.subTest(question=question):
                self.assert_complexity(question, "complex")

    def test_semantic_interpretation_overrides_weak_keyword_scoring(self):
        result = self.router.classify(
            ComplexityRouterInput(
                question="¿Qué secciones?",
                semantic_interpretation={"operation": "compare_years", "confidence": "high"},
            )
        )

        self.assertEqual(result.complexity, "semi_complex")
        self.assertIn("semantic operation: compare_years", result.reasons)

    def test_cross_metric_semantic_interpretation_routes_by_metric_count(self):
        semi = self.router.classify(
            {
                "question": "Combina dos indicadores",
                "semantic_interpretation": {
                    "operation": "cross_metric_ranking",
                    "metrics": ["income_individual", "abstention_pct"],
                    "confidence": "high",
                },
            }
        )
        complex_result = self.router.classify(
            {
                "question": "Combina varios indicadores",
                "semantic_interpretation": {
                    "operation": "cross_metric_ranking",
                    "metrics": ["income_individual", "abstention_pct", "average_age"],
                    "confidence": "high",
                },
            }
        )

        self.assertEqual(semi.complexity, "semi_complex")
        self.assertEqual(complex_result.complexity, "complex")

    def test_correlation_semantic_interpretation_is_complex(self):
        result = self.router.classify(
            ComplexityRouterInput(
                question="Relación entre renta y abstención",
                semantic_interpretation={"operation": "correlation_analysis", "confidence": "high"},
            )
        )

        self.assertEqual(result.complexity, "complex")


if __name__ == "__main__":
    unittest.main()
