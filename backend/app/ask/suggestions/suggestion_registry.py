from __future__ import annotations

from pydantic import BaseModel


class SuggestionDefinition(BaseModel):
    id: str
    question: str
    domain: str
    required_tool: str
    context_required: bool = False
    fallback_question: str | None = None


class SuggestionRegistry:
    def __init__(self) -> None:
        self._items = {
            item.question.lower(): item
            for item in [
                SuggestionDefinition(
                    id="mobilizable_abstention_general",
                    question="¿Dónde hay más abstención movilizable?",
                    domain="electoral",
                    required_tool="mobilizable_abstention_opportunity",
                    fallback_question="¿Qué secciones tienen mayor abstención?",
                ),
                SuggestionDefinition(
                    id="mobilization_campaign_priority",
                    question="¿Qué zonas debería priorizar una campaña?",
                    domain="electoral",
                    required_tool="mobilizable_abstention_opportunity",
                    fallback_question="¿Dónde hay más abstención movilizable?",
                ),
                SuggestionDefinition(
                    id="mobilization_campaign_priority_full",
                    question="¿Qué zonas debería priorizar una campaña de movilización?",
                    domain="electoral",
                    required_tool="mobilizable_abstention_opportunity",
                    fallback_question="¿Dónde hay más abstención movilizable?",
                ),
                SuggestionDefinition(
                    id="abstention_ranking",
                    question="¿Qué secciones tienen mayor abstención?",
                    domain="electoral",
                    required_tool="rank_sections",
                ),
            ]
        }

    def get(self, question: str) -> SuggestionDefinition | None:
        return self._items.get(question.strip().lower())

    def all(self) -> list[SuggestionDefinition]:
        return list(self._items.values())
