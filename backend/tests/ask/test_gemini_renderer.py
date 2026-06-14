import unittest

from app.ask.llm.provider import LLMProvider
from app.ask.llm.schemas import LLMPlanRequest, LLMPlanResponse, LLMSynthesisResponse
from app.ask.rendering import GeminiRenderer, compress_tool_result_for_llm
from app.ask.tools_v2.schemas import ToolResult


class FakeProvider(LLMProvider):
    name = "gemini"

    def __init__(self, responses=None, *, raises=False):
        self.responses = list(responses or [])
        self.raises = raises
        self.synthesis_calls = []

    async def plan(self, request: LLMPlanRequest) -> LLMPlanResponse:
        return LLMPlanResponse(provider="gemini", model="fake", tool_call=None)

    async def synthesize(self, request):
        self.synthesis_calls.append(request)
        if self.raises:
            raise RuntimeError("provider unavailable")
        if self.responses:
            return self.responses.pop(0)
        return LLMSynthesisResponse(
            provider="gemini",
            model="fake-model",
            answer="La sección con mayor población es Sección 23 · Riviera Sur, con 5.351 habitantes en 2025.",
            methodology="He comparado las secciones por población total.",
            suggested_followups=["¿Qué zonas han crecido más?"],
        )

    def healthcheck(self):
        return {"provider": "gemini", "configured": True}


def ranking_result() -> ToolResult:
    return ToolResult(
        tool_name="rank_sections",
        operation="rank_sections",
        status="ok",
        rows=[
            {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "value": 5351, "value_label": "habitantes", "year": 2025},
            {"section_id": "2907001001", "section_name": "Sección 1", "value": 4200, "value_label": "habitantes", "year": 2025},
        ],
        summary={"value_label": "habitantes", "row_count": 2},
        metadata={"municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025, "metric": "population_total"},
        chart_spec={"type": "bar", "x": "section_name", "y": "value", "rows": [{"section_name": "Sección 23 · Riviera Sur", "value": 5351}]},
        methodology_plain="Comparo todas las secciones por población total.",
        suggested_followups=["Qué zonas han crecido más"],
    )


def entity_list_result() -> ToolResult:
    return ToolResult(
        tool_name="persistent_winner",
        operation="persistent_winner",
        status="ok",
        rows=[
            {"section_id": "1", "section_name": "Sección 1", "value": 100.0, "always_wins": True},
            {"section_id": "2", "section_name": "Sección 2", "value": 100.0, "always_wins": True},
        ],
        metadata={"party": "PP", "municipio_id": "29070"},
        methodology_plain="Reviso las elecciones disponibles.",
        suggested_followups=["Y el PSOE"],
    )


def single_value_result() -> ToolResult:
    return ToolResult(
        tool_name="aggregate_municipality",
        operation="aggregate_municipality",
        status="ok",
        rows=[{"municipio_nombre": "Mijas", "value": 93000, "value_label": "habitantes", "year": 2025}],
        summary={"value_label": "habitantes"},
        metadata={"municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025},
        chart_spec={"type": "metric", "value": 93000},
        methodology_plain="Sumo la población de todas las secciones.",
        suggested_followups=["¿Y en 2023?"],
    )


class GeminiRendererTest(unittest.IsolatedAsyncioTestCase):
    async def test_renders_ranking_answer_and_preserves_chart_spec(self):
        tool_result = ranking_result()
        renderer = GeminiRenderer(FakeProvider())
        rendered = await renderer.render("¿Cuál es la sección con mayor población?", tool_result, {})

        self.assertIn("Sección 23 · Riviera Sur", rendered.answer)
        self.assertEqual(rendered.chart_spec, tool_result.chart_spec)
        self.assertEqual(rendered.suggested_followups, ["¿Qué zonas han crecido más?"])
        self.assertEqual(rendered.metadata["renderer"], "gemini")

    async def test_renders_entity_list_answer(self):
        provider = FakeProvider([
            LLMSynthesisResponse(
                provider="gemini",
                model="fake",
                answer="El PP gana en todas las elecciones disponibles en Sección 1 y Sección 2.",
                suggested_followups=["¿Y el PSOE?"],
            )
        ])
        rendered = await GeminiRenderer(provider).render("¿Dónde gana siempre el PP?", entity_list_result(), {})

        self.assertIn("PP", rendered.answer)
        self.assertEqual(len(rendered.entities), 2)

    async def test_renders_single_value_answer(self):
        provider = FakeProvider([
            LLMSynthesisResponse(
                provider="gemini",
                model="fake",
                answer="La población municipal de Mijas es 93.000 habitantes en 2025.",
                methodology="Sumo las secciones censales.",
            )
        ])
        rendered = await GeminiRenderer(provider).render("¿Cuál es la población de Mijas?", single_value_result(), {})

        self.assertIn("93.000", rendered.answer)
        self.assertEqual(rendered.chart_spec, {"type": "metric", "value": 93000})
        self.assertEqual(rendered.methodology, "Sumo las secciones censales.")

    async def test_handles_structured_synthesis_fields(self):
        provider = FakeProvider([
            LLMSynthesisResponse(
                provider="gemini",
                model="fake",
                answer="La sección con mayor población es Sección 23 · Riviera Sur, con 5.351 habitantes en 2025.",
                methodology="Metodología clara.",
                short_caveat="Dato del último año disponible.",
                caveats=["Cautela."],
                suggested_followups=["¿Y en 2023?"],
            )
        ])
        rendered = await GeminiRenderer(provider).render("Pregunta", ranking_result(), {})

        self.assertEqual(rendered.methodology, "Metodología clara.")
        self.assertEqual(rendered.short_caveat, "Dato del último año disponible.")
        self.assertEqual(rendered.caveats, ["Cautela."])

    async def test_handles_plain_text_synthesis(self):
        provider = FakeProvider([
            LLMSynthesisResponse(
                provider="gemini",
                model="fake",
                answer="La sección con mayor población es Sección 23 · Riviera Sur, con 5.351 habitantes en 2025.",
            )
        ])
        rendered = await GeminiRenderer(provider).render("Pregunta", ranking_result(), {})

        self.assertIn("Sección 23", rendered.answer)
        self.assertEqual(rendered.methodology, ranking_result().methodology_plain)

    async def test_provider_unavailable_falls_back(self):
        rendered = await GeminiRenderer(FakeProvider(raises=True)).render("Pregunta", ranking_result(), {})

        self.assertEqual(rendered.metadata["renderer"], "deterministic")
        self.assertEqual(rendered.metadata["renderer_fallback_reason"], "provider_error")

    async def test_sql_answer_falls_back(self):
        provider = FakeProvider([
            LLMSynthesisResponse(provider="gemini", model="fake", answer="SELECT * FROM marts.agent_section_profile")
        ])
        rendered = await GeminiRenderer(provider).render("Pregunta", ranking_result(), {})

        self.assertEqual(rendered.metadata["renderer"], "deterministic")
        self.assertNotIn("marts.", rendered.answer)

    async def test_wrong_top_section_falls_back(self):
        provider = FakeProvider([
            LLMSynthesisResponse(provider="gemini", model="fake", answer="La primera es Sección 99, con 5.351 habitantes en 2025.")
        ])
        rendered = await GeminiRenderer(provider).render("Pregunta", ranking_result(), {})

        self.assertEqual(rendered.metadata["renderer"], "deterministic")
        self.assertIn("Sección 23 · Riviera Sur", rendered.answer)

    async def test_omitted_entity_list_falls_back(self):
        provider = FakeProvider([
            LLMSynthesisResponse(provider="gemini", model="fake", answer="El PP gana siempre en Sección 1.")
        ])
        rendered = await GeminiRenderer(provider).render("Pregunta", entity_list_result(), {})

        self.assertEqual(rendered.metadata["renderer"], "deterministic")
        self.assertIn("Sección 2", rendered.answer)

    async def test_compress_tool_result_truncates_rows(self):
        tool_result = ranking_result()
        compressed = compress_tool_result_for_llm(tool_result, max_rows=1)

        self.assertEqual(compressed["rows_shown"], 1)
        self.assertEqual(compressed["rows_total"], 2)
        self.assertTrue(compressed["truncated"])
        self.assertNotIn("rows", compressed["chart_spec"])


if __name__ == "__main__":
    unittest.main()
