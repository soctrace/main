from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.semantic_layer import SemanticCatalog
from app.ask.sql.query_executor import QueryExecutor
from app.ask.sql.sql_validator import SqlValidator
from app.ask.tools_v2.executor import ToolExecutorV2
from app.ask.tools_v2.registry import ToolRegistryV2
from app.ask.tools_v2.schemas import ToolContext
from app.core.database import SessionLocal


SMOKE_TESTS: list[tuple[str, str, dict]] = [
    ("rank_sections population_total", "rank_sections", {"metric": "population_total", "order": "desc", "limit": 5}),
    ("rank_sections average_age asc", "rank_sections", {"metric": "average_age", "order": "asc", "limit": 5}),
    ("rank_sections population_over_65", "rank_sections", {"metric": "population_over_65", "order": "desc", "limit": 5}),
    ("rank_sections income_individual", "rank_sections", {"metric": "income_individual", "order": "desc", "limit": 5}),
    ("rank_sections abstention_pct", "rank_sections", {"metric": "abstention_pct", "order": "desc", "limit": 5}),
    ("rank_sections market_price_estimated_m2", "rank_sections", {"metric": "market_price_estimated_m2", "order": "desc", "limit": 5}),
    ("rank_sections residential_pressure_index", "rank_sections", {"metric": "residential_pressure_index", "order": "desc", "limit": 5}),
    ("filter_sections population > 5000", "filter_sections", {"conditions": [{"metric": "population_total", "operator": ">", "value": 5000}], "limit": 20}),
    ("aggregate_municipality population_total", "aggregate_municipality", {"metric": "population_total"}),
    ("aggregate_municipality population_over_65", "aggregate_municipality", {"metric": "population_over_65"}),
    ("compare_years average_age decrease", "compare_years", {"metric": "average_age", "start_year": 2021, "end_year": 2025, "direction": "largest_decrease", "limit": 5}),
    ("population_growth", "population_growth", {"start_year": 2021, "end_year": 2025, "rank_by": "growth_abs", "order": "desc", "limit": 5}),
    ("age_cohort_projection 18 in 2027", "age_cohort_projection", {"source_year": 2025, "source_age": 16, "target_year": 2027, "target_age": 18, "group_by": "municipality_and_section", "limit": 5}),
    ("party_strength PP", "party_strength", {"party": "PP", "historical": True, "limit": 5}),
    ("party_strength PSOE", "party_strength", {"party": "PSOE", "historical": True, "limit": 5}),
    ("persistent_winner PP", "persistent_winner", {"party": "PP", "limit": 20}),
    ("persistent_winner PSOE", "persistent_winner", {"party": "PSOE", "limit": 20}),
    ("persistent_winner VOX", "persistent_winner", {"party": "VOX", "limit": 20}),
    ("historical_party_average PP", "historical_party_average", {"party": "PP", "limit": 5}),
    ("historical_party_average Riviera Sur", "historical_party_average", {"section": "Riviera Sur", "limit": 5}),
    (
        "cross_metric_ranking low income high abstention",
        "cross_metric_ranking",
        {"metrics": [{"metric": "income_individual", "direction": "low"}, {"metric": "abstention_pct", "direction": "high"}], "limit": 5},
    ),
    (
        "cross_metric_ranking youth growth proxy",
        "cross_metric_ranking",
        {"metrics": [{"metric": "population_under_30", "direction": "high"}, {"metric": "population_total", "direction": "high"}], "limit": 5},
    ),
    ("correlation_analysis income abstention", "correlation_analysis", {"x_metric": "income_individual", "y_metric": "abstention_pct"}),
]


def main() -> int:
    session = SessionLocal()
    try:
        catalog = SemanticCatalog()
        registry = ToolRegistryV2(QueryExecutor(session), SqlValidator(catalog.approved_relations), catalog)
        executor = ToolExecutorV2(registry)
        context = ToolContext()
        failures: list[str] = []
        for label, tool_name, args in SMOKE_TESTS:
            result = executor.execute_sync(tool_name, args, context)
            rows = len(result.rows)
            print(f"{label}: {result.status} rows={rows}")
            if result.status != "ok" or rows == 0:
                failures.append(f"{label}: {result.status} {result.error_code or ''}".strip())
                session.rollback()
        if failures:
            print("MVP catalog validation failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("MVP catalog validation OK")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
