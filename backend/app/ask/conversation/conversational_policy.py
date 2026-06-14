from __future__ import annotations

import re
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ask.conversation.context_inheritance_policy import ContextInheritancePolicy
from app.ask.conversation.conversation_topic_resolver import ConversationTopicResolver
from app.services.local_analyst_service import extract_party, normalize


logger = logging.getLogger(__name__)


class ConversationalPolicyDecision(BaseModel):
    action: Literal[
        "direct_tool",
        "proxy_analysis",
        "clarify_with_options",
        "scenario_estimate",
        "unsupported",
    ]
    rewritten_question: str | None = None
    preferred_tool: str | None = None
    preferred_arguments: dict[str, Any] = Field(default_factory=dict)
    explanation_to_user: str | None = None
    memory_label: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class ConversationalPolicyLayer:
    """Maps conversational intent to safe computable proxies before hard fallback."""

    def __init__(self) -> None:
        self.topic_resolver = ConversationTopicResolver()
        self.inheritance_policy = ContextInheritancePolicy()

    def resolve(
        self,
        question: str,
        semantic_interpretation: dict | None,
        conversation_context: dict,
    ) -> ConversationalPolicyDecision:
        del semantic_interpretation
        text = normalize(question or "")
        party = extract_party(question or "")
        previous_estimate_type = self._context_value(conversation_context, "estimate_type")
        previous_tool = self._context_value(conversation_context, "last_tool_name") or self._context_value(conversation_context, "lastTool")
        topic = self.topic_resolver.resolve(question, conversation_context)

        mobilizable_target = self._mobilizable_abstention_target(text, party, conversation_context, topic, question)
        if mobilizable_target:
            target_label = "general" if mobilizable_target == "general" else mobilizable_target
            return ConversationalPolicyDecision(
                action="proxy_analysis",
                rewritten_question=f"Identificar secciones con mayor abstención movilizable para {target_label}.",
                preferred_tool="mobilizable_abstention_opportunity",
                preferred_arguments={"target": mobilizable_target, "election_type": "MUNICIPALES"},
                explanation_to_user=(
                    "Interpreto la abstención movilizable como una oportunidad territorial: abstención, peso electoral, "
                    "competitividad y afinidad con el partido o bloque cuando la conversación ya lo sugiere."
                ),
                memory_label=f"abstención movilizable {target_label}",
                confidence="high",
            )

        if topic.intent == "electoral_growth_opportunity" and topic.conversation_party:
            return ConversationalPolicyDecision(
                action="proxy_analysis",
                rewritten_question=f"Identificar secciones con mayor potencial de crecimiento electoral para {topic.conversation_party}.",
                preferred_tool="electoral_growth_opportunity",
                preferred_arguments={"party": topic.conversation_party, "election_type": "MUNICIPALES"},
                explanation_to_user=(
                    f"Interpreto el crecimiento en continuidad con el análisis electoral anterior de {topic.conversation_party}: "
                    "margen competitivo, abstención y capacidad territorial de mejora."
                ),
                memory_label=f"margen de crecimiento electoral {topic.conversation_party}",
                confidence="high",
            )

        if self._is_party_followup(text) and (previous_estimate_type == "electoral_viability" or previous_tool == "electoral_viability_estimate"):
            party = party or self._party_from_followup(text)
            if party:
                return self._viability_decision(question, party, action="scenario_estimate", confidence="medium")

        if self._asks_best_party(text):
            return self._viability_decision(
                question,
                "ALL",
                rewritten_question="Comparar la viabilidad electoral orientativa de los principales partidos ahora.",
                action="proxy_analysis",
                confidence="medium",
            )

        if self._asks_win_probability(text):
            if party:
                return self._viability_decision(question, party, action="scenario_estimate", confidence="medium")
            return ConversationalPolicyDecision(
                action="clarify_with_options",
                rewritten_question="Calcular una estimación orientativa de viabilidad electoral por partido.",
                preferred_tool="electoral_viability_estimate",
                preferred_arguments={"party": "ALL"},
                explanation_to_user=(
                    "No tengo una probabilidad electoral real porque falta una capa de sondeos actuales, "
                    "pero puedo estimar viabilidad con datos históricos y territoriales."
                ),
                confidence="low",
            )

        return ConversationalPolicyDecision(action="unsupported", confidence="low")

    def _viability_decision(
        self,
        question: str,
        party: str,
        *,
        rewritten_question: str | None = None,
        action: Literal["proxy_analysis", "scenario_estimate"] = "scenario_estimate",
        confidence: Literal["high", "medium", "low"] = "medium",
    ) -> ConversationalPolicyDecision:
        label_party = "principales partidos" if party == "ALL" else party
        return ConversationalPolicyDecision(
            action=action,
            rewritten_question=rewritten_question or f"Calcular la viabilidad electoral orientativa de {label_party} ahora.",
            preferred_tool="electoral_viability_estimate",
            preferred_arguments={"party": party, "election_type": "MUNICIPALES"},
            explanation_to_user=(
                "No dispongo de una probabilidad electoral real porque no hay sondeos actuales conectados. "
                "Sí puedo estimar la fortaleza electoral con resultados históricos, fuerza territorial, margen frente a rivales y competitividad por secciones."
            ),
            memory_label=f"viabilidad electoral {label_party} ahora",
            confidence=confidence,
        )

    def _asks_win_probability(self, text: str) -> bool:
        asks_chance = bool(re.search(r"probabilidad|probabilidades|opciones|posibilidades|chances|viabilidad", text))
        asks_win = bool(re.search(r"ganar|gane|victoria|municipales|elecciones|alcald", text))
        can_win = bool(re.search(r"puede ganar|podria ganar|podría ganar|tendria.*ganar|tendría.*ganar", text))
        return (asks_chance and asks_win) or can_win

    def _asks_best_party(self, text: str) -> bool:
        return bool(
            re.search(r"que partido|qué partido", text)
            and re.search(r"mas posibilidades|más posibilidades|mas opciones|más opciones|puede ganar|ganaria|ganaría", text)
        )

    def _is_party_followup(self, text: str) -> bool:
        cleaned = text.strip(" ¿?!.")
        return bool(re.fullmatch(r"(y\s+)?(el\s+|la\s+)?(pp|psoe|vox|cs|ciudadanos|partido popular|partido socialista)", cleaned))

    def _party_from_followup(self, text: str) -> str | None:
        return extract_party(text)

    def _mobilizable_abstention_target(
        self,
        text: str,
        party: str | None,
        context: dict[str, Any],
        topic: Any,
        question: str,
    ) -> str | None:
        asks_mobilizable = bool(re.search(
            r"abstencion movilizable|abstenci[oó]n movilizable|bolsa de abstencion|bolsa de abstenci[oó]n|"
            r"abstencionistas potenciales|movilizar abstencion|movilizar abstenci[oó]n|"
            r"voto abstencionista movilizable|abstencion activable|abstenci[oó]n activable|"
            r"donde hay mas abstencionistas|d[oó]nde hay m[aá]s abstencionistas|"
            r"priorizar.*campa[nñ]a.*moviliz|zonas.*priorizar.*campa[nñ]a",
            text,
        ))
        explicit_target = self.inheritance_policy.explicit_target(question)
        inherit_party = self.inheritance_policy.should_inherit_party(question, context)
        cleaned = text.strip(" ¿?!.")
        explicit_followup = bool(explicit_target and re.fullmatch(r"(?:y\s+)?para\s+.+", cleaned))
        previous_party = self.inheritance_policy.previous_party(context)
        if not asks_mobilizable and not explicit_followup and not inherit_party:
            return None
        if explicit_target:
            final_target = explicit_target
        elif inherit_party and previous_party:
            final_target = previous_party
        else:
            final_target = "general"
        logger.debug(
            "ask_mobilizable_abstention_target_resolved",
            extra={
                "question": question,
                "explicit_party": party,
                "previous_party": previous_party or topic.conversation_party,
                "inherit_party": inherit_party,
                "final_target": final_target,
            },
        )
        return final_target

    def _context_value(self, context: dict[str, Any], key: str) -> Any:
        if key in context:
            return context.get(key)
        last_result = context.get("lastResult") if isinstance(context.get("lastResult"), dict) else {}
        summary = last_result.get("summary") if isinstance(last_result.get("summary"), dict) else {}
        metadata = last_result.get("metadata") if isinstance(last_result.get("metadata"), dict) else {}
        return summary.get(key) or metadata.get(key)
