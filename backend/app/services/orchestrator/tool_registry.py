from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ask.llm.schemas import LLMToolSchema


class PublicToolInput(BaseModel):
    municipio_id: str = Field(default="29070", description="INE municipality id. Use 29070 for Mijas.")
    year: int | None = Field(default=None, description="Data year. Use latest available if omitted.")
    section: str | None = Field(default=None, description="Optional section id, section number or section name.")
    limit: int = Field(default=5, ge=1, le=50)


class RankSectionsPublicInput(BaseModel):
    municipio_id: str = Field(default="29070")
    metric: str = Field(description="Approved metric key.")
    year: int | None = None
    order: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=5, ge=1, le=50)


class ElectoralPublicInput(BaseModel):
    municipio_id: str = Field(default="29070")
    party: str | None = Field(default=None, description="Optional party label, e.g. PP, PSOE or VOX.")
    intent: Literal["results", "abstention", "growth_opportunity"] = Field(default="results")
    election_type: str | None = Field(default="MUNICIPALES")
    election_year: int | None = None
    section: str | None = None
    limit: int = Field(default=5, ge=1, le=50)


class AddressLookupInput(BaseModel):
    municipio_id: str = Field(default="29070")
    address: str = Field(min_length=3, max_length=300)


class CompareSectionsInput(BaseModel):
    municipio_id: str = Field(default="29070")
    sections: list[str] = Field(min_length=1, max_length=8)
    year: int | None = None
    include_domains: list[str] = Field(default_factory=lambda: ["population", "income", "electoral", "housing"])


class CompareYearsInput(BaseModel):
    municipio_id: str = Field(default="29070")
    metric: Literal["population_total"] = "population_total"
    start_year: int = Field(ge=2021, le=2025)
    end_year: int = Field(ge=2021, le=2025)
    order: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=10, ge=1, le=50)


class CrossMetricInput(BaseModel):
    municipio_id: str = Field(default="29070")
    year: int | None = None
    metrics: list[dict[str, Any]] = Field(min_length=2, max_length=4)
    limit: int = Field(default=10, ge=1, le=50)


class ToolDefinitionMetadata(BaseModel):
    name: str
    description: str
    parameters_schema: dict[str, Any]
    data_layer: str
    variables_available: list[str] = Field(default_factory=list)
    source_views: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


PUBLIC_TOOL_SCHEMAS: dict[str, type[BaseModel]] = {
    "get_population_profile": PublicToolInput,
    "get_age_structure": PublicToolInput,
    "get_income_profile": PublicToolInput,
    "get_socioeconomic_profile": PublicToolInput,
    "get_electoral_results": ElectoralPublicInput,
    "get_housing_profile": PublicToolInput,
    "get_urban_profile": PublicToolInput,
    "lookup_section_by_address": AddressLookupInput,
    "rank_sections": RankSectionsPublicInput,
    "compare_sections": CompareSectionsInput,
    "compare_years": CompareYearsInput,
    "cross_metric_analysis": CrossMetricInput,
}


PUBLIC_TOOL_DESCRIPTIONS: dict[str, str] = {
    "get_population_profile": "Population profile or ranking for Mijas sections.",
    "get_age_structure": "Age structure, young population, children, seniors and average age.",
    "get_income_profile": "Income profile and income rankings.",
    "get_socioeconomic_profile": "Multidomain socioeconomic profile combining approved indicators.",
    "get_electoral_results": "Aggregated electoral results by section or party. Never individual voting behavior.",
    "get_housing_profile": "Housing, real estate value and residential pressure profile.",
    "get_urban_profile": "Urban built environment, parcel density, building intensity and land profile.",
    "lookup_section_by_address": "Resolve an address to an aggregate census section when reliable lookup data is available.",
    "rank_sections": "Rank sections by an approved metric.",
    "compare_sections": "Compare or profile one or more sections.",
    "compare_years": "Compare population by compatible census-section identities between two supported years.",
    "cross_metric_analysis": "Join and rank sections using two to four approved metrics with explicit directions and weights.",
}


PUBLIC_TOOL_METADATA: dict[str, dict[str, Any]] = {
    "get_population_profile": {
        "data_layer": "Population Intelligence",
        "variables_available": ["population_total", "population_density"],
        "source_views": ["marts.agent_section_profile"],
        "limitations": ["Population data is aggregated by census section."],
    },
    "get_age_structure": {
        "data_layer": "Age Structure",
        "variables_available": ["average_age", "population_under_18", "population_under_30", "population_over_65"],
        "source_views": ["marts.agent_section_profile"],
        "limitations": ["Age cohorts are aggregated, not individual records."],
    },
    "get_income_profile": {
        "data_layer": "Income Intelligence",
        "variables_available": ["income_individual", "income_household", "salary_share", "pension_share", "unemployment_share"],
        "source_views": ["marts.agent_income_sources"],
        "limitations": ["Income values are section-level aggregates."],
    },
    "get_socioeconomic_profile": {
        "data_layer": "Socioeconomic Intelligence",
        "variables_available": ["income_individual", "population_total", "abstention_pct", "population_under_30"],
        "source_views": ["marts.agent_section_profile", "marts.agent_income_sources"],
        "limitations": ["Composite interpretation must distinguish observed variables from recommendations."],
    },
    "get_electoral_results": {
        "data_layer": "Electoral Intelligence",
        "variables_available": ["vote_pct", "abstention_pct", "winner_party", "participation_pct"],
        "source_views": ["marts.agent_electoral_results", "marts.agent_electoral_summary"],
        "limitations": ["Electoral data is aggregated by section and never identifies individual votes."],
    },
    "get_housing_profile": {
        "data_layer": "Housing Intelligence",
        "variables_available": ["market_price_estimated_m2", "residential_pressure_index", "housing_classification"],
        "source_views": ["marts.agent_housing_profile"],
        "limitations": ["Real-estate values are estimates and should not be treated as appraisals."],
    },
    "get_urban_profile": {
        "data_layer": "Urban Intelligence",
        "variables_available": ["parcel_density", "built_footprint", "building_intensity", "avg_plot_size"],
        "source_views": ["marts.agent_housing_profile"],
        "limitations": ["Urban indicators describe built form, not service availability."],
    },
    "lookup_section_by_address": {
        "data_layer": "Section Lookup",
        "variables_available": ["address", "section_id"],
        "source_views": ["marts.agent_section_lookup"],
        "limitations": ["Address geocoding is only available when a reliable SocTrace lookup exists."],
    },
    "rank_sections": {
        "data_layer": "Territorial Ranking",
        "variables_available": ["approved semantic catalog metrics"],
        "source_views": ["approved semantic catalog"],
        "limitations": ["Rankings depend on the selected metric and available year."],
    },
    "compare_sections": {
        "data_layer": "Section Profile",
        "variables_available": ["population", "income", "electoral", "housing"],
        "source_views": ["marts.agent_section_profile"],
        "limitations": ["Comparison is section-level and may mix source years by domain."],
    },
    "compare_years": {
        "data_layer": "Population Intelligence",
        "variables_available": ["population_absolute_change", "population_growth_pct"],
        "source_views": ["marts.agent_population_growth"],
        "limitations": ["Comparisons use compatible territorial lineage or common identifiers."],
    },
    "cross_metric_analysis": {
        "data_layer": "Cross-domain Intelligence",
        "variables_available": ["approved semantic catalog metrics"],
        "source_views": ["approved semantic catalog"],
        "limitations": ["Only sections present for every requested metric are ranked; weights are disclosed."],
    },
}


class OrchestratorToolRegistry:
    def list_tool_names(self) -> list[str]:
        return list(PUBLIC_TOOL_SCHEMAS)

    def has_tool(self, name: str) -> bool:
        return name in PUBLIC_TOOL_SCHEMAS

    def metadata_for(self, name: str) -> ToolDefinitionMetadata | None:
        if not self.has_tool(name):
            return None
        return ToolDefinitionMetadata(
            name=name,
            description=PUBLIC_TOOL_DESCRIPTIONS[name],
            parameters_schema=PUBLIC_TOOL_SCHEMAS[name].model_json_schema(),
            **PUBLIC_TOOL_METADATA[name],
        )

    def llm_schemas(self) -> list[LLMToolSchema]:
        return [
            LLMToolSchema(
                name=name,
                description=PUBLIC_TOOL_DESCRIPTIONS[name],
                parameters=input_model.model_json_schema(),
            )
            for name, input_model in PUBLIC_TOOL_SCHEMAS.items()
        ]

    def public_catalog(self) -> list[dict[str, Any]]:
        return [metadata.model_dump() for name in self.list_tool_names() if (metadata := self.metadata_for(name))]
