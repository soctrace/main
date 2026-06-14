from __future__ import annotations

import asyncio
import os

from app.ask.llm.gemini_provider import GeminiProvider
from app.ask.rendering import GeminiRenderer
from app.ask.tools_v2.schemas import ToolResult


def samples() -> list[tuple[str, ToolResult]]:
    return [
        (
            "¿Cuál es la sección con mayor población?",
            ToolResult(
                tool_name="rank_sections",
                operation="rank_sections",
                status="ok",
                rows=[
                    {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "value": 5351, "value_label": "habitantes", "year": 2025}
                ],
                summary={"value_label": "habitantes", "row_count": 1},
                metadata={"municipio_id": "29070", "municipio_nombre": "Mijas", "year": 2025, "metric": "population_total"},
                chart_spec={"type": "bar", "x": "section_name", "y": "value", "rows": []},
                methodology_plain="Comparo todas las secciones por población total en el último año disponible.",
                suggested_followups=["¿Qué zonas han crecido más?"],
            ),
        ),
        (
            "¿Dónde gana siempre el PP?",
            ToolResult(
                tool_name="persistent_winner",
                operation="persistent_winner",
                status="ok",
                rows=[
                    {"section_id": "2907001001", "section_name": "Sección 1", "value": 100.0, "always_wins": True},
                    {"section_id": "2907001002", "section_name": "Sección 2", "value": 100.0, "always_wins": True},
                ],
                summary={"value_label": "victorias del PP", "row_count": 2},
                metadata={"party": "PP", "municipio_id": "29070", "municipio_nombre": "Mijas"},
                methodology_plain="Reviso las elecciones disponibles y cuento las secciones donde el PP es primera fuerza en todas.",
                suggested_followups=["¿Y el PSOE?"],
            ),
        ),
        (
            "¿Cuántas personas tendrán 18 años en 2027?",
            ToolResult(
                tool_name="age_cohort_projection",
                operation="age_cohort_projection",
                status="ok",
                rows=[
                    {"section_id": "2907001023", "section_name": "Sección 23 · Riviera Sur", "value": 120, "target_age": 18, "target_year": 2027, "source_age": 16, "source_year": 2025, "value_label": "personas que tendrán 18 años"}
                ],
                summary={"value_label": "personas que tendrán 18 años", "row_count": 1},
                metadata={"estimated": True, "municipio_id": "29070", "municipio_nombre": "Mijas", "target_year": 2027},
                methodology_plain="Estimación basada en cohortes quinquenales.",
                caveats=["Es una estimación, no una predicción de participación electoral."],
                suggested_followups=["¿Dónde se concentran los nuevos votantes?"],
            ),
        ),
    ]


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY no está configurada; no se llama a Gemini.")
        return
    renderer = GeminiRenderer(GeminiProvider())
    for question, tool_result in samples():
        rendered = await renderer.render(question, tool_result, {}, "detailed", "es-ES")
        print("\n---")
        print(question)
        print(rendered.answer)


if __name__ == "__main__":
    asyncio.run(main())
