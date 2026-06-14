from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ActiveElection(BaseModel):
    type: str
    year: int


class AgeRange(BaseModel):
    minAge: int
    maxAge: int | None = None


class ConversationSection(BaseModel):
    sectionId: str
    sectionName: str
    value: float | int | None = None
    valueLabel: str | None = None


class AnalyticalContext(BaseModel):
    resultType: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class MunicipalityContext(BaseModel):
    id: str
    name: str


class ElectionContext(BaseModel):
    type: str | None = None
    year: int | None = None


class LastAnswerContext(BaseModel):
    question: str
    answerSummary: str
    operation: str
    tool: str | None = None
    metric: str | None = None
    metricLabel: str | None = None
    municipality: MunicipalityContext | None = None
    year: int | None = None
    startYear: int | None = None
    endYear: int | None = None
    election: ElectionContext | None = None
    ageRange: AgeRange | None = None
    sections: list[ConversationSection] = Field(default_factory=list)
    resultRows: list[dict[str, Any]] = Field(default_factory=list)
    chartSpec: Any | None = None
    methodologyPlain: str | None = None
    caveats: list[str] = Field(default_factory=list)
    party: str | None = None
    provider: str | None = None
    model: str | None = None
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConversationState(BaseModel):
    conversationId: str
    municipality: str | None = None
    activeYear: int | None = None
    activeElection: ActiveElection | None = None
    lastParty: str | None = None
    lastQuestion: str | None = None
    lastResultType: str | None = None
    lastMetric: str | None = None
    lastDirection: str | None = None
    lastYear: int | None = None
    lastSection: ConversationSection | None = None
    lastSql: str | None = None
    lastResultRows: list[dict[str, Any]] = Field(default_factory=list)
    lastAgeRange: AgeRange | None = None
    lastSections: list[ConversationSection] = Field(default_factory=list)
    lastTool: str | None = None
    last_tool_name: str | None = None
    last_operation: str | None = None
    last_start_year: int | None = None
    last_end_year: int | None = None
    last_party: str | None = None
    last_election: dict[str, Any] | None = None
    last_rows: list[dict[str, Any]] = Field(default_factory=list)
    last_chart_spec: Any | None = None
    lastResult: Any | None = None
    analyticalContext: AnalyticalContext = Field(default_factory=AnalyticalContext)
    lastMetrics: dict[str, Any] = Field(default_factory=dict)
    lastOutputType: str | None = None
    lastAnswer: str | None = None
    lastMethodology: str | None = None
    lastCaveats: list[str] = Field(default_factory=list)
    lastSources: list[str] = Field(default_factory=list)
    lastTable: dict[str, Any] | None = None
    lastDebug: Any | None = None
    lastAnswerContext: LastAnswerContext | None = None
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updatedAt = datetime.now(timezone.utc).isoformat()
