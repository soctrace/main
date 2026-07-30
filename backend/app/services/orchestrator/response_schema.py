from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.analyst.schemas import AnalystChatContext


Confidence = Literal["low", "medium", "high"]
DisplayMode = Literal["chat", "structured"]


class OrchestratorChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=120)
    municipality_id: str = Field(default="29070", min_length=1, max_length=32)
    context: AnalystChatContext = Field(default_factory=AnalystChatContext)


class OrchestratorTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]


class OrchestratorChart(BaseModel):
    kind: str
    title: str
    data: list[dict[str, Any]] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    answer: str
    methodology: str = ""
    confidence: Confidence = "medium"
    data_used: list[str] = Field(default_factory=list)
    data_layers_used: list[str] = Field(default_factory=list)
    variables_used: list[str] = Field(default_factory=list)
    source_views: list[str] = Field(default_factory=list)
    missing_relevant_variables: list[str] = Field(default_factory=list)
    ranking_basis: dict[str, Any] = Field(default_factory=dict)
    self_check: dict[str, bool] = Field(default_factory=dict)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    tables: list[OrchestratorTable] = Field(default_factory=list)
    charts: list[OrchestratorChart] = Field(default_factory=list)
    strategic_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    display_mode: DisplayMode = "chat"
    tools_used: list[str] = Field(default_factory=list)
    mode: str = "orchestrator"
    llm_called: bool = False
    tools_called: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    response_source: Literal["gemini", "tool", "fallback", "legacy"] = "tool"
    conversation_id: str | None = None
    audit_id: str | None = None


def analyst_compatible_payload(response: OrchestratorResponse) -> dict[str, Any]:
    payload = response.model_dump()
    payload["limitations"] = list(response.warnings)
    payload["recommendations"] = list(response.strategic_recommendations)
    payload["evidence_table"] = []
    payload["priority_sections"] = list(response.sections)
    return payload
