from typing import Any, Literal

from pydantic import BaseModel, Field


LLMProviderName = Literal["mock", "gemini", "openai"]
LLMComplexityLevel = Literal["simple", "semi_complex", "complex"]


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class LLMToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class LLMToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


class LLMPlanRequest(BaseModel):
    question: str
    system_prompt: str
    conversation_context: dict[str, Any] = Field(default_factory=dict)
    semantic_context: dict[str, Any] = Field(default_factory=dict)
    tools: list[LLMToolSchema] = Field(default_factory=list)
    complexity: LLMComplexityLevel = "simple"
    locale: str = "es-ES"


class LLMPlanResponse(BaseModel):
    provider: LLMProviderName
    model: str
    tool_call: LLMToolCall | None = None
    reasoning_summary: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    raw: dict[str, Any] | None = None


class LLMSynthesisRequest(BaseModel):
    question: str
    system_prompt: str
    tool_result: dict[str, Any]
    conversation_context: dict[str, Any] = Field(default_factory=dict)
    response_style: Literal["simple", "detailed", "debug"] = "detailed"
    locale: str = "es-ES"


class LLMSynthesisResponse(BaseModel):
    provider: LLMProviderName
    model: str
    answer: str
    methodology: str | None = None
    short_caveat: str | None = None
    suggested_followups: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None
