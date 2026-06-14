from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from app.services.local_analyst_service import extract_party, normalize


class ConversationTopic(BaseModel):
    conversation_topic: str | None = None
    conversation_entity: str | None = None
    conversation_party: str | None = None
    conversation_metric: str | None = None
    conversation_domain: str | None = None
    intent: str | None = None

    @property
    def as_memory(self) -> dict[str, Any]:
        return {
            "topic": self.conversation_topic,
            "entity": self.conversation_entity,
            "party": self.conversation_party,
            "metric": self.conversation_metric,
            "domain": self.conversation_domain,
            "intent": self.intent,
        }


class ConversationTopicResolver:
    AMBIGUOUS_GROWTH_TERMS = re.compile(r"crecimiento|fortaleza|potencial|mejora|oportunidad|margen|reforzar|crecer")

    def resolve(self, question: str, conversation_context: dict[str, Any]) -> ConversationTopic:
        text = normalize(question or "")
        party = extract_party(question or "") or self._context_value(conversation_context, "party") or self._context_value(conversation_context, "lastParty")
        previous_tool = self._context_value(conversation_context, "tool") or self._context_value(conversation_context, "lastTool") or self._context_value(conversation_context, "last_tool_name")
        previous_estimate = self._context_value(conversation_context, "estimate_type") or self._context_value(conversation_context, "analysis_type")
        previous_metric = self._context_value(conversation_context, "metric") or self._context_value(conversation_context, "lastMetric")

        if self._is_electoral_question(text) or previous_tool in {"electoral_viability_estimate", "electoral_growth_opportunity"} or previous_estimate == "electoral_viability":
            intent = "viability_analysis" if previous_estimate == "electoral_viability" or previous_tool == "electoral_viability_estimate" else None
            if self.is_ambiguous_growth_question(question, conversation_context) or (party and self.AMBIGUOUS_GROWTH_TERMS.search(text)):
                intent = "electoral_growth_opportunity"
            return ConversationTopic(
                conversation_topic="electoral",
                conversation_entity=party,
                conversation_party=party,
                conversation_metric=previous_metric or previous_estimate or "electoral_viability",
                conversation_domain="electoral",
                intent=intent,
            )

        if re.search(r"poblacion|habitantes|edad|joven|mayor|crecimiento demografico|crecimiento poblacional", text):
            return ConversationTopic(conversation_topic="population", conversation_metric=previous_metric, conversation_domain="population")
        if re.search(r"renta|ingresos|pension", text):
            return ConversationTopic(conversation_topic="income", conversation_metric=previous_metric, conversation_domain="income")
        if re.search(r"vivienda|inmobili|residencial", text):
            return ConversationTopic(conversation_topic="housing", conversation_metric=previous_metric, conversation_domain="housing")
        return ConversationTopic(conversation_party=party, conversation_metric=previous_metric)

    def is_ambiguous_growth_question(self, question: str, conversation_context: dict[str, Any]) -> bool:
        text = normalize(question or "")
        if not self.AMBIGUOUS_GROWTH_TERMS.search(text):
            return False
        if re.search(r"poblacion|habitantes|demograf|padron|padr[oó]n", text):
            return False
        previous_tool = self._context_value(conversation_context, "tool") or self._context_value(conversation_context, "lastTool") or self._context_value(conversation_context, "last_tool_name")
        previous_estimate = self._context_value(conversation_context, "estimate_type") or self._context_value(conversation_context, "analysis_type")
        previous_domain = self._context_value(conversation_context, "domain") or self._context_value(conversation_context, "conversation_domain")
        return previous_domain == "electoral" or previous_tool in {"electoral_viability_estimate", "electoral_growth_opportunity"} or previous_estimate == "electoral_viability"

    def _is_electoral_question(self, text: str) -> bool:
        return bool(re.search(r"voto|partido|pp|psoe|vox|eleccion|elecciones|municipales|ganar|alcald|campana|campaña", text))

    def _context_value(self, context: dict[str, Any], key: str) -> Any:
        if key in context:
            return context.get(key)
        last_result = context.get("lastResult") if isinstance(context.get("lastResult"), dict) else {}
        summary = last_result.get("summary") if isinstance(last_result.get("summary"), dict) else {}
        metadata = last_result.get("metadata") if isinstance(last_result.get("metadata"), dict) else {}
        analytical = context.get("analyticalContext") if isinstance(context.get("analyticalContext"), dict) else {}
        metrics = analytical.get("metrics") if isinstance(analytical.get("metrics"), dict) else {}
        answer_context = context.get("lastAnswerContext") if isinstance(context.get("lastAnswerContext"), dict) else {}
        return summary.get(key) or metadata.get(key) or metrics.get(key) or answer_context.get(key)
