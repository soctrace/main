from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, model_validator


class AskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str | None = Field(default=None, min_length=1, max_length=2000)
    message: str | None = Field(default=None, min_length=1, max_length=2000)
    conversationId: str | None = Field(default=None, max_length=120)
    conversation_id: str | None = Field(default=None, max_length=120)
    session_id: str | None = Field(default=None, max_length=120)
    user_id: str | None = Field(default=None, max_length=120)
    activeMunicipality: str | None = Field(default="29070", max_length=80)
    active_municipality: str | None = Field(default=None, max_length=80)
    activeYear: int | None = Field(default=None, ge=1900, le=2100)
    active_year: int | None = Field(default=None, ge=1900, le=2100)
    activeLayer: str | None = Field(default=None, max_length=120)
    active_layer: str | None = Field(default=None, max_length=120)
    selectedSectionId: str | None = Field(default=None, max_length=80)
    selected_section_id: str | None = Field(default=None, max_length=80)
    mode: Literal["simple", "detailed", "debug"] | None = None

    @model_validator(mode="after")
    def normalize_chat_payload(self) -> "AskRequest":
        if self.question is None and self.message:
            self.question = self.message
        if self.conversationId is None and self.conversation_id:
            self.conversationId = self.conversation_id
        if self.conversationId is None and self.session_id:
            self.conversationId = self.session_id
        if self.session_id is None and self.conversationId:
            self.session_id = self.conversationId
        if self.activeMunicipality == "29070" and self.active_municipality:
            self.activeMunicipality = self.active_municipality
        if self.activeYear is None and self.active_year is not None:
            self.activeYear = self.active_year
        if self.activeLayer is None and self.active_layer:
            self.activeLayer = self.active_layer
        if self.selectedSectionId is None and self.selected_section_id:
            self.selectedSectionId = self.selected_section_id
        if not self.question:
            raise ValueError("question or message is required")
        return self


class AskResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    answer: str
    mode: Literal["simple", "detailed", "debug"] = "simple"
    confidence: str = "high"
    resultType: str | None = None
    entities: list[dict[str, Any]] = Field(default_factory=list)
    data: Any | None = None
    shortCaveat: str | None = None
    methodology: str | None = None
    caveats: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    suggestedFollowUps: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    table: dict[str, Any] | None = None
    chartSpec: dict[str, Any] | None = None
    sqlDebug: str | None = None
    debug: Any | None = None
    session_memory: dict[str, Any] | None = None
    conversation_id: str | None = None
    session_id: str | None = None
