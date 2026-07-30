from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyticalExplanationContext(BaseModel):
    methodology: str = ""
    warnings: list[str] = Field(default_factory=list)


class OrchestratorConversationContext(BaseModel):
    last_user_goal: str = ""
    last_topic: str = ""
    last_sections: list[str] = Field(default_factory=list)
    last_tools_used: list[str] = Field(default_factory=list)
    last_data_layers_used: list[str] = Field(default_factory=list)
    last_variables_used: list[str] = Field(default_factory=list)
    last_answer_summary: str = ""
    methodology_explanation: AnalyticalExplanationContext = Field(default_factory=AnalyticalExplanationContext)
    last_source_views: list[str] = Field(default_factory=list)
    last_missing_relevant_variables: list[str] = Field(default_factory=list)
    last_ranking_basis: dict[str, Any] = Field(default_factory=dict)
    pending_clarification: str | None = None


class OrchestratorContextStore:
    _states: dict[str, OrchestratorConversationContext] = {}

    def get(self, conversation_id: str) -> OrchestratorConversationContext:
        if conversation_id not in self._states:
            self._states[conversation_id] = OrchestratorConversationContext()
        return self._states[conversation_id]

    def update(
        self,
        conversation_id: str,
        *,
        user_goal: str,
        topic: str,
        sections: list[str],
        tools_used: list[str],
        data_layers_used: list[str],
        variables_used: list[str],
        source_views: list[str],
        missing_relevant_variables: list[str],
        ranking_basis: dict[str, Any],
        answer: str,
        methodology: str = "",
        warnings: list[str] | None = None,
        pending_clarification: str | None = None,
    ) -> OrchestratorConversationContext:
        state = self.get(conversation_id)
        state.last_user_goal = user_goal
        state.last_topic = topic
        state.last_sections = sections
        state.last_tools_used = tools_used
        state.last_data_layers_used = data_layers_used
        state.last_variables_used = variables_used
        state.last_source_views = source_views
        state.last_missing_relevant_variables = missing_relevant_variables
        state.last_ranking_basis = ranking_basis
        state.last_answer_summary = answer[:500]
        if tools_used:
            state.methodology_explanation = AnalyticalExplanationContext(
                methodology=methodology[:1000],
                warnings=list(warnings or []),
            )
        state.pending_clarification = pending_clarification
        return state

    def as_llm_context(self, conversation_id: str) -> dict[str, Any]:
        return self.get(conversation_id).model_dump()


context_store = OrchestratorContextStore()
