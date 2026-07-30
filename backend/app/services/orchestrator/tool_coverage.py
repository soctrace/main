from __future__ import annotations

from typing import Any


TOOL_COVERAGE_AUDIT: list[dict[str, Any]] = [
    {
        "tool_name": "get_population_profile",
        "data_layer": "Population Intelligence",
        "source_tables_or_views": ["marts.agent_section_profile"],
        "variables_returned": ["population_total", "population_density"],
        "years_available": ["latest available by marts.agent_section_profile"],
        "section_level": True,
        "known_limitations": ["Aggregated by census section; no individual records."],
    },
    {
        "tool_name": "get_age_structure",
        "data_layer": "Age Structure",
        "source_tables_or_views": ["marts.agent_section_profile"],
        "variables_returned": ["average_age", "population_under_18", "population_under_30", "population_over_65"],
        "years_available": ["latest available by marts.agent_section_profile"],
        "section_level": True,
        "known_limitations": ["Young population defaults to under 30 unless a different cohort is requested."],
    },
    {
        "tool_name": "get_electoral_results",
        "data_layer": "Electoral Intelligence",
        "source_tables_or_views": ["marts.agent_electoral_results", "marts.agent_electoral_summary"],
        "variables_returned": ["vote_pct", "abstention_pct", "participation_pct", "winner_party", "margin_to_first_place", "volatility_pct"],
        "years_available": ["latest municipal election by default", "historical elections when internal growth tool is used"],
        "section_level": True,
        "known_limitations": ["Aggregated election results only; never individual voting behavior."],
    },
    {
        "tool_name": "get_income_profile",
        "data_layer": "Income Intelligence",
        "source_tables_or_views": ["marts.agent_income_sources"],
        "variables_returned": ["income_individual", "income_household", "salary_share", "pension_share", "unemployment_share"],
        "years_available": ["latest available by marts.agent_income_sources"],
        "section_level": True,
        "known_limitations": ["Income is an aggregate/proxy at section level."],
    },
    {
        "tool_name": "get_socioeconomic_profile",
        "data_layer": "Socioeconomic Intelligence",
        "source_tables_or_views": ["marts.agent_section_profile", "marts.agent_income_sources"],
        "variables_returned": ["income_individual", "population_total", "population_under_30", "abstention_pct"],
        "years_available": ["latest compatible year by domain"],
        "section_level": True,
        "known_limitations": ["Composite reasoning must not imply unavailable service gaps or individual vulnerability."],
    },
    {
        "tool_name": "get_housing_profile",
        "data_layer": "Housing Intelligence",
        "source_tables_or_views": ["marts.agent_housing_profile"],
        "variables_returned": ["market_price_estimated_m2", "residential_pressure_index", "housing_classification"],
        "years_available": ["latest available by marts.agent_housing_profile"],
        "section_level": True,
        "known_limitations": ["Estimated values are not appraisals."],
    },
    {
        "tool_name": "get_urban_profile",
        "data_layer": "Urban Intelligence",
        "source_tables_or_views": ["marts.agent_housing_profile"],
        "variables_returned": ["building_intensity", "parcel_density", "built_footprint", "avg_plot_size"],
        "years_available": ["latest available by marts.agent_housing_profile"],
        "section_level": True,
        "known_limitations": ["Built-form indicators do not prove electoral opportunity or public-service gaps."],
    },
    {
        "tool_name": "lookup_section_by_address",
        "data_layer": "Section Lookup",
        "source_tables_or_views": ["marts.agent_section_lookup"],
        "variables_returned": ["address", "section_id"],
        "years_available": [],
        "section_level": True,
        "known_limitations": ["Currently returns controlled unavailable status until reliable geocoding is active."],
    },
    {
        "tool_name": "rank_sections",
        "data_layer": "Territorial Ranking",
        "source_tables_or_views": ["approved semantic catalog"],
        "variables_returned": ["metric selected by request"],
        "years_available": ["depends on selected metric"],
        "section_level": True,
        "known_limitations": ["Generic ranking must not be reinterpreted as campaign ROI or electoral potential."],
    },
    {
        "tool_name": "compare_sections",
        "data_layer": "Section Profile",
        "source_tables_or_views": ["marts.agent_section_profile"],
        "variables_returned": ["population", "income", "electoral", "housing"],
        "years_available": ["latest compatible year by domain"],
        "section_level": True,
        "known_limitations": ["May mix domains with different source years."],
    },
]


def tool_coverage_audit() -> list[dict[str, Any]]:
    return [dict(item) for item in TOOL_COVERAGE_AUDIT]
