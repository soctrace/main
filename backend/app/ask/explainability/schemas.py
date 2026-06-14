from __future__ import annotations

from pydantic import BaseModel, Field


class MetricExplanation(BaseModel):
    metric: str
    label: str
    plain_definition: str
    interpretation: str
    caveat: str | None = None


class ScoreExplanation(BaseModel):
    score_name: str
    scale: str
    plain_definition: str
    variables_used: list[str]
    interpretation_rules: list[str]
    caveat: str | None = None


class ResponseExplanation(BaseModel):
    what_it_means: str
    how_it_is_calculated: str
    how_to_read_values: str | None = None
    practical_use: str | None = None
    caveats: list[str] = Field(default_factory=list)
