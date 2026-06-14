from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TaskType = Literal[
    "single_extreme",
    "historical_extreme_consistency",
    "historical_party_dominance_for_section",
    "section_metric_history",
    "section_party_history",
    "comparison",
    "aggregation",
    "unknown",
]
StepType = Literal["sql", "tool", "calculation"]
ExpectedAnswerType = Literal["single_value", "yes_no_with_evidence", "ranking", "historical_table", "comparison"]
RendererType = Literal[
    "singleExtremeRenderer",
    "historicalConsistencyRenderer",
    "partyHistoryRenderer",
    "rankingRenderer",
    "tableRenderer",
    "comparisonRenderer",
    "genericTableRenderer",
]


class RequiredContext(BaseModel):
    previousSection: bool | None = None
    previousMetric: bool | None = None
    previousYear: bool | None = None


class ResolvedContext(BaseModel):
    sectionId: str | None = None
    sectionName: str | None = None
    metric: str | None = None
    year: int | None = None
    direction: Literal["min", "max", "asc", "desc"] | None = None
    party: str | None = None


class AgentPlanStep(BaseModel):
    id: str
    type: StepType
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    dependsOn: list[str] | None = None


class AgentExecutionPlan(BaseModel):
    planId: str = Field(default_factory=lambda: str(uuid4()))
    userQuestion: str
    resolvedQuestion: str
    task: TaskType
    requiredContext: RequiredContext | None = None
    resolvedContext: ResolvedContext = Field(default_factory=ResolvedContext)
    steps: list[AgentPlanStep] = Field(default_factory=list)
    expectedAnswerType: ExpectedAnswerType
    renderer: RendererType
    confidence: Literal["high", "medium", "low"]


class AnswerCheck(BaseModel):
    passed: bool
    missing: list[str] = Field(default_factory=list)
