from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.ask.semantic_layer import MetricDefinition, SemanticCatalog
from app.ask.tools_v2.schemas import (
    AgeCohortProjectionInput,
    AggregateMunicipalityInput,
    CompareYearsInput,
    CorrelationAnalysisInput,
    CrossMetricRankingInput,
    EcologicalVoteProfileByAgeGroupInput,
    FilterSectionsInput,
    HistoricalPartyAverageInput,
    PartyStrengthInput,
    PersistentWinnerInput,
    PopulationGrowthInput,
    RankSectionsInput,
    SectionProfileInput,
)


AGENT_RELATIONS = {
    "marts.agent_section_profile",
    "marts.agent_population_age",
    "marts.agent_electoral_results",
    "marts.agent_electoral_summary",
    "marts.agent_income_sources",
    "marts.agent_housing_profile",
    "marts.agent_section_lookup",
    "marts.mv_electoral_behavior",
}


@dataclass(frozen=True)
class BuiltSql:
    sql: str
    sources: list[str]
    metadata: dict[str, Any]


class ToolSqlBuilders:
    def __init__(self, catalog: SemanticCatalog | None = None, lineage_path: Path | None = None) -> None:
        self.catalog = catalog or SemanticCatalog()
        self.lineage_path = lineage_path or Path(__file__).resolve().parents[1] / "section_lineage.yaml"
        self.section_lineage = yaml.safe_load(self.lineage_path.read_text(encoding="utf-8")) if self.lineage_path.exists() else {"lineages": []}

    def metric(self, metric_id: str) -> MetricDefinition:
        metric = self.catalog.metric(metric_id)
        if not metric:
            raise ValueError(f"Metric `{metric_id}` is not defined in Semantic Layer v2.")
        if metric.view not in AGENT_RELATIONS:
            raise ValueError(f"Metric `{metric_id}` does not use an approved agent_* relation.")
        return metric

    def rank_sections(self, payload: RankSectionsInput) -> BuiltSql:
        metric = self.metric(payload.metric)
        if metric.view == "marts.mv_electoral_behavior":
            year_filter = f"AND behavior.anio = {int(payload.year)}" if payload.year else ""
            order = payload.order.upper()
            sql = f"""
WITH filtered AS (
    SELECT
        behavior.seccion_id::text AS section_id,
        COALESCE(lookup.section_name, behavior.seccion_id::text) AS section_name,
        {self._literal(payload.municipio_id)} AS municipio_id,
        'Mijas' AS municipio_nombre,
        behavior.anio AS year,
        behavior.{metric.field} AS value
    FROM marts.mv_electoral_behavior AS behavior
    LEFT JOIN marts.agent_section_lookup AS lookup
      ON lookup.section_id = behavior.seccion_id::text
     AND lookup.municipio_id = {self._literal(payload.municipio_id)}
    WHERE LEFT(behavior.seccion_id::text, 5) = {self._literal(payload.municipio_id)}
      {year_filter}
      AND behavior.{metric.field} IS NOT NULL
),
latest AS (
    SELECT MAX(year) AS year
    FROM filtered
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    year,
    value
FROM filtered
JOIN latest USING (year)
ORDER BY value {order}, section_name
LIMIT {int(payload.limit)}
""".strip()
            return BuiltSql(sql, [metric.view, "marts.agent_section_lookup"], {"metric": metric.metric_id, "value_label": metric.label, "order": payload.order})
        temporal_column = "year"
        year_value = payload.year
        extra_filters = ""
        if metric.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"}:
            temporal_column = "election_year"
            year_value = payload.election_year or payload.year
            election_type = self._election_type(payload.election_type)
            extra_filters += f" AND election_type = {self._literal(election_type)}"
        year_filter = f"AND {temporal_column} = {int(year_value)}" if year_value else ""
        order = payload.order.upper()
        extra_selects = ""
        if metric.metric_id == "margin_pct":
            extra_selects = ",\n        winner_party,\n        winner_vote_pct,\n        second_party,\n        second_vote_pct"
        sql = f"""
WITH filtered AS (
    SELECT
        section_id,
        section_name,
        municipio_id,
        municipio_nombre,
        {temporal_column} AS year,
        {metric.field} AS value{extra_selects}
    FROM {metric.view}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {year_filter}
      {extra_filters}
      AND {metric.field} IS NOT NULL
),
latest AS (
    SELECT MAX(year) AS year
    FROM filtered
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    year,
    value{extra_selects}
FROM filtered
JOIN latest USING (year)
ORDER BY value {order}, section_name
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, [metric.view], {"metric": metric.metric_id, "value_label": metric.label, "order": payload.order})

    def aggregate_municipality(self, payload: AggregateMunicipalityInput) -> BuiltSql:
        metric = self.metric(payload.metric)
        age_min = payload.filters.get("age_min")
        age_max = payload.filters.get("age_max")
        if age_min is not None and age_max is not None:
            year_filter = f"AND year = {int(payload.year)}" if payload.year else ""
            sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM marts.agent_population_age
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {year_filter}
)
SELECT
    municipio_id,
    municipio_nombre,
    year,
    SUM(people)::numeric AS value
FROM marts.agent_population_age
JOIN latest USING (year)
WHERE municipio_id = {self._literal(payload.municipio_id)}
  AND gender IN ('H', 'M')
  AND age_max >= {int(age_min)}
  AND age_min <= {int(age_max)}
GROUP BY municipio_id, municipio_nombre, year
""".strip()
            return BuiltSql(sql, ["marts.agent_population_age"], {"metric": "population_total", "value_label": f"personas de {age_min} a {age_max} anos"})
        year_filter = f"AND year = {int(payload.year)}" if payload.year else ""
        aggregation = "AVG" if payload.aggregation in {"avg", "weighted_avg"} or metric.metric_id.endswith("_pct") else "SUM"
        sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM {metric.view}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {year_filter}
)
SELECT
    municipio_id,
    municipio_nombre,
    year,
    {aggregation}({metric.field})::numeric AS value
FROM {metric.view}
JOIN latest USING (year)
WHERE municipio_id = {self._literal(payload.municipio_id)}
  AND {metric.field} IS NOT NULL
GROUP BY municipio_id, municipio_nombre, year
""".strip()
        return BuiltSql(sql, [metric.view], {"metric": metric.metric_id, "value_label": metric.label, "aggregation": aggregation.lower()})

    def compare_years(self, payload: CompareYearsInput) -> BuiltSql:
        metric = self.metric(payload.metric)
        if payload.entity == "municipality":
            group_select = "municipio_id, municipio_nombre"
            group_by = "municipio_id, municipio_nombre"
            id_select = "municipio_id, municipio_nombre"
        else:
            group_select = "section_id, section_name, municipio_id, municipio_nombre"
            group_by = "section_id, section_name, municipio_id, municipio_nombre"
            id_select = "section_id, section_name, municipio_id, municipio_nombre"
        start_expr = f"MIN(year) FILTER (WHERE year = {int(payload.start_year)})" if payload.start_year else "MIN(year)"
        end_expr = f"MAX(year) FILTER (WHERE year = {int(payload.end_year)})" if payload.end_year else "MAX(year)"
        order_col = "delta_pct" if payload.order_by == "delta_pct" else "delta_abs"
        order = "ASC" if payload.direction == "largest_decrease" else "DESC"
        value_expr = "SUM(metric_value)" if payload.entity == "municipality" and metric.type == "integer" else "AVG(metric_value)" if payload.entity == "municipality" else "MAX(metric_value)"
        sql = f"""
WITH profile AS (
    SELECT
        {group_select},
        year,
        {metric.field} AS metric_value
    FROM {metric.view}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND {metric.field} IS NOT NULL
),
years AS (
    SELECT
        COALESCE({start_expr}, MIN(year)) AS start_year,
        COALESCE({end_expr}, MAX(year)) AS end_year
    FROM profile
),
aggregated AS (
    SELECT
        {group_select},
        year,
        {value_expr} AS metric_value
    FROM profile
    GROUP BY {group_by}, year
),
pivoted AS (
    SELECT
        {id_select},
        years.start_year,
        years.end_year,
        MAX(metric_value) FILTER (WHERE year = years.start_year) AS start_value,
        MAX(metric_value) FILTER (WHERE year = years.end_year) AS end_value
    FROM aggregated
    CROSS JOIN years
    WHERE year IN (years.start_year, years.end_year)
    GROUP BY {id_select}, years.start_year, years.end_year
)
SELECT
    *,
    ROUND((end_value - start_value)::numeric, 2) AS delta_abs,
    ROUND((end_value - start_value)::numeric / NULLIF(start_value, 0) * 100, 2) AS delta_pct
FROM pivoted
WHERE start_value IS NOT NULL
  AND end_value IS NOT NULL
ORDER BY {order_col} {order}, {('section_name' if payload.entity == 'section' else 'municipio_nombre')}
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, [metric.view], {"metric": metric.metric_id, "value_label": metric.label, "direction": payload.direction})

    def population_growth(self, payload: PopulationGrowthInput) -> BuiltSql:
        order = payload.order.upper()
        rank_column = "growth_pct" if payload.rank_by == "growth_pct" else "growth_abs"
        start_filter = f"MIN(year) FILTER (WHERE year = {int(payload.start_year)})" if payload.start_year else "MIN(year)"
        end_filter = f"MAX(year) FILTER (WHERE year = {int(payload.end_year)})" if payload.end_year else "MAX(year)"
        lineage_values = self._section_lineage_values(payload.municipio_id)
        sql = f"""
WITH population_profile AS MATERIALIZED (
    SELECT municipio_id, municipio_nombre, section_id, section_name, year, population_total
    FROM marts.agent_section_profile
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND population_total IS NOT NULL
),
years AS (
    SELECT COALESCE({start_filter}, MIN(year)) AS start_year, COALESCE({end_filter}, MAX(year)) AS end_year
    FROM population_profile
),
manual_lineage(municipio_id, lineage_group_id, lineage_group_name, base_year, base_section_id, current_year, current_section_id, relationship_type, notes) AS (
    VALUES
        {lineage_values}
),
current_sections AS (
    SELECT profile.section_id, profile.section_name, profile.municipio_nombre
    FROM population_profile profile
    CROSS JOIN years
    WHERE profile.year = years.end_year
),
lineage_assignments AS (
    SELECT
        current_sections.section_id AS current_section_id,
        COALESCE(manual_lineage.base_section_id, current_sections.section_id) AS base_section_id,
        COALESCE(manual_lineage.lineage_group_id, {self._literal(payload.municipio_id)} || '_' || current_sections.section_id || '_LINEAGE') AS lineage_group_id,
        COALESCE(manual_lineage.lineage_group_name, 'Zona historica ' || current_sections.section_name) AS lineage_group_name,
        COALESCE(manual_lineage.relationship_type, 'unchanged') AS relationship_type,
        manual_lineage.notes,
        current_sections.section_name AS current_section_name,
        current_sections.municipio_nombre
    FROM current_sections
    LEFT JOIN manual_lineage
      ON manual_lineage.municipio_id = {self._literal(payload.municipio_id)}
     AND manual_lineage.current_section_id = current_sections.section_id
),
base_members AS (
    SELECT DISTINCT lineage_group_id, lineage_group_name, base_section_id
    FROM lineage_assignments
),
start_pop AS (
    SELECT base_members.lineage_group_id, SUM(profile.population_total)::bigint AS population_start, STRING_AGG(profile.section_name, ' + ' ORDER BY profile.section_name) AS base_sections
    FROM base_members
    CROSS JOIN years
    JOIN population_profile profile ON profile.year = years.start_year AND profile.section_id = base_members.base_section_id
    GROUP BY base_members.lineage_group_id
),
end_pop AS (
    SELECT lineage_assignments.lineage_group_id, MAX(lineage_assignments.lineage_group_name) AS lineage_group_name, MAX(lineage_assignments.municipio_nombre) AS municipio_nombre, SUM(profile.population_total)::bigint AS population_end, STRING_AGG(lineage_assignments.current_section_name, ' + ' ORDER BY lineage_assignments.current_section_name) AS current_sections, BOOL_OR(lineage_assignments.relationship_type = 'split_child') AS includes_split, STRING_AGG(lineage_assignments.notes, ' | ' ORDER BY lineage_assignments.current_section_id) FILTER (WHERE lineage_assignments.notes IS NOT NULL) AS lineage_notes
    FROM lineage_assignments
    CROSS JOIN years
    JOIN population_profile profile ON profile.year = years.end_year AND profile.section_id = lineage_assignments.current_section_id
    GROUP BY lineage_assignments.lineage_group_id
)
SELECT
    end_pop.lineage_group_id AS section_id,
    end_pop.lineage_group_name AS section_name,
    end_pop.lineage_group_id,
    end_pop.lineage_group_name,
    end_pop.municipio_nombre,
    years.start_year,
    years.end_year,
    start_pop.base_sections,
    end_pop.current_sections,
    start_pop.population_start,
    end_pop.population_end,
    (end_pop.population_end - start_pop.population_start)::bigint AS growth_abs,
    ROUND((end_pop.population_end - start_pop.population_start)::numeric / NULLIF(start_pop.population_start, 0) * 100, 2) AS growth_pct,
    end_pop.includes_split,
    end_pop.lineage_notes
FROM end_pop
JOIN start_pop USING (lineage_group_id)
CROSS JOIN years
ORDER BY {rank_column} {order}, end_pop.lineage_group_name
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, ["marts.agent_section_profile"], {"metric": "population_total", "value_label": "crecimiento de poblacion", "rank_by": payload.rank_by})

    def filter_sections(self, payload: FilterSectionsInput) -> BuiltSql:
        if not payload.conditions:
            raise ValueError("At least one condition is required.")
        condition = payload.conditions[0]
        metric = self.metric(condition.metric)
        if metric.view == "marts.mv_electoral_behavior":
            year_filter = f"AND behavior.anio = {int(payload.year)}" if payload.year else ""
            where_condition = self._condition_sql("value", condition.operator, condition.value)
            sql = f"""
WITH filtered AS (
    SELECT
        behavior.seccion_id::text AS section_id,
        COALESCE(lookup.section_name, behavior.seccion_id::text) AS section_name,
        {self._literal(payload.municipio_id)} AS municipio_id,
        'Mijas' AS municipio_nombre,
        behavior.anio AS year,
        behavior.{metric.field} AS value
    FROM marts.mv_electoral_behavior AS behavior
    LEFT JOIN marts.agent_section_lookup AS lookup
      ON lookup.section_id = behavior.seccion_id::text
     AND lookup.municipio_id = {self._literal(payload.municipio_id)}
    WHERE LEFT(behavior.seccion_id::text, 5) = {self._literal(payload.municipio_id)}
      {year_filter}
      AND behavior.{metric.field} IS NOT NULL
),
latest AS (
    SELECT MAX(year) AS year FROM filtered
),
scored AS (
    SELECT filtered.*, AVG(value) OVER () AS municipal_average, PERCENT_RANK() OVER (ORDER BY value) AS pct_rank
    FROM filtered
    JOIN latest USING (year)
)
SELECT section_id, section_name, municipio_id, municipio_nombre, year, value, municipal_average
FROM scored
WHERE {where_condition}
ORDER BY value DESC, section_name
LIMIT {int(payload.limit)}
""".strip()
            return BuiltSql(sql, [metric.view, "marts.agent_section_lookup"], {"metric": metric.metric_id, "value_label": metric.label, "condition": condition.model_dump()})
        temporal_column = "year"
        extra_filters = ""
        if metric.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"}:
            temporal_column = "election_year"
            extra_filters = " AND election_type = 'MUNICIPALES'"
        year_filter = f"AND {temporal_column} = {int(payload.year)}" if payload.year else ""
        where_condition = self._condition_sql("value", condition.operator, condition.value)
        sql = f"""
WITH filtered AS (
    SELECT
        section_id,
        section_name,
        municipio_id,
        municipio_nombre,
        {temporal_column} AS year,
        {metric.field} AS value
    FROM {metric.view}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {year_filter}
      {extra_filters}
      AND {metric.field} IS NOT NULL
),
latest AS (
    SELECT MAX(year) AS year FROM filtered
),
scored AS (
    SELECT filtered.*, AVG(value) OVER () AS municipal_average, PERCENT_RANK() OVER (ORDER BY value) AS pct_rank
    FROM filtered
    JOIN latest USING (year)
)
SELECT section_id, section_name, municipio_id, municipio_nombre, year, value, municipal_average
FROM scored
WHERE {where_condition}
ORDER BY value DESC, section_name
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, [metric.view], {"metric": metric.metric_id, "value_label": metric.label, "condition": condition.model_dump()})

    def section_profile(self, payload: SectionProfileInput) -> BuiltSql:
        section_filter = self._section_filter(payload.section)
        year_filter = f"AND profile.year = {int(payload.year)}" if payload.year else ""
        sql = f"""
WITH target AS (
    SELECT section_id, section_name, municipio_id, municipio_nombre
    FROM marts.agent_section_lookup
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND ({section_filter})
    ORDER BY section_name
    LIMIT 1
),
latest_profile AS (
    SELECT MAX(year) AS year FROM marts.agent_section_profile WHERE municipio_id = {self._literal(payload.municipio_id)}
),
latest_income AS (
    SELECT MAX(year) AS year FROM marts.agent_income_sources WHERE municipio_id = {self._literal(payload.municipio_id)}
),
latest_housing AS (
    SELECT MAX(year) AS year FROM marts.agent_housing_profile WHERE municipio_id = {self._literal(payload.municipio_id)}
),
latest_election AS (
    SELECT MAX(election_year) AS election_year FROM marts.agent_electoral_summary WHERE municipio_id = {self._literal(payload.municipio_id)} AND election_type = 'MUNICIPALES'
)
SELECT
    target.section_id,
    target.section_name,
    target.municipio_id,
    target.municipio_nombre,
    profile.year,
    profile.population_total,
    profile.average_age,
    income.income_individual,
    income.income_household,
    electoral.election_year,
    electoral.winner_party,
    electoral.participation_pct,
    electoral.abstention_pct,
    housing.market_price_estimated_m2,
    housing.residential_pressure_index,
    housing.building_intensity
FROM target
LEFT JOIN marts.agent_section_profile profile ON profile.section_id = target.section_id AND profile.municipio_id = target.municipio_id
LEFT JOIN latest_profile ON latest_profile.year = profile.year
LEFT JOIN marts.agent_income_sources income ON income.section_id = target.section_id AND income.municipio_id = target.municipio_id
LEFT JOIN latest_income ON latest_income.year = income.year
LEFT JOIN marts.agent_electoral_summary electoral ON electoral.section_id = target.section_id AND electoral.municipio_id = target.municipio_id
LEFT JOIN latest_election ON latest_election.election_year = electoral.election_year
LEFT JOIN marts.agent_housing_profile housing ON housing.section_id = target.section_id AND housing.municipio_id = target.municipio_id
LEFT JOIN latest_housing ON latest_housing.year = housing.year
WHERE (profile.year = latest_profile.year {year_filter} OR profile.year IS NULL)
  AND (income.year = latest_income.year OR income.year IS NULL)
  AND (electoral.election_year = latest_election.election_year OR electoral.election_year IS NULL)
  AND (electoral.election_type = 'MUNICIPALES' OR electoral.election_type IS NULL)
  AND (housing.year = latest_housing.year OR housing.year IS NULL)
LIMIT 1
""".strip()
        return BuiltSql(sql, ["marts.agent_section_lookup", "marts.agent_section_profile", "marts.agent_income_sources", "marts.agent_electoral_summary", "marts.agent_housing_profile"], {"section": payload.section})

    def party_strength(self, payload: PartyStrengthInput) -> BuiltSql:
        election_type = self._election_type(payload.election_type)
        year_filter = f"AND election_year = {int(payload.election_year)}" if payload.election_year else ""
        if payload.historical:
            sql = f"""
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    canonical_party AS party,
    ROUND(AVG(vote_pct)::numeric, 2) AS value,
    COUNT(*) AS elections_included,
    MIN(election_year) AS first_year,
    MAX(election_year) AS last_year
FROM marts.agent_electoral_results
WHERE municipio_id = {self._literal(payload.municipio_id)}
  AND election_type = {self._literal(election_type)}
  AND UPPER(canonical_party) = {self._literal(payload.party.upper())}
  AND vote_pct IS NOT NULL
GROUP BY section_id, section_name, municipio_id, municipio_nombre, canonical_party
ORDER BY value DESC, section_name
LIMIT {int(payload.limit)}
""".strip()
        else:
            sql = f"""
WITH latest AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_results
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND election_type = {self._literal(election_type)}
      {year_filter}
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    canonical_party AS party,
    election_year AS year,
    vote_pct AS value
FROM marts.agent_electoral_results
JOIN latest USING (election_year)
WHERE municipio_id = {self._literal(payload.municipio_id)}
  AND election_type = {self._literal(election_type)}
  AND UPPER(canonical_party) = {self._literal(payload.party.upper())}
  AND vote_pct IS NOT NULL
ORDER BY value DESC, section_name
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, ["marts.agent_electoral_results"], {"metric": "vote_pct", "value_label": f"voto a {payload.party.upper()}", "party": payload.party.upper()})

    def persistent_winner(self, payload: PersistentWinnerInput) -> BuiltSql:
        election_filter = f"AND election_type = {self._literal(self._election_type(payload.election_type))}" if payload.election_type else ""
        exact_filter = "WHERE always_wins OR NOT EXISTS (SELECT 1 FROM section_counts WHERE always_wins)" if payload.require_all_available else ""
        sql = f"""
WITH winners AS (
    SELECT section_id, section_name, election_id, election_label, winner_party
    FROM marts.agent_electoral_summary
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {election_filter}
),
section_counts AS (
    SELECT
        section_id,
        section_name,
        COUNT(*) AS elections_checked,
        COUNT(*) FILTER (WHERE UPPER(winner_party) = {self._literal(payload.party.upper())}) AS party_wins,
        STRING_AGG(DISTINCT election_label, ', ' ORDER BY election_label) AS elections_included
    FROM winners
    GROUP BY section_id, section_name
),
ranked AS (
    SELECT
        *,
        ROUND(party_wins::numeric / NULLIF(elections_checked, 0) * 100, 2) AS value,
        party_wins = elections_checked AS always_wins
    FROM section_counts
)
SELECT *
FROM ranked
{exact_filter}
ORDER BY always_wins DESC, party_wins DESC, value DESC, section_name
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, ["marts.agent_electoral_summary"], {"metric": "winner_party", "value_label": f"victorias de {payload.party.upper()}", "party": payload.party.upper()})

    def historical_party_average(self, payload: HistoricalPartyAverageInput) -> BuiltSql:
        election_filter = f"AND election_type = {self._literal(self._election_type(payload.election_type))}" if payload.election_type else ""
        section_join = ""
        section_filter = ""
        group_cols = "canonical_party"
        select_cols = "canonical_party AS party"
        order_name = "party"
        if payload.section:
            section_join = f"""
JOIN (
    SELECT section_id
    FROM marts.agent_section_lookup
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND ({self._section_filter(payload.section)})
    LIMIT 1
) target USING (section_id)
"""
        if payload.party:
            section_filter = f"AND UPPER(canonical_party) = {self._literal(payload.party.upper())}"
            group_cols = "section_id, section_name, canonical_party"
            select_cols = "section_id, section_name, canonical_party AS party"
            order_name = "section_name"
        average_expr = "SUM(votes)::numeric / NULLIF(SUM(valid_votes), 0) * 100" if payload.average_type == "weighted_by_valid_votes" else "AVG(vote_pct)"
        sql = f"""
SELECT
    {select_cols},
    ROUND(({average_expr})::numeric, 2) AS value,
    COUNT(*) AS elections_included,
    MIN(election_year) AS first_year,
    MAX(election_year) AS last_year,
    ROUND(MIN(vote_pct)::numeric, 2) AS min_vote_pct,
    ROUND(MAX(vote_pct)::numeric, 2) AS max_vote_pct
FROM marts.agent_electoral_results
{section_join}
WHERE municipio_id = {self._literal(payload.municipio_id)}
  {election_filter}
  {section_filter}
  AND vote_pct IS NOT NULL
GROUP BY {group_cols}
ORDER BY value DESC, {order_name}
LIMIT {int(payload.limit)}
""".strip()
        return BuiltSql(sql, ["marts.agent_electoral_results", "marts.agent_section_lookup"] if payload.section else ["marts.agent_electoral_results"], {"metric": "vote_pct", "value_label": "media historica de voto"})

    def age_cohort_projection(self, payload: AgeCohortProjectionInput) -> BuiltSql:
        if payload.target_year and payload.target_age and (payload.source_year or payload.source_age):
            source_year = payload.source_year or payload.target_year - 2
            source_age = payload.source_age or max(payload.target_age - 2, 0)
            limit_clause = "" if payload.group_by == "municipality" else f"LIMIT {int(payload.limit)}"
            section_cols = "section_id, section_name," if payload.group_by != "municipality" else ""
            section_group = "section_id, section_name," if payload.group_by != "municipality" else ""
            sql = f"""
WITH source AS (
    SELECT
        {section_cols}
        municipio_id,
        municipio_nombre,
        year AS source_year,
        SUM(people)::numeric AS source_age_band_population
    FROM marts.agent_population_age
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND year = {int(source_year)}
      AND gender IN ('H', 'M')
      AND age_min <= {int(source_age)}
      AND age_max >= {int(source_age)}
    GROUP BY {section_group} municipio_id, municipio_nombre, year
),
estimated AS (
    SELECT
        *,
        {int(source_age)}::integer AS source_age,
        {int(payload.target_year)}::integer AS target_year,
        {int(payload.target_age)}::integer AS target_age,
        ROUND(source_age_band_population / NULLIF((5), 0))::bigint AS value
    FROM source
)
SELECT
    *,
    SUM(value) OVER ()::bigint AS municipality_total
FROM estimated
ORDER BY value DESC
{limit_clause}
""".strip()
            return BuiltSql(sql, ["marts.agent_population_age"], {"metric": "population_total", "value_label": f"personas que tendran {payload.target_age} anos", "estimated": True})
        min_age = payload.min_age if payload.min_age is not None else 65
        max_age = payload.max_age if payload.max_age is not None else 120
        year_filter = f"AND year = {int(payload.source_year or payload.target_year)}" if (payload.source_year or payload.target_year) else ""
        section_cols = "section_id, section_name," if payload.group_by != "municipality" else ""
        section_group = "section_id, section_name," if payload.group_by != "municipality" else ""
        limit_clause = "" if payload.group_by == "municipality" else f"LIMIT {int(payload.limit)}"
        sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM marts.agent_population_age
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {year_filter}
)
SELECT
    {section_cols}
    municipio_id,
    municipio_nombre,
    year,
    SUM(people)::bigint AS value,
    SUM(SUM(people)) OVER ()::bigint AS municipality_total
FROM marts.agent_population_age
JOIN latest USING (year)
WHERE municipio_id = {self._literal(payload.municipio_id)}
  AND gender IN ('H', 'M')
  AND age_max >= {int(min_age)}
  AND age_min <= {int(max_age)}
GROUP BY {section_group} municipio_id, municipio_nombre, year
ORDER BY value DESC
{limit_clause}
""".strip()
        return BuiltSql(sql, ["marts.agent_population_age"], {"metric": "population_total", "value_label": f"personas de {min_age} a {max_age} anos", "estimated": False})

    def ecological_vote_profile_by_age_group(self, payload: EcologicalVoteProfileByAgeGroupInput) -> BuiltSql:
        min_age = payload.min_age if payload.min_age is not None else 0
        max_age = payload.max_age if payload.max_age is not None else 120
        if min_age > max_age:
            raise ValueError("min_age cannot be greater than max_age.")
        election_type = self._election_type(payload.election_type)
        year_filter = f"AND election_year = {int(payload.election_year)}" if payload.election_year else ""
        main_party_filter = "AND party_total_votes >= valid_votes_total * 0.02" if payload.party_scope == "main" else ""
        sql = f"""
WITH population_year AS MATERIALIZED (
    SELECT MAX(year) AS year
    FROM marts.agent_population_age
    WHERE municipio_id = {self._literal(payload.municipio_id)}
),
section_age AS MATERIALIZED (
    SELECT
        age.section_id,
        MAX(age.section_name) AS section_name,
        MAX(age.municipio_id) AS municipio_id,
        MAX(age.municipio_nombre) AS municipio_nombre,
        SUM(age.people) FILTER (WHERE age.age_max >= {int(min_age)} AND age.age_min <= {int(max_age)})::numeric AS age_group_population,
        SUM(age.people)::numeric AS total_population
    FROM marts.agent_population_age age
    JOIN population_year USING (year)
    WHERE age.municipio_id = {self._literal(payload.municipio_id)}
      AND age.gender IN ('H', 'M')
    GROUP BY age.section_id
),
age_profile AS MATERIALIZED (
    SELECT
        *,
        age_group_population / NULLIF(total_population, 0) AS age_group_share
    FROM section_age
    WHERE age_group_population > 0
      AND total_population > 0
),
age_threshold AS (
    SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY age_group_share) AS high_age_threshold
    FROM age_profile
),
election_year AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_results
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      AND election_type = {self._literal(election_type)}
      {year_filter}
),
electoral AS MATERIALIZED (
    SELECT
        results.section_id,
        results.section_name,
        results.canonical_party AS party,
        results.election_year,
        results.vote_pct::numeric AS vote_pct,
        results.votes::numeric AS votes,
        results.valid_votes::numeric AS valid_votes
    FROM marts.agent_electoral_results results
    JOIN election_year USING (election_year)
    WHERE results.municipio_id = {self._literal(payload.municipio_id)}
      AND results.election_type = {self._literal(election_type)}
      AND results.vote_pct IS NOT NULL
      AND results.canonical_party IS NOT NULL
),
party_totals AS (
    SELECT
        party,
        SUM(votes) AS party_total_votes,
        SUM(valid_votes) AS valid_votes_total
    FROM electoral
    GROUP BY party
),
joined AS MATERIALIZED (
    SELECT
        electoral.party,
        electoral.section_id,
        COALESCE(electoral.section_name, age_profile.section_name) AS section_name,
        age_profile.municipio_id,
        age_profile.municipio_nombre,
        electoral.election_year,
        electoral.vote_pct,
        age_profile.age_group_population,
        age_profile.total_population,
        age_profile.age_group_share,
        party_totals.party_total_votes,
        party_totals.valid_votes_total,
        age_threshold.high_age_threshold
    FROM electoral
    JOIN age_profile USING (section_id)
    JOIN party_totals USING (party)
    CROSS JOIN age_threshold
),
party_profile AS (
    SELECT
        party,
        MAX(municipio_id) AS municipio_id,
        MAX(municipio_nombre) AS municipio_nombre,
        MAX(election_year) AS election_year,
        ROUND((SUM(vote_pct * age_group_population) / NULLIF(SUM(age_group_population), 0))::numeric, 2) AS weighted_vote_pct,
        ROUND(AVG(vote_pct) FILTER (WHERE age_group_share >= high_age_threshold)::numeric, 2) AS average_vote_pct_in_high_age_sections,
        ROUND(CORR(age_group_share, vote_pct)::numeric, 4) AS correlation_with_age_group_share,
        ROUND(SUM(age_group_population)::numeric, 0) AS weighted_age_population,
        MAX(party_total_votes) AS party_total_votes,
        MAX(valid_votes_total) AS valid_votes_total
    FROM joined
    GROUP BY party
),
top_sections AS (
    SELECT
        STRING_AGG(section_name || ' (' || ROUND((age_group_share * 100)::numeric, 1)::text || '%)', ', ' ORDER BY age_group_share DESC, section_name) AS top_sections
    FROM (
        SELECT
            section_name,
            age_group_share,
            ROW_NUMBER() OVER (ORDER BY age_group_share DESC, section_name) AS rank
        FROM age_profile
    ) ranked_sections
    WHERE rank <= 5
)
SELECT
    party,
    municipio_id,
    municipio_nombre,
    election_year,
    {int(min_age)}::integer AS min_age,
    {int(max_age)}::integer AS max_age,
    weighted_vote_pct,
    average_vote_pct_in_high_age_sections,
    correlation_with_age_group_share,
    top_sections,
    weighted_vote_pct AS value
FROM party_profile
CROSS JOIN top_sections
WHERE weighted_vote_pct IS NOT NULL
  {main_party_filter}
ORDER BY weighted_vote_pct DESC, party
LIMIT 10
""".strip()
        age_label = self._age_group_label(payload.min_age, payload.max_age)
        return BuiltSql(
            sql,
            [
                "marts.agent_population_age",
                "marts.agent_section_profile",
                "marts.agent_electoral_results",
                "marts.agent_electoral_summary",
            ],
            {
                "metric": "ecological_vote_profile_by_age_group",
                "value_label": f"perfil electoral estimado de {age_label}",
                "age_group_label": age_label,
                "min_age": payload.min_age,
                "max_age": payload.max_age,
                "election_type": election_type,
                "election_year": payload.election_year,
                "party_scope": payload.party_scope,
                "method": payload.method,
            },
        )

    def cross_metric_ranking(self, payload: CrossMetricRankingInput) -> BuiltSql:
        if len(payload.metrics) < 2:
            raise ValueError("At least two metrics are required.")
        metric_a = payload.metrics[0]
        metric_b = payload.metrics[1]
        sql = self._cross_metric_sql(payload, metric_a.metric, metric_a.direction, metric_a.weight, metric_b.metric, metric_b.direction, metric_b.weight, metric_b.party or metric_a.party)
        sources = sorted({self.metric(metric_a.metric).view, self.metric(metric_b.metric).view if metric_b.metric != "vote_pct" else "marts.agent_electoral_results"})
        concept = self._cross_metric_concept(payload)
        value_label = {
            "demographic_polarization": "Índice de polarización demográfica",
            "demographic_homogeneity": "Índice de homogeneidad demográfica",
            "housing_opportunity": "Índice de oportunidad inmobiliaria",
            "housing_revaluation_potential": "Índice de potencial de revalorización",
        }.get(concept, "Índice combinado")
        return BuiltSql(
            sql,
            sources,
            {
                "metric": "cross_metric_score",
                "value_label": value_label,
                "analysis_concept": concept,
                "components": [metric.model_dump() for metric in payload.metrics],
            },
        )

    def correlation_analysis(self, payload: CorrelationAnalysisInput) -> BuiltSql:
        x = self.metric(payload.x_metric)
        y = self.metric(payload.y_metric)
        if payload.method != "pearson":
            raise ValueError("Only pearson is currently supported by the SQL builder.")
        x_temporal = "election_year" if x.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"} else "year"
        y_temporal = "election_year" if y.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"} else "year"
        x_year_filter = f"AND {x_temporal} = {int(payload.year)}" if payload.year else ""
        y_year_filter = f"AND {y_temporal} = {int(payload.year)}" if payload.year else ""
        x_election_filter = "AND election_type = 'MUNICIPALES'" if x.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"} else ""
        y_election_filter = "AND election_type = 'MUNICIPALES'" if y.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"} else ""
        sql = f"""
WITH x_latest AS (
    SELECT MAX({x_temporal}) AS year FROM {x.view} WHERE municipio_id = {self._literal(payload.municipio_id)} {x_year_filter} {x_election_filter}
),
y_latest AS (
    SELECT MAX({y_temporal}) AS year FROM {y.view} WHERE municipio_id = {self._literal(payload.municipio_id)} {y_year_filter} {y_election_filter}
),
x_values AS (
    SELECT section_id, section_name, municipio_id, municipio_nombre, {x.field}::numeric AS x_value
    FROM {x.view} AS x_source
    JOIN x_latest ON x_latest.year = x_source.{x_temporal}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {x_election_filter}
      AND {x.field} IS NOT NULL
),
y_values AS (
    SELECT section_id, {y.field}::numeric AS y_value
    FROM {y.view} AS y_source
    JOIN y_latest ON y_latest.year = y_source.{y_temporal}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {y_election_filter}
      AND {y.field} IS NOT NULL
),
joined AS (
    SELECT x_values.section_id, x_values.section_name, x_values.municipio_nombre, x_value, y_value
    FROM x_values
    JOIN y_values USING (section_id)
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    x_value,
    y_value,
    CORR(x_value, y_value) OVER () AS correlation
FROM joined
ORDER BY section_name
""".strip()
        return BuiltSql(sql, [x.view, y.view], {"metric": "correlation", "x_metric": x.metric_id, "y_metric": y.metric_id, "value_label": "correlacion"})

    def _cross_metric_sql(self, payload: CrossMetricRankingInput, metric_a: str, direction_a: str, weight_a: float, metric_b: str, direction_b: str, weight_b: float, party: str | None) -> str:
        metric_defs = [self.metric(metric_a), self.metric(metric_b)]
        joins: list[str] = []
        selects: list[str] = []
        latest_ctes: list[str] = []
        for idx, metric in enumerate(metric_defs, start=1):
            alias = f"m{idx}"
            if metric.view == "marts.mv_electoral_behavior":
                party_clause = ""
                latest_ctes.append(
                    f"latest_{idx} AS (SELECT MAX(anio) AS year FROM marts.mv_electoral_behavior WHERE LEFT(seccion_id::text, 5) = {self._literal(payload.municipio_id)})"
                )
                joins.append(f"""
{alias}_values AS (
    SELECT
        behavior.seccion_id::text AS section_id,
        COALESCE(lookup.section_name, behavior.seccion_id::text) AS section_name,
        {self._literal(payload.municipio_id)} AS municipio_id,
        'Mijas' AS municipio_nombre,
        behavior.{metric.field}::numeric AS value_{idx}
    FROM marts.mv_electoral_behavior AS behavior
    JOIN latest_{idx} ON latest_{idx}.year = behavior.anio
    LEFT JOIN marts.agent_section_lookup lookup ON lookup.section_id = behavior.seccion_id::text
    WHERE LEFT(behavior.seccion_id::text, 5) = {self._literal(payload.municipio_id)}
      AND behavior.{metric.field} IS NOT NULL
)
""")
                selects.append(f"value_{idx}")
                continue
            temporal_col = "election_year" if metric.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"} else "year"
            year_clause = f"AND {temporal_col} = {int(payload.year)}" if payload.year else ""
            election_clause = "AND election_type = 'MUNICIPALES'" if metric.view in {"marts.agent_electoral_summary", "marts.agent_electoral_results"} else ""
            party_clause = f"AND UPPER(canonical_party) = {self._literal(str(party).upper())}" if metric.metric_id == "vote_pct" and party else ""
            latest_ctes.append(f"latest_{idx} AS (SELECT MAX({temporal_col}) AS year FROM {metric.view} WHERE municipio_id = {self._literal(payload.municipio_id)} {year_clause} {election_clause} {party_clause})")
            joins.append(f"""
{alias}_values AS (
    SELECT section_id, section_name, municipio_id, municipio_nombre, {metric.field}::numeric AS value_{idx}
    FROM {metric.view} AS {alias}_source
    JOIN latest_{idx} ON latest_{idx}.year = {alias}_source.{temporal_col}
    WHERE municipio_id = {self._literal(payload.municipio_id)}
      {election_clause}
      {party_clause}
      AND {metric.field} IS NOT NULL
)
""")
            selects.append(f"value_{idx}")
        order_a = "DESC" if direction_a == "low" else "ASC"
        order_b = "DESC" if direction_b == "low" else "ASC"
        return f"""
WITH {', '.join(latest_ctes)},
{','.join(joins)},
joined AS (
    SELECT
        m1_values.section_id,
        m1_values.section_name,
        m1_values.municipio_nombre,
        m1_values.value_1,
        m2_values.value_2
    FROM m1_values
    JOIN m2_values USING (section_id)
),
scored AS (
    SELECT
        *,
        PERCENT_RANK() OVER (ORDER BY value_1 {order_a}) AS component_1,
        PERCENT_RANK() OVER (ORDER BY value_2 {order_b}) AS component_2
    FROM joined
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    value_1,
    value_2,
    ROUND(component_1::numeric, 4) AS component_1,
    ROUND(component_2::numeric, 4) AS component_2,
    ROUND((component_1 * {float(weight_a)} + component_2 * {float(weight_b)})::numeric / NULLIF({float(weight_a) + float(weight_b)}, 0), 4) AS value
FROM scored
ORDER BY value DESC, section_name
LIMIT {int(payload.limit)}
""".strip()

    def _cross_metric_concept(self, payload: CrossMetricRankingInput) -> str | None:
        signature = tuple((item.metric, item.direction) for item in payload.metrics[:2])
        if signature == (("population_under_30_pct", "high"), ("population_over_65_pct", "high")):
            return "demographic_polarization"
        if signature == (("population_under_30_pct", "low"), ("population_over_65_pct", "low")):
            return "demographic_homogeneity"
        if signature == (("market_to_cadastral_ratio", "low"), ("residential_pressure_index", "low")):
            return "housing_opportunity"
        if signature == (("market_to_cadastral_ratio", "low"), ("building_intensity", "high")):
            return "housing_revaluation_potential"
        return None

    def _condition_sql(self, field: str, operator: str, value: Any) -> str:
        if operator in {">", ">=", "<", "<=", "="}:
            return f"{field} {operator} {self._numeric(value)}"
        if operator == "between":
            low, high = value
            return f"{field} BETWEEN {self._numeric(low)} AND {self._numeric(high)}"
        if operator == "above_municipal_average":
            return f"{field} > municipal_average"
        if operator == "below_municipal_average":
            return f"{field} < municipal_average"
        if operator == "top_quantile":
            return f"pct_rank >= {1 - float(value or 0.75)}"
        if operator == "bottom_quantile":
            return f"pct_rank <= {float(value or 0.25)}"
        raise ValueError(f"Unsupported operator `{operator}`.")

    def _section_filter(self, section: str) -> str:
        cleaned = section.strip()
        like = "%" + cleaned.lower().replace("'", "''") + "%"
        clauses = [
            f"LOWER(section_id) = {self._literal(cleaned.lower())}",
            f"LOWER(section_name) LIKE {self._literal(like)}",
            f"LOWER(display_name) LIKE {self._literal(like)}",
        ]
        digits = "".join(ch for ch in cleaned if ch.isdigit())
        if digits:
            clauses.append(f"section_number = {int(digits)}")
        return " OR ".join(clauses)

    def _section_lineage_values(self, municipality_id: str) -> str:
        rows = [row for row in self.section_lineage.get("lineages", []) if str(row.get("municipio_id")) == str(municipality_id)]
        if not rows:
            return "('__NO_MUNICIPIO__', '__NO_LINEAGE__', '__NO_LINEAGE__', NULL, '__NO_BASE__', NULL, '__NO_CURRENT__', '__NO_REL__', NULL)"
        values: list[str] = []
        for row in rows:
            values.append(
                "("
                f"{self._literal(str(row.get('municipio_id', '')))}, "
                f"{self._literal(str(row.get('lineage_group_id', '')))}, "
                f"{self._literal(str(row.get('lineage_group_name', '')))}, "
                f"{int(row['base_year']) if row.get('base_year') is not None else 'NULL'}, "
                f"{self._literal(str(row.get('base_section_id', '')))}, "
                f"{int(row['current_year']) if row.get('current_year') is not None else 'NULL'}, "
                f"{self._literal(str(row.get('current_section_id', '')))}, "
                f"{self._literal(str(row.get('relationship_type', '')))}, "
                f"{self._literal(str(row.get('notes', ''))) if row.get('notes') is not None else 'NULL'}"
                ")"
            )
        return ",\n        ".join(values)

    def _election_type(self, election_type: str | None) -> str:
        if not election_type:
            return "MUNICIPALES"
        normalized = election_type.strip().upper()
        aliases = {"MUNICIPAL": "MUNICIPALES", "MUNICIPALES": "MUNICIPALES", "LOCAL": "MUNICIPALES"}
        return aliases.get(normalized, normalized)

    def _age_group_label(self, min_age: int | None, max_age: int | None) -> str:
        if min_age is not None and max_age is not None:
            return f"personas de {min_age} a {max_age} anos"
        if min_age is not None:
            return f"personas mayores de {min_age} anos"
        if max_age is not None:
            return f"personas menores de {max_age} anos"
        return "la poblacion por edad"

    def _literal(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _numeric(self, value: Any) -> str:
        return str(float(value))
