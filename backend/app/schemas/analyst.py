from typing import Any, Literal

from pydantic import BaseModel, Field


AnalystIntent = Literal[
    "simple_electoral_ranking",
    "party_performance_by_section_across_elections",
    "historical_party_average",
    "historical_party_dominance_for_section",
    "cross_variable_similarity",
    "multi_step_electoral_socioeconomic_analysis",
    "demographic_analysis",
    "income_analysis",
    "data_lookup",
    "section_comparison",
    "electoral_calculation",
    "forecast_question",
    "methodology_explanation",
    "strategic_interpretation",
    "unknown_or_unsupported",
]
ConfidenceLevel = Literal["high", "medium", "low"]


class AnalystQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    municipality_id: str = "29070"


class AnalystTable(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]


class AnalystChartSpec(BaseModel):
    kind: str
    title: str
    data: list[dict[str, Any]] = Field(default_factory=list)


class AnalystMetric(BaseModel):
    label: str
    value: str | int | float
    description: str | None = None


class AnalystFinding(BaseModel):
    label: str
    description: str
    evidence: str | None = None


class AnalystAnswer(BaseModel):
    answer: str
    summary: str
    title: str | None = None
    methodology: str | None = None
    metrics: list[AnalystMetric] = Field(default_factory=list)
    findings: list[AnalystFinding] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    suggested_follow_ups: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel
    used_tools: list[str]
    data_origin: list[str]
    methodological_notes: list[str]
    table: AnalystTable | None = None
    chart_spec: AnalystChartSpec | None = None
    audit_id: str
