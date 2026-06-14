from __future__ import annotations

import unittest

from app.ask.explainability.schemas import MetricExplanation, ScoreExplanation
from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import LLMPlanRequest, LLMPlanResponse, LLMSynthesisRequest, LLMSynthesisResponse
from app.ask.rendering.gemini_renderer import GeminiRenderer
from app.ask.service import AskSocTraceService
from app.ask.tools_v2.schemas import ToolResult
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.ask import AskRequest


def assert_before(testcase: unittest.TestCase, answer: str, first: str, *later: str) -> None:
    first_position = answer.find(first)
    testcase.assertGreaterEqual(first_position, 0, f"Missing heading: {first}\n\n{answer}")
    for heading in later:
        later_position = answer.find(heading)
        testcase.assertGreaterEqual(later_position, 0, f"Missing heading: {heading}\n\n{answer}")
        testcase.assertLess(
            first_position,
            later_position,
            f"{first!r} must appear before {heading!r}\n\n{answer}",
        )


class FakeProvider(LLMProvider):
    name = "gemini"

    def __init__(self, response: LLMSynthesisResponse):
        self.response = response

    async def plan(self, request: LLMPlanRequest) -> LLMPlanResponse:
        return LLMPlanResponse(provider="gemini", model="fake", tool_call=None)

    async def synthesize(self, request: LLMSynthesisRequest) -> LLMSynthesisResponse:
        return self.response

    def healthcheck(self):
        return {"provider": "gemini", "configured": True}


def cross_metric_tool_result() -> ToolResult:
    return ToolResult(
        tool_name="cross_metric_ranking",
        operation="cross_metric_ranking",
        status="ok",
        rows=[
            {
                "section_id": "2907001009",
                "section_name": "Sección 09 · Barrio de las flores Este",
                "value": 0.861,
                "value_label": "Índice combinado renta individual/juventud",
                "components": {
                    "income_individual": 0.14,
                    "population_under_30_pct": 0.92,
                },
            }
        ],
        summary={"value_label": "Índice combinado renta individual/juventud", "row_count": 1},
        metadata={"municipio_id": "29070", "municipio_nombre": "Mijas"},
        methodology_plain="Combino indicadores normalizados por sección.",
        metric_explanations=[
            MetricExplanation(
                metric="income_individual",
                label="Renta individual",
                plain_definition="Ingreso medio individual estimado.",
                interpretation="Valores más bajos indican menor renta.",
            ),
            MetricExplanation(
                metric="population_under_30_pct",
                label="Población joven",
                plain_definition="Peso de población menor de 30 años.",
                interpretation="Valores más altos indican más presencia joven.",
            ),
        ],
        score_explanation=ScoreExplanation(
            score_name="Índice combinado renta individual/juventud",
            scale="0 a 1",
            plain_definition="Ordena secciones combinando menor renta y mayor población joven.",
            variables_used=["Renta individual", "Población joven"],
            interpretation_rules=["Cuanto más cerca de 1, mayor ajuste a la combinación buscada."],
        ),
        caveats=["No demuestra causalidad."],
    )


class ResponseOrderingEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.session = SessionLocal()
        cls.settings = get_settings()
        cls.settings.ask_use_llm_planner = False
        cls.service = AskSocTraceService(cls.session, cls.settings)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.session.close()

    def _ask(self, question: str):
        return self.service.ask(
            AskRequest(
                question=question,
                activeMunicipality="29070",
                conversationId=f"response-order-{abs(hash(question))}",
                mode="debug",
            )
        )

    def test_cross_metric_answer_puts_results_before_explanation(self):
        response = self._ask("¿Qué secciones tienen más jóvenes y menos renta?")

        assert_before(self, response.answer, "Resultados principales", "Qué significa", "Cómo se ha calculado")

    def test_strategic_answer_puts_indicators_before_methodology(self):
        response = self._ask("¿Qué probabilidades tiene el PP de ganar?")

        assert_before(self, response.answer, "Indicadores principales", "Qué significa", "Cómo se ha calculado")

    def test_mobilizable_abstention_puts_results_or_indicators_first(self):
        response = self._ask("¿Dónde hay más abstención movilizable?")
        heading = "Indicadores principales" if "Indicadores principales" in response.answer else "Resultados principales"

        assert_before(self, response.answer, heading, "Qué significa", "Cómo se ha calculado")


class ResponseOrderingRendererFallbackTest(unittest.IsolatedAsyncioTestCase):
    async def test_gemini_answer_with_old_order_falls_back_to_result_first_renderer(self):
        provider = FakeProvider(
            LLMSynthesisResponse(
                provider="gemini",
                model="fake",
                answer=(
                    "La sección que mejor combina población joven y menor renta es Sección 09 · Barrio de las flores Este.\n\n"
                    "Qué significa\n\n"
                    "Combino dos factores.\n\n"
                    "Cómo se ha calculado\n\n"
                    "Se normalizan ambos indicadores.\n\n"
                    "Resultados principales\n\n"
                    "• Sección 09 · Barrio de las flores Este — 0,861"
                ),
            )
        )

        rendered = await GeminiRenderer(provider).render(
            "¿Qué secciones tienen más jóvenes y menos renta?",
            cross_metric_tool_result(),
            {},
        )

        self.assertEqual(rendered.metadata["renderer"], "deterministic")
        self.assertEqual(rendered.metadata["renderer_fallback_reason"], "result_order_failed")
        assert_before(self, rendered.answer, "Resultados principales", "Qué significa", "Cómo se ha calculado")


if __name__ == "__main__":
    unittest.main()
