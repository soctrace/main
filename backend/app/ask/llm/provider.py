from abc import ABC, abstractmethod
from typing import Any

from app.ask.llm.schemas import (
    LLMPlanRequest,
    LLMPlanResponse,
    LLMProviderName,
    LLMSynthesisRequest,
    LLMSynthesisResponse,
)


class LLMProvider(ABC):
    name: LLMProviderName

    @abstractmethod
    async def plan(self, request: LLMPlanRequest) -> LLMPlanResponse:
        """Select the analytical tool call for a user question."""

    @abstractmethod
    async def synthesize(self, request: LLMSynthesisRequest) -> LLMSynthesisResponse:
        """Turn a ToolResult-shaped payload into a natural-language answer."""

    @abstractmethod
    def healthcheck(self) -> dict[str, Any]:
        """Report provider readiness without performing external calls."""
