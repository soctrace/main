from __future__ import annotations

from typing import Any

from app.ask.semantic_layer import AnalyticalOperation


OPERATION_TO_TOOL = {
    "rank_sections": "rank_sections",
    "aggregate_municipality": "aggregate_municipality",
    "compare_years": "compare_years",
    "filter_sections": "filter_sections",
    "section_profile": "section_profile",
    "party_strength": "party_strength",
    "persistent_winner": "persistent_winner",
    "historical_party_average": "historical_party_average",
    "age_cohort_projection": "age_cohort_projection",
    "ecological_vote_profile_by_age_group": "ecological_vote_profile_by_age_group",
    "electoral_viability_estimate": "electoral_viability_estimate",
    "electoral_growth_opportunity": "electoral_growth_opportunity",
    "mobilizable_abstention_opportunity": "mobilizable_abstention_opportunity",
    "population_growth": "population_growth",
    "cross_metric_ranking": "cross_metric_ranking",
    "correlation_analysis": "correlation_analysis",
}


def tool_call_from_operation(operation: AnalyticalOperation) -> tuple[str, dict[str, Any]] | None:
    if not operation.supported:
        return None
    tool_name = OPERATION_TO_TOOL.get(operation.operation)
    if not tool_name:
        return None
    municipio_id = operation.municipio_id or operation.municipality_id or "29070"
    if tool_name == "rank_sections":
        return tool_name, {
            "municipio_id": municipio_id,
            "metric": operation.metric,
            "year": operation.year,
            "order": operation.order,
            "limit": operation.limit,
            "filters": operation.filters,
            "election_type": operation.election_type,
            "election_year": operation.election_year,
        }
    if tool_name == "aggregate_municipality":
        return tool_name, {
            "municipio_id": municipio_id,
            "metric": operation.metric,
            "year": operation.year,
            "filters": operation.filters,
        }
    if tool_name == "compare_years":
        return tool_name, {
            "municipio_id": municipio_id,
            "metric": operation.metric,
            "start_year": operation.start_year,
            "end_year": operation.end_year,
            "direction": operation.direction or "largest_increase",
            "order_by": "delta_pct" if operation.rank_by == "growth_pct" else "delta_abs",
            "limit": operation.limit,
        }
    if tool_name == "population_growth":
        return tool_name, {
            "municipio_id": municipio_id,
            "start_year": operation.start_year,
            "end_year": operation.end_year,
            "rank_by": operation.rank_by or "growth_abs",
            "order": operation.order,
            "limit": operation.limit,
        }
    if tool_name == "filter_sections":
        return tool_name, {
            "municipio_id": municipio_id,
            "conditions": operation.filters.get("conditions") or [],
            "year": operation.year,
            "limit": operation.limit,
        }
    if tool_name == "party_strength":
        return tool_name, {
            "municipio_id": municipio_id,
            "party": operation.party,
            "election_type": operation.election_type,
            "election_year": operation.election_year,
            "historical": False,
            "limit": operation.limit,
        }
    if tool_name == "persistent_winner":
        return tool_name, {
            "municipio_id": municipio_id,
            "party": operation.party,
            "election_type": operation.election_type,
            "limit": operation.limit,
        }
    if tool_name == "historical_party_average":
        return tool_name, {
            "municipio_id": municipio_id,
            "party": operation.party,
            "election_type": operation.election_type,
            "limit": operation.limit,
        }
    if tool_name == "age_cohort_projection":
        return tool_name, {
            "municipio_id": municipio_id,
            "source_year": operation.filters.get("sourceYear"),
            "source_age": operation.filters.get("sourceAge"),
            "target_year": operation.filters.get("targetYear") or operation.year,
            "target_age": operation.filters.get("targetAge"),
            "min_age": operation.filters.get("age_min"),
            "max_age": operation.filters.get("age_max"),
            "group_by": operation.filters.get("groupBy") or "municipality_and_section",
            "limit": operation.limit,
        }
    if tool_name == "ecological_vote_profile_by_age_group":
        return tool_name, {
            "municipio_id": municipio_id,
            "min_age": operation.filters.get("age_min"),
            "max_age": operation.filters.get("age_max"),
            "election_type": operation.election_type or "MUNICIPALES",
            "election_year": operation.election_year,
            "party_scope": operation.filters.get("party_scope") or "main",
            "method": operation.filters.get("method") or "section_weighted_profile",
        }
    if tool_name == "electoral_viability_estimate":
        return tool_name, {
            "municipio_id": municipio_id,
            "party": operation.party or "ALL",
            "election_type": operation.election_type or "MUNICIPALES",
            "baseline_year": operation.year,
            "include_other_elections": True,
            "include_abstention": True,
            "include_competitiveness": True,
        }
    if tool_name == "electoral_growth_opportunity":
        return tool_name, {
            "municipio_id": municipio_id,
            "party": operation.party or "PP",
            "election_type": operation.election_type or "MUNICIPALES",
            "election_year": operation.year or operation.election_year,
            "limit": operation.limit or 8,
        }
    if tool_name == "mobilizable_abstention_opportunity":
        return tool_name, {
            "municipio_id": municipio_id,
            "election_type": operation.election_type or "MUNICIPALES",
            "election_year": operation.year or operation.election_year,
            "target": operation.filters.get("target") or operation.party or "general",
            "limit": operation.limit or 10,
        }
    if tool_name == "cross_metric_ranking":
        specs = []
        directions = operation.filters.get("metric_directions") if isinstance(operation.filters, dict) else {}
        if not isinstance(directions, dict):
            directions = {}
        for metric in operation.metrics:
            direction = str(directions.get(metric) or "high")
            if direction not in {"low", "high"}:
                direction = "high"
            specs.append({"metric": metric, "direction": direction, "weight": 1.0, "party": operation.party if metric == "vote_pct" else None})
        if len(specs) == 2 and specs[0]["metric"] == "income_individual" and specs[1]["metric"] == "abstention_pct":
            specs[0]["direction"] = "low"
            specs[1]["direction"] = "high"
        if len(specs) == 2 and specs[0]["metric"] == "population_under_30" and specs[1]["metric"] == "income_individual":
            specs[0]["direction"] = "high"
            specs[1]["direction"] = "low"
        return tool_name, {"municipio_id": municipio_id, "metrics": specs, "limit": operation.limit}
    if tool_name == "correlation_analysis":
        return tool_name, {
            "municipio_id": municipio_id,
            "x_metric": operation.metrics[0],
            "y_metric": operation.metrics[1],
            "year": operation.year,
            "method": "pearson",
        }
    return None
