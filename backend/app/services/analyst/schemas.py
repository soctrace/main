from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Confidence = Literal["low", "medium", "high"]


class AnalystChatContext(BaseModel):
    active_layer: str | None = None
    active_year: int | None = Field(default=None, ge=1900, le=2100)
    selected_section_id: str | None = Field(default=None, min_length=10, max_length=10)
    selected_election: str | int | None = None

    @field_validator("active_layer", "selected_section_id", "selected_election", mode="before")
    @classmethod
    def empty_optional_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AnalystChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=120)
    municipality_id: str = Field(default="29070", min_length=1, max_length=32)
    context: AnalystChatContext = Field(default_factory=AnalystChatContext)

    @field_validator("municipality_id")
    @classmethod
    def normalize_municipality(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned in {"mijas", "29070"}:
            return "29070"
        return value.strip()

    @field_validator("conversation_id", mode="before")
    @classmethod
    def empty_conversation_id_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AnalystSection(BaseModel):
    section_id: str
    name: str
    score: float | None = None
    tags: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class AnalystTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]


class AnalystChart(BaseModel):
    kind: str
    title: str
    data: list[dict[str, Any]] = Field(default_factory=list)


class StrategicRecommendation(BaseModel):
    priority: Literal["high", "medium", "low"] = "medium"
    section_id: str | None = None
    title: str
    rationale: str
    actions: list[str] = Field(default_factory=list)


class SyntheticVariableRef(BaseModel):
    id: str | None = None
    name: str
    version: str = "v0"
    status: Literal["experimental", "validated", "deprecated"] = "experimental"
    formula: str | None = None
    source_variables: list[str] = Field(default_factory=list)


class AnalystChatResponse(BaseModel):
    answer: str
    methodology: str
    confidence: Confidence
    display_mode: Literal["chat", "structured", "debug"] = "structured"
    data_used: list[str] = Field(default_factory=list)
    data_layers_used: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    variables_used: list[str] = Field(default_factory=list)
    executive_thesis: str | None = None
    priority_sections: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    evidence_table: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    sections: list[AnalystSection] = Field(default_factory=list)
    tables: list[AnalystTable] = Field(default_factory=list)
    charts: list[AnalystChart] = Field(default_factory=list)
    synthetic_variables_used: list[SyntheticVariableRef] = Field(default_factory=list)
    synthetic_variables_created: list[SyntheticVariableRef] = Field(default_factory=list)
    strategic_recommendations: list[StrategicRecommendation] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    conversation_id: str | None = None
    audit_id: str | None = None
