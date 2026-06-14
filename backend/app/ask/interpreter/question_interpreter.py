import json
import logging
from typing import Any

from app.ask.interpreter.intent_schema import AnalyticalIntent
from app.ask.interpreter.interpreter_prompt import INTERPRETER_SYSTEM_PROMPT
from app.ask.interpreter.semantic_synonyms import deterministic_intent


logger = logging.getLogger(__name__)


class QuestionInterpreter:
    def __init__(
        self,
        *,
        openai_api_key: str | None = None,
        openai_model: str = "gpt-4.1-mini",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.timeout_seconds = timeout_seconds

    def interpret(self, question: str, semantic_catalog: dict[str, Any] | None = None) -> AnalyticalIntent:
        deterministic = deterministic_intent(question)
        if deterministic:
            return deterministic

        llm_intent = self._interpret_with_llm(question, semantic_catalog or {})
        if llm_intent:
            return llm_intent

        return AnalyticalIntent(
            intent="unknown",
            entity="unknown",
            filters={"municipality": "Mijas"},
            confidence="low",
            clarificationNeeded=True,
        )

    def deterministic_match(self, question: str) -> AnalyticalIntent | None:
        return deterministic_intent(question)

    def _interpret_with_llm(self, question: str, semantic_catalog: dict[str, Any]) -> AnalyticalIntent | None:
        if not self.openai_api_key:
            return None
        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("OpenAI package is unavailable; skipping LLM question interpretation.")
            return None

        try:
            client = OpenAI(api_key=self.openai_api_key, timeout=self.timeout_seconds)
            response = client.responses.create(
                model=self.openai_model,
                input=[
                    {"role": "system", "content": INTERPRETER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question,
                                "semanticCatalog": semantic_catalog,
                            },
                            ensure_ascii=True,
                        ),
                    },
                ],
            )
            return AnalyticalIntent.model_validate_json(response.output_text)
        except Exception:
            logger.exception("LLM question interpretation failed; falling back to unknown intent.")
            return None
