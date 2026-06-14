import asyncio
import os

from app.ask.answer_guard import AnswerGuard
from app.ask.conversation.follow_up_resolver import FollowUpResolver
from app.ask.llm.complexity_router import ComplexityRouter
from app.ask.llm.factory import get_llm_provider
from app.ask.planner_loop import AskPlannerLoop
from app.ask.sql import QueryExecutor, SqlGenerator, SqlValidator
from app.ask.tools_v2 import ToolExecutorV2, ToolRegistryV2
from app.core.config import get_settings
from app.core.database import SessionLocal


QUESTIONS = [
    "¿Cuál es la sección con mayor población?",
    "¿Qué secciones concentran más jubilados?",
    "¿Qué sección ha rejuvenecido más desde 2021?",
    "¿Dónde gana siempre el PP?",
    "¿Cuántas personas tendrán 18 años en 2027?",
]


async def main() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is required.")
    if os.getenv("LLM_PROVIDER") != "gemini" or os.getenv("ASK_USE_LLM_PLANNER") != "true":
        raise SystemExit("Set LLM_PROVIDER=gemini and ASK_USE_LLM_PLANNER=true.")

    settings = get_settings()
    session = SessionLocal()
    try:
        sql_generator = SqlGenerator()
        validator = SqlValidator(sql_generator.approved_relations)
        executor = QueryExecutor(session)
        registry = ToolRegistryV2(executor, validator, sql_generator.semantic_catalog)
        loop = AskPlannerLoop(
            provider=get_llm_provider("gemini"),
            complexity_router=ComplexityRouter(),
            tool_registry=registry,
            tool_executor=ToolExecutorV2(registry),
            follow_up_resolver=FollowUpResolver(),
            answer_guard=AnswerGuard(),
            settings=settings,
        )
        for question in QUESTIONS:
            complexity = ComplexityRouter().classify(question)
            response = await loop.run(question, "live-gemini-planner")
            print("-" * 80)
            print("question:", question)
            print("complexity:", complexity.complexity)
            print("tool:", response.data.get("tool") if isinstance(response.data, dict) else None)
            print("tool_args:", response.data.get("tool_args") if isinstance(response.data, dict) else None)
            print("model:", response.data.get("model") if isinstance(response.data, dict) else None)
            print("answer:", response.answer[:400])
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
