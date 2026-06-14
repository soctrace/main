from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.ask.explainability.schemas import MetricExplanation, ResponseExplanation, ScoreExplanation


class ToolDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    status: Literal["supported", "beta", "pending", "hidden"] = "supported"
    input_model: type[BaseModel]
    operation: str
    examples: list[str] = Field(default_factory=list)


class ToolContext(BaseModel):
    municipio_id: str = "29070"
    municipio_nombre: str | None = "Mijas"
    locale: str = "es-ES"
    active_year: int | None = None
    conversation_id: str | None = None


class ToolResult(BaseModel):
    tool_name: str
    operation: str
    status: Literal["ok", "empty", "unsupported", "error"]
    rows: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    chart_spec: dict[str, Any] | None = None
    methodology_plain: str | None = None
    explanation: ResponseExplanation | None = None
    metric_explanations: list[MetricExplanation] = Field(default_factory=list)
    score_explanation: ScoreExplanation | None = None
    caveats: list[str] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class StrictToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RankSectionsInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    metric: str = Field(description="Canonical metric key, e.g. population_total, average_age, population_over_65, income_individual, abstention_pct.")
    year: int | None = Field(default=None, description="Data year. If omitted, the latest available year is used.")
    order: Literal["asc", "desc"] = Field(default="desc", description="Sort direction. Use asc for lowest/youngest average_age, desc for highest.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of sections to return.")
    filters: dict[str, Any] = Field(default_factory=dict, description="Optional structured filters already resolved by soctrace.")
    election_type: str | None = Field(default=None, description="Election type for electoral metrics, e.g. municipal.")
    election_year: int | None = Field(default=None, description="Election year for electoral metrics. If omitted, latest election is used.")


class AggregateMunicipalityInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    metric: str = Field(description="Canonical metric key to aggregate at municipality level.")
    year: int | None = Field(default=None, description="Data year. If omitted, latest available year is used.")
    aggregation: Literal["sum", "avg", "weighted_avg", "count"] = Field(default="sum", description="Aggregation method appropriate for the metric.")
    filters: dict[str, Any] = Field(default_factory=dict, description="Optional structured filters already resolved by soctrace.")


class CompareYearsInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    metric: str = Field(description="Canonical metric key to compare across years, e.g. population_total or average_age.")
    start_year: int | None = Field(default=None, description="Initial year. If omitted, earliest available year is used.")
    end_year: int | None = Field(default=None, description="Final year. If omitted, latest available year is used.")
    entity: Literal["section", "municipality"] = Field(default="section", description="Level of comparison.")
    order_by: Literal["delta_abs", "delta_pct"] = Field(default="delta_abs", description="Rank by absolute change or percentage change.")
    direction: Literal["largest_increase", "largest_decrease"] = Field(default="largest_increase", description="Direction of change to rank.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of rows to return.")


class PopulationGrowthInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    start_year: int | None = Field(default=None, description="Initial year. If omitted, earliest available year is used.")
    end_year: int | None = Field(default=None, description="Final year. If omitted, latest available year is used.")
    rank_by: Literal["growth_abs", "growth_pct"] = Field(default="growth_abs", description="Rank population growth by absolute or percentage growth.")
    order: Literal["asc", "desc"] = Field(default="desc", description="Sort direction.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of rows to return.")


class FilterCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(description="Canonical metric key used in this filter condition.")
    operator: Literal[">", ">=", "<", "<=", "=", "between", "above_municipal_average", "below_municipal_average", "top_quantile", "bottom_quantile"] = Field(description="Comparison operator.")
    value: Any | None = Field(default=None, description="Comparison value. For between, pass a two-value range.")


class FilterSectionsInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    conditions: list[FilterCondition] = Field(description="Metric conditions that sections must satisfy.")
    year: int | None = Field(default=None, description="Data year. If omitted, latest available year is used.")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of sections to return.")


class SectionProfileInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    section: str = Field(description="Section id, section number or known section name, e.g. Riviera Sur or 2907001023.")
    year: int | None = Field(default=None, description="Data year. If omitted, latest available year is used.")
    include_domains: list[str] = Field(default_factory=lambda: ["population", "income", "electoral", "housing"], description="Domains to include: population, income, electoral, housing.")


class PartyStrengthInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    party: str = Field(description="Canonical party name or common party label, e.g. PP, PSOE, VOX.")
    election_type: str | None = Field(default=None, description="Election type, e.g. municipal.")
    election_year: int | None = Field(default=None, description="Election year. If omitted, latest election is used.")
    historical: bool = Field(default=False, description="When true, rank by historical average across available elections.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of sections to return.")

    @field_validator("party")
    @classmethod
    def normalize_party(cls, value: str) -> str:
        return value.strip().upper()


class PersistentWinnerInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    party: str = Field(description="Canonical party name or common party label, e.g. PP, PSOE, VOX.")
    election_type: str | None = Field(default=None, description="Election type to restrict the analysis, e.g. municipal.")
    require_all_available: bool = Field(default=True, description="Require the party to win all available elections in scope.")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of sections to return.")

    @field_validator("party")
    @classmethod
    def normalize_party(cls, value: str) -> str:
        return value.strip().upper()


class HistoricalPartyAverageInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    section: str | None = Field(default=None, description="Optional section id, number or name.")
    party: str | None = Field(default=None, description="Optional party label, e.g. PP, PSOE, VOX.")
    election_type: str | None = Field(default=None, description="Election type to restrict the analysis.")
    average_type: Literal["unweighted_pct", "weighted_by_valid_votes"] = Field(default="unweighted_pct", description="Historical average method.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of rows to return.")


class AgeCohortProjectionInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    source_year: int | None = Field(default=None, description="Known source year for projection.")
    source_age: int | None = Field(default=None, description="Known source age for projection, e.g. 16 for people turning 18 in two years.")
    target_year: int | None = Field(default=None, description="Target year for projection, e.g. 2027.")
    target_age: int | None = Field(default=None, description="Target age for projection, e.g. 18.")
    min_age: int | None = Field(default=None, description="Minimum age for current age range queries.")
    max_age: int | None = Field(default=None, description="Maximum age for current age range queries.")
    group_by: Literal["municipality", "section", "municipality_and_section"] = Field(default="municipality_and_section", description="Aggregation level for cohort results.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of section rows to return.")


class EcologicalVoteProfileByAgeGroupInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    min_age: int | None = Field(default=None, ge=0, le=120, description="Minimum age included in the territorial age group.")
    max_age: int | None = Field(default=None, ge=0, le=120, description="Maximum age included in the territorial age group.")
    election_type: str = Field(default="MUNICIPALES", description="Election type, e.g. MUNICIPALES.")
    election_year: int | None = Field(default=None, description="Election year. If omitted, latest election is used.")
    party_scope: Literal["all", "main"] = Field(default="main", description="Whether to include all parties or only main parties.")
    method: Literal["section_weighted_profile", "correlation"] = Field(default="section_weighted_profile", description="Ecological inference method.")


class ElectoralViabilityEstimateInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    party: str = Field(description="Canonical party name, e.g. PP, PSOE, VOX. Use ALL to compare main parties.")
    election_type: str = Field(default="MUNICIPALES", description="Election type, normally MUNICIPALES.")
    baseline_year: int | None = Field(default=None, description="Baseline election year. If omitted, latest municipal election is used.")
    include_other_elections: bool = Field(default=True, description="Include historical elections in the structural average.")
    include_abstention: bool = Field(default=True, description="Include abstention/participation context when available.")
    include_competitiveness: bool = Field(default=True, description="Include competitive section count and margin context.")

    @field_validator("party")
    @classmethod
    def normalize_party(cls, value: str) -> str:
        return value.strip().upper()


class ElectoralGrowthOpportunityInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    party: str = Field(description="Canonical party name, e.g. PP, PSOE, VOX.")
    election_type: str = Field(default="MUNICIPALES", description="Election type, normally MUNICIPALES.")
    election_year: int | None = Field(default=None, description="Election year. If omitted, latest municipal election is used.")
    limit: int = Field(default=8, ge=1, le=30, description="Maximum number of opportunity sections to return.")

    @field_validator("party")
    @classmethod
    def normalize_party(cls, value: str) -> str:
        return value.strip().upper()


class MobilizableAbstentionOpportunityInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    election_type: str = Field(default="MUNICIPALES", description="Election type, normally MUNICIPALES.")
    election_year: int | None = Field(default=None, description="Election year. If omitted, latest municipal election is used.")
    target: Literal["general", "left", "right", "PP", "PSOE", "VOX"] = Field(default="general", description="Mobilization target context.")
    limit: int = Field(default=10, ge=1, le=30, description="Maximum number of sections to return.")


class CrossMetricSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(description="Canonical metric key included in the combined score.")
    direction: Literal["low", "high"] = Field(default="high", description="Whether high or low values should improve the score.")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Component weight between 0 and 1.")
    party: str | None = Field(default=None, description="Optional party for party-specific electoral metrics.")


class CrossMetricRankingInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    metrics: list[CrossMetricSpec] = Field(description="Metric components to combine into a normalized ranking score.")
    year: int | None = Field(default=None, description="Data year. If omitted, latest available year is used.")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of sections to return.")


class CorrelationAnalysisInput(StrictToolInput):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas by default.")
    x_metric: str = Field(description="Canonical metric key for the x axis.")
    y_metric: str = Field(description="Canonical metric key for the y axis.")
    year: int | None = Field(default=None, description="Data year. If omitted, latest compatible year is used.")
    method: Literal["pearson", "spearman"] = Field(default="pearson", description="Correlation method.")
