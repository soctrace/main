from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from app.ask.tools_v2.schemas import ToolResult


ResponseStyle = Literal["simple", "detailed", "debug"]


class AskRenderedAnswer(BaseModel):
    answer: str
    mode: ResponseStyle = "detailed"
    short_caveat: str | None = None
    methodology: str | None = None
    caveats: list[str] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    table: dict[str, Any] | None = None
    chart_spec: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AskAnswerRenderer(Protocol):
    async def render(
        self,
        question: str,
        tool_result: ToolResult,
        conversation_context: dict[str, Any],
        response_style: ResponseStyle = "detailed",
        locale: str = "es-ES",
    ) -> AskRenderedAnswer:
        ...
