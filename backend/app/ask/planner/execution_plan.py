from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    action: str
    toolName: str | None = None
    toolInput: dict[str, Any] = Field(default_factory=dict)
    description: str


class ExecutionPlan(BaseModel):
    intent: str
    resolvedReferences: dict[str, Any] = Field(default_factory=dict)
    steps: list[PlanStep] = Field(default_factory=list)
