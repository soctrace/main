import asyncio
import os

from app.ask.llm import LLMPlanRequest, LLMToolSchema
from app.ask.llm.complexity_router import ComplexityRouter, ComplexityRouterInput
from app.ask.llm.gemini_provider import GeminiProvider


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is required for the live Gemini provider test.")

    provider = GeminiProvider()
    print(provider.healthcheck())

    question = "¿Cuál es la sección con mayor población?"
    complexity = ComplexityRouter().classify(ComplexityRouterInput(question=question)).complexity
    response = await provider.plan(
        LLMPlanRequest(
            question=question,
            system_prompt="",
            complexity=complexity,
            tools=[
                LLMToolSchema(
                    name="rank_sections",
                    description="Rank sections by a metric",
                    parameters={
                        "type": "object",
                        "properties": {
                            "metric": {"type": "string"},
                            "order": {"type": "string", "enum": ["asc", "desc"]},
                            "limit": {"type": "integer"},
                            "municipio_id": {"type": "string"},
                        },
                        "required": ["metric"],
                    },
                )
            ],
        )
    )
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
