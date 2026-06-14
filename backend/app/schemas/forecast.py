from typing import Any

from pydantic import BaseModel, Field


class ForecastPartyShare(BaseModel):
    party: str
    projected_vote_share: float


class ForecastMunicipalityOutlook(BaseModel):
    municipality_id: str
    forecast_year: int = 2027
    projected_leading_party: str | None = None
    projected_leading_vote_share: float | None = None
    projected_vote_shares: list[ForecastPartyShare] = Field(default_factory=list)
    turnout_forecast: float | None = None
    volatility: float | None = None
    forecast_confidence: float
    structural_forecast_confidence: float | None = None
    contextual_vote_adjustment_pct: float | None = None
    contextual_uncertainty: float | None = None
    has_contextual_adjustments: bool = False
    confidence_level: str
    section_count: int
    swing_territory_count: int
    strategic_section_count: int
    abstention_risk_area_count: int
    interpretation: str
    model_version: str
    oraculum_calibrated: bool


class ForecastSectionOutlook(BaseModel):
    section_id: str
    municipality_id: str
    forecast_year: int
    projected_leading_party: str | None = None
    projected_vote_share: float | None = None
    structural_projected_leading_party: str | None = None
    structural_projected_vote_share: float | None = None
    turnout_forecast: float | None = None
    volatility: float
    abstention_risk: float
    localist_potential: float
    swing_sections: float
    forecast_confidence: float
    structural_forecast_confidence: float | None = None
    contextual_adjustment_score: float | None = None
    contextual_vote_adjustment_pct: float | None = None
    contextual_uncertainty: float | None = None
    contextual_confidence: str | None = None
    has_contextual_adjustments: bool = False
    contextual_drivers: list[dict[str, Any]] = Field(default_factory=list)
    confidence_level: str
    is_strategic_section: bool
    is_swing_section: bool
    is_abstention_risk_area: bool
    interpretation: str
    drivers: list[dict[str, Any]] = Field(default_factory=list)
    model_version: str
    oraculum_calibrated: bool


class ForecastScenario(BaseModel):
    municipality_id: str
    forecast_year: int = 2027
    scenario_id: str
    scenario_name: str
    scenario_label: str
    scenario_description: str
    scenario_assumption: str
    turnout_forecast: float | None = None
    volatility: float | None = None
    forecast_confidence: float
    contextual_uncertainty: float
    swing_territory_count: int
    strategic_section_count: int
    projected_vote_shares: list[ForecastPartyShare] = Field(default_factory=list)
    projected_leading_party: str | None = None
    projected_leading_vote_share: float | None = None
    oraculum_calibrated: bool
    model_version: str
    interpretation: str
    cs_supply_uncertainty: float
    pmp_supply_uncertainty: float
    localist_supply_uncertainty: float
    candidate_supply_uncertainty: float
    is_conditional: bool = False
    has_contextual_adjustments: bool = False
    oraculum_priority_sections: list[dict[str, Any]] = Field(default_factory=list)


class ForecastScenarioList(BaseModel):
    municipality_id: str
    year: int = 2027
    scenarios: list[ForecastScenario] = Field(default_factory=list)
