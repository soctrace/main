from __future__ import annotations

import logging
import re
from typing import Any

from app.services.local_analyst_service import extract_party, normalize


logger = logging.getLogger(__name__)


class ContextInheritancePolicy:
    """Controls when memory is allowed to narrow an otherwise general question."""

    def should_inherit_party(self, question: str, conversation_context: dict[str, Any]) -> bool:
        text = normalize(question or "")
        explicit_party = extract_party(question or "")
        previous_party = self.previous_party(conversation_context)
        inherit = bool(
            previous_party
            and not explicit_party
            and (
                self.is_clear_party_followup(text)
                or self.is_contextual_strategy_followup(text)
            )
        )
        logger.debug(
            "ask_context_inheritance_party",
            extra={
                "question": question,
                "explicit_party": explicit_party,
                "previous_party": previous_party,
                "inherit_party": inherit,
            },
        )
        return inherit

    def explicit_target(self, question: str) -> str | None:
        text = normalize(question or "")
        party = extract_party(question or "")
        if party in {"PP", "PSOE", "VOX"}:
            return party
        if re.search(r"\bpara\s+(?:la\s+)?izquierda\b|\bpara\s+(?:el\s+)?bloque progresista\b|progresist", text):
            return "left"
        if re.search(r"\bpara\s+(?:la\s+)?derecha\b|\bpara\s+(?:el\s+)?bloque conservador\b|conservador", text):
            return "right"
        return None

    def previous_party(self, context: dict[str, Any]) -> str | None:
        for key in ("party", "lastParty", "last_party"):
            value = context.get(key)
            if value in {"PP", "PSOE", "VOX"}:
                return str(value)
        last_entities = context.get("last_entities") if isinstance(context.get("last_entities"), dict) else {}
        entity_party = last_entities.get("party")
        if entity_party in {"PP", "PSOE", "VOX"}:
            return str(entity_party)
        last_result = context.get("lastResult") if isinstance(context.get("lastResult"), dict) else {}
        summary = last_result.get("summary") if isinstance(last_result.get("summary"), dict) else {}
        metadata = last_result.get("metadata") if isinstance(last_result.get("metadata"), dict) else {}
        for source in (summary, metadata):
            value = source.get("party")
            if value in {"PP", "PSOE", "VOX"}:
                return str(value)
        return None

    def is_clear_party_followup(self, text: str) -> bool:
        cleaned = text.strip(" ¿?!.")
        return bool(
            re.fullmatch(r"(?:y\s+)?para\s+(?:ellos|ellas|esa candidatura|esta candidatura|ese partido|esa fuerza|la candidatura)", cleaned)
            or re.fullmatch(r"(?:y\s+)?para\s+(?:el\s+|la\s+)?(?:pp|psoe|vox|partido popular|partido socialista)", cleaned)
            or re.fullmatch(r"(?:y\s+)?(?:el\s+|la\s+)?(?:pp|psoe|vox|partido popular|partido socialista)", cleaned)
        )

    def is_contextual_strategy_followup(self, text: str) -> bool:
        return bool(
            re.search(r"\ben esas secciones\b|\ben esas zonas\b|\ball[ií]\b|\bah[ií]\b", text)
            or re.search(r"d[oó]nde deber[ií]a movilizar|d[oó]nde podr[ií]a movilizar|qu[eé] puede hacer", text)
            or re.fullmatch(r"(?:y\s+)?d[oó]nde tendr[ií]a m[aá]s margen", text.strip(" ¿?!."))
        )
