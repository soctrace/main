from typing import Any, Literal

from pydantic import BaseModel, Field


IntentType = Literal[
    "ranking",
    "single_extreme",
    "count",
    "comparison",
    "correlation",
    "trend",
    "aggregation",
    "derived_metric",
    "unknown",
]
EntityType = Literal["section", "municipality", "party", "age_group", "election", "unknown"]
DirectionType = Literal["asc", "desc", "min", "max"]
ConfidenceType = Literal["high", "medium", "low"]


class TimeScope(BaseModel):
    year: int | None = None
    electionType: str | None = None
    allAvailable: bool | None = None


class AnalyticalIntent(BaseModel):
    intent: IntentType
    entity: EntityType
    metric: str | None = None
    direction: DirectionType | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    groupBy: list[str] = Field(default_factory=list)
    timeScope: TimeScope | None = None
    derivedLogic: str | None = None
    confidence: ConfidenceType
    clarificationNeeded: bool | None = None
