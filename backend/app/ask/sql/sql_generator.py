import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from app.ask.interpreter import AnalyticalIntent
from app.ask.semantic_layer import AnalyticalOperation, SemanticCatalog, SemanticOperationInterpreter
from app.services.local_analyst_service import extract_party, normalize


ExpectedOutput = Literal["single_value", "ranking", "comparison", "table", "chart"]


@dataclass(frozen=True, slots=True)
class SemanticPlan:
    intent: str
    question: str
    sql: str
    expectedOutput: ExpectedOutput
    methodology: str
    confidence: Literal["high", "medium", "low"]
    sources: list[str]
    chartSpec: dict[str, Any] | None = None
    caveats: list[str] | None = None


class SqlGenerator:
    def __init__(self) -> None:
        catalog_path = Path(__file__).resolve().parents[1] / "semantic_catalog.yaml"
        lineage_path = Path(__file__).resolve().parents[1] / "section_lineage.yaml"
        self.catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        self.section_lineage = yaml.safe_load(lineage_path.read_text(encoding="utf-8")) if lineage_path.exists() else {"lineages": []}
        self.semantic_catalog = SemanticCatalog(catalog_path)
        self.operation_interpreter = SemanticOperationInterpreter(self.semantic_catalog)

    @property
    def approved_relations(self) -> set[str]:
        return self.semantic_catalog.approved_relations

    def generate(
        self,
        question: str,
        *,
        analytical_intent: AnalyticalIntent | None = None,
        active_municipality: str | None = None,
        resolved_references: dict[str, Any] | None = None,
    ) -> SemanticPlan | None:
        text = normalize(question)
        municipality_id = self._municipality_id(active_municipality)
        resolved_references = resolved_references or {}

        if self._is_dataset_inventory_question(text):
            return None

        followup_plan = self._contextual_followup_plan(question, municipality_id, resolved_references)
        if followup_plan:
            return followup_plan

        population_plan = self._population_profile_plan(question, municipality_id)
        if population_plan:
            return population_plan

        if self._asks_age_turnout_or_abstention(text):
            age_range = self._extract_age_range(question)
            if age_range:
                election_type = self._extract_election_type(question) or "municipales"
                year = self._extract_year(question) or 2023
                return self._age_abstention_plan(question, municipality_id, year, election_type, age_range)

        semantic_operation = self.operation_interpreter.interpret(
            question,
            municipio_id=municipality_id,
            active_year=resolved_references.get("lastYear"),
            last_metric=resolved_references.get("lastMetric"),
            last_party=resolved_references.get("lastParty"),
        )
        if semantic_operation:
            plan = self._plan_from_semantic_operation(question, semantic_operation)
            if plan:
                return plan

        if analytical_intent and analytical_intent.intent != "unknown":
            plan = self._plan_from_analytical_intent(question, analytical_intent, municipality_id)
            if plan:
                return plan

        direct_age_plan = self._direct_age_population_plan(question, municipality_id)
        if direct_age_plan:
            return direct_age_plan

        if re.search(r"gana.*siempre|siempre.*gana|fuerza.*siempre", text):
            party = extract_party(question) or "PSOE"
            return self._always_wins_plan(question, municipality_id, party)

        if re.search(r"poblacion joven|jovenes|menores de 30", text) and re.search(r"abstencion|no vot|participacion", text):
            return self._young_abstention_plan(question, municipality_id, self._extract_year(question) or 2023)

        if re.search(r"media|promedio|histor", text) and re.search(r"voto|porcentaje", text) and extract_party(question):
            return self._historical_party_average_plan(question, municipality_id, extract_party(question) or "PP")

        if re.search(r"renta alta|alta renta|renta.*alta", text) and re.search(r"voto alto|alto.*voto|voto.*pp|pp", text):
            party = extract_party(question) or "PP"
            return self._high_income_high_party_plan(question, municipality_id, party, self._extract_year(question) or 2023)

        sections = resolved_references.get("resolvedSections") or []
        if sections and re.search(r"gan[oó]|gano|ganaron|fuerza m[aá]s votada", text):
            party = extract_party(question) or "PP"
            return self._previous_sections_winner_count_plan(question, sections, party, self._extract_year(question) or 2023)

        return None

    def _population_profile_plan(self, question: str, municipality_id: str) -> SemanticPlan | None:
        text = normalize(question)
        asks_growth = bool(re.search(r"crecid|crecimiento|aumentad|ganado|perdid|perdido|decrecid|decrecimiento|growth|grown|lost", text))
        if not re.search(r"poblacion|habitantes|demograf", text) and not asks_growth:
            return None
        if asks_growth and re.search(r"zonas|secciones|areas|barrios|poblacion|habitantes", text):
            operation = self.operation_interpreter.interpret(question, municipio_id=municipality_id)
            if operation and operation.operation == "population_growth":
                return self._semantic_section_growth_plan(question, operation)
        if re.search(r"evolucion|evolucionado|ha evolucionado|desde|tendencia", text):
            start_year = self._extract_year(question) or 2021
            return self._municipality_population_trend_plan(question, municipality_id, start_year)
        if re.search(r"poblacion total.*mijas|mijas.*poblacion total|habitantes.*mijas|mijas.*habitantes", text):
            return self._municipality_population_total_plan(question, municipality_id)
        threshold = self._extract_population_threshold(text)
        if threshold is not None and re.search(r"superan|mas de|más de|por encima|mayor(?:es)? que", text):
            return self._population_threshold_sections_plan(question, municipality_id, threshold)
        return None

    def _extract_population_threshold(self, text: str) -> int | None:
        match = re.search(r"(\d{1,3}(?:[\.\s]\d{3})+|\d{4,6})\s*(?:habitantes|personas)?", text)
        if not match:
            return None
        return int(re.sub(r"\D", "", match.group(1)))

    def _municipality_population_total_plan(self, question: str, municipality_id: str) -> SemanticPlan:
        sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM marts.agent_section_profile
    WHERE municipio_id = '{municipality_id}'
),
current_total AS (
    SELECT
        municipio_id,
        municipio_nombre,
        year,
        SUM(population_total)::bigint AS population_total
    FROM marts.agent_section_profile
    JOIN latest USING (year)
    WHERE municipio_id = '{municipality_id}'
    GROUP BY municipio_id, municipio_nombre, year
),
first_total AS (
    SELECT
        year AS first_year,
        SUM(population_total)::bigint AS first_population_total
    FROM marts.agent_section_profile
    WHERE municipio_id = '{municipality_id}'
    GROUP BY year
    ORDER BY year ASC
    LIMIT 1
)
SELECT
    current_total.municipio_id,
    current_total.municipio_nombre,
    current_total.year,
    current_total.population_total,
    first_total.first_year,
    first_total.first_population_total,
    ROUND(
        (current_total.population_total - first_total.first_population_total)::numeric
        / NULLIF(first_total.first_population_total, 0) * 100,
        2
    ) AS growth_pct_since_first_year
FROM current_total
CROSS JOIN first_total
""".strip()
        return SemanticPlan(
            intent="municipality_population_total",
            question=question,
            sql=sql,
            expectedOutput="single_value",
            methodology="Agrego la población residente de todas las secciones censales del municipio y uso el último año disponible.",
            confidence="high",
            sources=["marts.agent_section_profile"],
            caveats=[],
        )

    def _municipality_population_trend_plan(self, question: str, municipality_id: str, start_year: int) -> SemanticPlan:
        sql = f"""
SELECT
    municipio_id,
    municipio_nombre,
    year,
    SUM(population_total)::bigint AS population_total
FROM marts.agent_section_profile
WHERE municipio_id = '{municipality_id}'
  AND year >= {int(start_year)}
GROUP BY municipio_id, municipio_nombre, year
ORDER BY year
""".strip()
        return SemanticPlan(
            intent="municipality_population_trend",
            question=question,
            sql=sql,
            expectedOutput="chart",
            methodology="Sumo la población de todas las secciones para cada año disponible y comparo el primer y último punto de la serie.",
            confidence="high",
            sources=["marts.agent_section_profile"],
            chartSpec={"type": "line", "title": "Evolución de la población de Mijas", "x": "year", "y": "population_total"},
            caveats=[],
        )

    def _population_threshold_sections_plan(self, question: str, municipality_id: str, threshold: int) -> SemanticPlan:
        sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM marts.agent_section_profile
    WHERE municipio_id = '{municipality_id}'
)
SELECT
    section_id AS section_id,
    section_name,
    municipio_nombre,
    year,
    population_total
FROM marts.agent_section_profile
JOIN latest USING (year)
WHERE municipio_id = '{municipality_id}'
  AND population_total > {int(threshold)}
ORDER BY population_total DESC, section_name
""".strip()
        return SemanticPlan(
            intent="population_threshold_sections",
            question=question,
            sql=sql,
            expectedOutput="table",
            methodology=f"Filtro las secciones del último año disponible y conservo solo las que superan {threshold:,} habitantes.".replace(",", "."),
            confidence="high",
            sources=["marts.agent_section_profile"],
            chartSpec={"type": "bar", "title": f"Secciones con más de {threshold:,} habitantes".replace(",", "."), "x": "section_name", "y": "population_total"},
            caveats=[],
        )

    def _plan_from_semantic_operation(self, question: str, operation: AnalyticalOperation) -> SemanticPlan | None:
        if not operation.supported:
            return None
        if operation.operation == "persistent_winner":
            return self._semantic_persistent_winners_plan(question, operation)
        if operation.operation == "party_strength":
            return self._semantic_party_strength_plan(question, operation)
        if operation.operation == "population_growth":
            return self._semantic_section_growth_plan(question, operation)
        if operation.operation == "compare_years":
            return self._semantic_compare_years_plan(question, operation)
        if operation.operation == "age_cohort_projection":
            return self._future_age_cohort_projection_plan(question, operation.municipio_id, operation)
        if operation.operation == "aggregate_municipality":
            return self._semantic_aggregate_municipality_plan(question, operation)
        if operation.operation == "cross_metric_ranking":
            return self._semantic_cross_metric_ranking_plan(question, operation)
        if operation.operation == "historical_party_average":
            return self._historical_party_average_plan(question, operation.municipio_id, operation.party or "PP")
        if operation.operation == "rank_sections":
            return self._semantic_rank_sections_plan(question, operation)
        return None

    def _future_age_cohort_projection_plan(
        self,
        question: str,
        municipality_id: str,
        operation: AnalyticalOperation | None = None,
    ) -> SemanticPlan:
        target_year = int(operation.year) if operation and operation.year else self._extract_year(question) or 2027
        target_age = int((operation.filters or {}).get("targetAge") or 18) if operation else 18
        source_year = int((operation.filters or {}).get("sourceYear") or target_year - 2) if operation else target_year - 2
        source_age = int((operation.filters or {}).get("sourceAge") or max(target_age - 2, 0)) if operation else max(target_age - 2, 0)
        limit = max(1, min(operation.limit if operation else 5, 50))
        sql = f"""
WITH source_cohort AS (
    SELECT
        section_id,
        section_name,
        municipio_id,
        municipio_nombre,
        year AS source_year,
        SUM(people)::numeric AS source_age_band_population
    FROM marts.agent_population_age
    WHERE municipio_id = '{municipality_id}'
      AND year = {source_year}
      AND gender IN ('H', 'M')
      AND age_cohort = '15-19'
    GROUP BY section_id, section_name, municipio_id, municipio_nombre, year
),
estimated AS (
    SELECT
        section_id,
        section_name,
        municipio_id,
        municipio_nombre,
        source_year,
        {source_age}::integer AS source_age,
        {target_year}::integer AS target_year,
        {target_age}::integer AS target_age,
        source_age_band_population,
        ROUND(source_age_band_population / 5.0)::bigint AS estimated_future_age_population
    FROM source_cohort
),
ranked AS (
    SELECT
        *,
        SUM(estimated_future_age_population) OVER ()::bigint AS municipality_estimated_future_age_population,
        RANK() OVER (ORDER BY estimated_future_age_population DESC, section_name) AS section_rank
    FROM estimated
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    source_year,
    source_age,
    target_year,
    target_age,
    estimated_future_age_population,
    municipality_estimated_future_age_population,
    section_rank,
    'estimado_desde_cohorte_15_19' AS estimation_method
FROM ranked
ORDER BY estimated_future_age_population DESC, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="future_age_cohort_projection",
            question=question,
            sql=sql,
            expectedOutput="table",
            methodology=(
                f"Estimo las personas que tendran {target_age} años en {target_year} tomando como referencia "
                f"la cohorte que tenia aproximadamente {source_age} años en {source_year}. Como los datos estan "
                "agrupados en tramos quinquenales, prorrateo una quinta parte del grupo 15-19."
            ),
            confidence="medium",
            sources=["marts.agent_population_age"],
            chartSpec={
                "type": "bar",
                "title": f"Nuevos potenciales votantes en {target_year}",
                "x": "section_name",
                "y": "estimated_future_age_population",
            },
            caveats=[
                "Es una estimación porque la fuente disponible agrupa la edad en cohortes quinquenales.",
                "No predice participación electoral ni permanencia residencial hasta la elección.",
            ],
        )

    def _semantic_aggregate_municipality_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan:
        age_min = operation.filters.get("age_min")
        age_max = operation.filters.get("age_max")
        if age_min is not None and age_max is not None:
            year_filter = f"AND year = {int(operation.year)}" if operation.year else ""
            sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM marts.agent_population_age
    WHERE municipio_id = '{operation.municipio_id}'
      {year_filter}
),
cohort AS (
    SELECT
        municipio_id,
        municipio_nombre,
        year,
        SUM(people)::bigint AS people
    FROM marts.agent_population_age
    JOIN latest USING (year)
    WHERE municipio_id = '{operation.municipio_id}'
      AND gender IN ('H', 'M')
      AND age_min >= {int(age_min)}
      AND age_max <= {int(age_max)}
    GROUP BY municipio_id, municipio_nombre, year
)
SELECT municipio_id, municipio_nombre, year, people AS population_total
FROM cohort
""".strip()
            return SemanticPlan(
                intent="municipality_age_range_total",
                question=question,
                sql=sql,
                expectedOutput="single_value",
                methodology=f"Sumo las cohortes de edad entre {int(age_min)} y {int(age_max)} años en la vista agent_population_age.",
                confidence=operation.confidence,
                sources=["marts.agent_population_age"],
                caveats=["Los tramos de edad se agregan por cohortes completas disponibles."],
            )
        metric = self.semantic_catalog.metric(operation.metric)
        if not metric:
            return self._municipality_population_total_plan(question, operation.municipio_id)
        year_filter = f"AND year = {int(operation.year)}" if operation.year else ""
        sql = f"""
WITH latest AS (
    SELECT MAX(year) AS year
    FROM {metric.view}
    WHERE municipio_id = '{operation.municipio_id}'
      {year_filter}
)
SELECT
    municipio_id,
    municipio_nombre,
    latest.year,
    SUM({metric.field})::numeric AS {metric.metric_id}
FROM {metric.view}
JOIN latest USING (year)
WHERE municipio_id = '{operation.municipio_id}'
GROUP BY municipio_id, municipio_nombre, latest.year
""".strip()
        return SemanticPlan(
            intent="municipality_metric_total",
            question=question,
            sql=sql,
            expectedOutput="single_value",
            methodology=f"Agrego {metric.label.lower()} para el municipio en el ultimo año disponible.",
            confidence=operation.confidence,
            sources=[metric.view],
            caveats=list(metric.caveats),
        )

    def _semantic_section_growth_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan:
        metric = operation.metric or "population_growth_abs"
        rank_by = operation.rank_by or ("growth_pct" if metric == "population_growth_pct" else "growth_abs")
        rank_column = "growthPct" if rank_by == "growth_pct" else "growthAbs"
        order = operation.order.upper()
        limit = max(1, min(operation.limit or 5, 50))
        start_filter = f"MIN(year) FILTER (WHERE year = {int(operation.start_year)})" if operation.start_year else "MIN(year)"
        end_filter = f"MAX(year) FILTER (WHERE year = {int(operation.end_year)})" if operation.end_year else "MAX(year)"
        lineage_values = self._section_lineage_values(operation.municipio_id)
        sql = f"""
WITH population_profile AS MATERIALIZED (
    SELECT
        municipio_id,
        municipio_nombre,
        section_id,
        section_name,
        year,
        population_total
    FROM marts.agent_section_profile
    WHERE municipio_id = '{operation.municipio_id}'
      AND population_total IS NOT NULL
),
years AS (
    SELECT
        COALESCE({start_filter}, MIN(year)) AS start_year,
        COALESCE({end_filter}, MAX(year)) AS end_year
    FROM population_profile
),
manual_lineage(
    municipio_id,
    lineage_group_id,
    lineage_group_name,
    base_year,
    base_section_id,
    current_year,
    current_section_id,
    relationship_type,
    notes
) AS (
    VALUES
        {lineage_values}
),
current_sections AS (
    SELECT
        profile.section_id,
        profile.section_name,
        profile.municipio_nombre
    FROM population_profile profile
    CROSS JOIN years
    WHERE profile.municipio_id = '{operation.municipio_id}'
      AND profile.year = years.end_year
),
lineage_assignments AS (
    SELECT
        current_sections.section_id AS current_section_id,
        COALESCE(manual_lineage.base_section_id, current_sections.section_id) AS base_section_id,
        COALESCE(manual_lineage.lineage_group_id, '{operation.municipio_id}_' || current_sections.section_id || '_LINEAGE') AS lineage_group_id,
        COALESCE(manual_lineage.lineage_group_name, 'Zona historica ' || current_sections.section_name) AS lineage_group_name,
        COALESCE(manual_lineage.relationship_type, 'unchanged') AS relationship_type,
        manual_lineage.notes,
        current_sections.section_name AS current_section_name,
        current_sections.municipio_nombre
    FROM current_sections
    LEFT JOIN manual_lineage
     ON manual_lineage.municipio_id = '{operation.municipio_id}'
     AND manual_lineage.current_section_id = current_sections.section_id
),
base_members AS (
    SELECT DISTINCT
        lineage_group_id,
        lineage_group_name,
        base_section_id
    FROM lineage_assignments
),
start_pop AS (
    SELECT
        base_members.lineage_group_id,
        SUM(profile.population_total)::bigint AS population_start,
        STRING_AGG(profile.section_name, ' + ' ORDER BY profile.section_name) AS base_sections
    FROM base_members
    CROSS JOIN years
    JOIN population_profile profile
      ON profile.municipio_id = '{operation.municipio_id}'
     AND profile.year = years.start_year
     AND profile.section_id = base_members.base_section_id
    GROUP BY base_members.lineage_group_id
),
end_pop AS (
    SELECT
        lineage_assignments.lineage_group_id,
        MAX(lineage_assignments.lineage_group_name) AS lineage_group_name,
        MAX(lineage_assignments.municipio_nombre) AS municipio_nombre,
        SUM(profile.population_total)::bigint AS population_end,
        STRING_AGG(lineage_assignments.current_section_name, ' + ' ORDER BY lineage_assignments.current_section_name) AS current_sections,
        BOOL_OR(lineage_assignments.relationship_type = 'split_child') AS includes_split,
        STRING_AGG(lineage_assignments.notes, ' | ' ORDER BY lineage_assignments.current_section_id) FILTER (WHERE lineage_assignments.notes IS NOT NULL) AS lineage_notes
    FROM lineage_assignments
    CROSS JOIN years
    JOIN population_profile profile
      ON profile.municipio_id = '{operation.municipio_id}'
     AND profile.year = years.end_year
     AND profile.section_id = lineage_assignments.current_section_id
    GROUP BY lineage_assignments.lineage_group_id
)
SELECT
    end_pop.lineage_group_id AS section_id,
    end_pop.lineage_group_id,
    end_pop.lineage_group_name,
    end_pop.lineage_group_name AS section_name,
    end_pop.municipio_nombre,
    years.start_year,
    years.end_year,
    start_pop.base_sections,
    end_pop.current_sections,
    start_pop.population_start,
    end_pop.population_end,
    (end_pop.population_end - start_pop.population_start)::bigint AS growth_abs,
    (end_pop.population_end - start_pop.population_start)::bigint AS "growthAbs",
    ROUND(
        (end_pop.population_end - start_pop.population_start)::numeric
        / NULLIF(start_pop.population_start, 0) * 100,
        1
    ) AS growth_pct,
    ROUND(
        (end_pop.population_end - start_pop.population_start)::numeric
        / NULLIF(start_pop.population_start, 0) * 100,
        1
    ) AS "growthPct",
    end_pop.includes_split,
    end_pop.lineage_notes
FROM end_pop
JOIN start_pop USING (lineage_group_id)
CROSS JOIN years
ORDER BY "{rank_column}" {order}, end_pop.lineage_group_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_population_growth",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=(
                "Comparo la población de cada zona historica entre el primer y el ultimo año solicitado o disponible. "
                "Cuando hay divisiones administrativas de secciones censales, agrego las secciones actuales que proceden de la misma zona base."
            ),
            confidence=operation.confidence,
            sources=["marts.agent_section_profile", "backend/app/ask/section_lineage.yaml"],
            chartSpec={
                "type": "bar",
                "title": "Zonas con mayor crecimiento de población",
                "x": "lineage_group_name",
                "y": rank_column,
                "secondaryValue": "growthPct",
            },
            caveats=[
                "Tiene en cuenta divisiones históricas de secciones censales cuando están disponibles.",
                "Por defecto se ordena por crecimiento absoluto; el crecimiento porcentual puede destacar secciones pequeñas.",
            ],
        )

    def _section_lineage_values(self, municipality_id: str) -> str:
        rows = [
            row
            for row in self.section_lineage.get("lineages", [])
            if str(row.get("municipio_id")) == str(municipality_id)
        ]
        if not rows:
            return "('__NO_MUNICIPIO__', '__NO_LINEAGE__', '__NO_LINEAGE__', NULL, '__NO_BASE__', NULL, '__NO_CURRENT__', '__NO_REL__', NULL)"
        values: list[str] = []
        for row in rows:
            values.append(
                "("
                f"{self._sql_literal(str(row.get('municipio_id', '')))}, "
                f"{self._sql_literal(str(row.get('lineage_group_id', '')))}, "
                f"{self._sql_literal(str(row.get('lineage_group_name', '')))}, "
                f"{int(row['base_year']) if row.get('base_year') is not None else 'NULL'}, "
                f"{self._sql_literal(str(row.get('base_section_id', '')))}, "
                f"{int(row['current_year']) if row.get('current_year') is not None else 'NULL'}, "
                f"{self._sql_literal(str(row.get('current_section_id', '')))}, "
                f"{self._sql_literal(str(row.get('relationship_type', '')))}, "
                f"{self._sql_literal(str(row.get('notes', ''))) if row.get('notes') is not None else 'NULL'}"
                ")"
            )
        return ",\n        ".join(values)

    def _sql_literal(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _semantic_compare_years_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan | None:
        metric = self.semantic_catalog.metric(operation.metric)
        if not metric:
            return None
        order = "ASC" if operation.direction == "largest_decrease" else "DESC"
        limit = max(1, min(operation.limit or 5, 50))
        start_filter = f"MIN(year) FILTER (WHERE year = {int(operation.start_year)})" if operation.start_year else "MIN(year)"
        end_filter = f"MAX(year) FILTER (WHERE year = {int(operation.end_year)})" if operation.end_year else "MAX(year)"
        sql = f"""
WITH profile AS (
    SELECT
        municipio_id,
        municipio_nombre,
        section_id,
        section_name,
        year,
        {metric.field} AS metric_value
    FROM {metric.view}
    WHERE municipio_id = '{operation.municipio_id}'
      AND {metric.field} IS NOT NULL
),
years AS (
    SELECT
        COALESCE({start_filter}, MIN(year)) AS start_year,
        COALESCE({end_filter}, MAX(year)) AS end_year
    FROM profile
),
pivoted AS (
    SELECT
        profile.section_id,
        MAX(profile.section_name) AS section_name,
        MAX(profile.municipio_nombre) AS municipio_nombre,
        MAX(profile.metric_value) FILTER (WHERE profile.year = years.start_year) AS start_value,
        MAX(profile.metric_value) FILTER (WHERE profile.year = years.end_year) AS end_value,
        years.start_year,
        years.end_year
    FROM profile
    CROSS JOIN years
    WHERE profile.year IN (years.start_year, years.end_year)
    GROUP BY profile.section_id, years.start_year, years.end_year
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    start_year,
    end_year,
    ROUND(start_value::numeric, 2) AS start_value,
    ROUND(end_value::numeric, 2) AS end_value,
    ROUND((end_value - start_value)::numeric, 2) AS metric_change
FROM pivoted
WHERE start_value IS NOT NULL
  AND end_value IS NOT NULL
ORDER BY metric_change {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_compare_years",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=f"Comparo {metric.label.lower()} entre el año inicial y el ultimo año disponible por seccion.",
            confidence=operation.confidence,
            sources=[metric.view],
            chartSpec={"type": "bar", "x": "section_name", "y": "metric_change"},
            caveats=list(metric.caveats),
        )

    def _semantic_cross_metric_ranking_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan | None:
        metrics = operation.metrics or []
        if set(metrics) >= {"income_individual", "abstention_pct"}:
            return self._cross_income_abstention_plan(question, operation, low_income=True)
        if set(metrics) >= {"population_under_30", "income_individual"}:
            return self._cross_youth_income_plan(question, operation)
        if set(metrics) >= {"income_individual", "vote_pct"}:
            return self._cross_income_party_plan(question, operation)
        return None

    def _cross_income_abstention_plan(self, question: str, operation: AnalyticalOperation, *, low_income: bool) -> SemanticPlan:
        limit = max(1, min(operation.limit or 10, 50))
        income_order = "ASC" if low_income else "DESC"
        sql = f"""
WITH latest_income AS (
    SELECT MAX(year) AS year
    FROM marts.agent_income_sources
    WHERE municipio_id = '{operation.municipio_id}'
),
latest_election AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_summary
    WHERE municipio_id = '{operation.municipio_id}'
      AND election_type = 'MUNICIPALES'
),
joined AS (
    SELECT
        income.section_id,
        income.section_name,
        income.municipio_nombre,
        income.income_individual,
        electoral.abstention_pct,
        PERCENT_RANK() OVER (ORDER BY income.income_individual {income_order}) AS income_component,
        PERCENT_RANK() OVER (ORDER BY electoral.abstention_pct DESC) AS abstention_component
    FROM marts.agent_income_sources income
    JOIN latest_income ON latest_income.year = income.year
    JOIN marts.agent_electoral_summary electoral
      ON electoral.municipio_id = income.municipio_id
     AND electoral.section_id = income.section_id
    JOIN latest_election ON latest_election.election_year = electoral.election_year
    WHERE income.municipio_id = '{operation.municipio_id}'
      AND electoral.election_type = 'MUNICIPALES'
      AND income.income_individual IS NOT NULL
      AND electoral.abstention_pct IS NOT NULL
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    income_individual,
    abstention_pct,
    ROUND(((income_component + abstention_component) / 2.0)::numeric, 4) AS score
FROM joined
ORDER BY score DESC, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="cross_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology="Combino renta y abstencion mediante percentiles normalizados por seccion.",
            confidence="medium",
            sources=["marts.agent_income_sources", "marts.agent_electoral_summary"],
            chartSpec={"type": "scatter", "x": "income_individual", "y": "abstention_pct"},
            caveats=["Ranking beta: el score combina percentiles simples, no un modelo causal."],
        )

    def _cross_youth_income_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan:
        limit = max(1, min(operation.limit or 10, 50))
        sql = f"""
WITH latest_profile AS (
    SELECT MAX(year) AS year
    FROM marts.agent_section_profile
    WHERE municipio_id = '{operation.municipio_id}'
),
joined AS (
    SELECT
        section_id,
        section_name,
        municipio_nombre,
        population_under_30,
        income_individual,
        PERCENT_RANK() OVER (ORDER BY population_under_30 DESC) AS youth_component,
        PERCENT_RANK() OVER (ORDER BY income_individual ASC) AS income_component
    FROM marts.agent_section_profile
    JOIN latest_profile USING (year)
    WHERE municipio_id = '{operation.municipio_id}'
      AND population_under_30 IS NOT NULL
      AND income_individual IS NOT NULL
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    population_under_30,
    income_individual,
    ROUND(((youth_component + income_component) / 2.0)::numeric, 4) AS score
FROM joined
ORDER BY score DESC, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="cross_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology="Combino volumen de jovenes y renta baja mediante percentiles normalizados.",
            confidence="medium",
            sources=["marts.agent_section_profile"],
            chartSpec={"type": "scatter", "x": "income_individual", "y": "population_under_30"},
            caveats=["Ranking beta: el score combina percentiles simples, no un modelo causal."],
        )

    def _cross_income_party_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan:
        limit = max(1, min(operation.limit or 10, 50))
        party_sql = (operation.party or "PP").replace("'", "''").upper()
        sql = f"""
WITH latest_income AS (
    SELECT MAX(year) AS year
    FROM marts.agent_income_sources
    WHERE municipio_id = '{operation.municipio_id}'
),
latest_election AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_results
    WHERE municipio_id = '{operation.municipio_id}'
      AND election_type = 'MUNICIPALES'
),
joined AS (
    SELECT
        income.section_id,
        income.section_name,
        income.municipio_nombre,
        income.income_individual,
        votes.vote_pct,
        PERCENT_RANK() OVER (ORDER BY income.income_individual DESC) AS income_component,
        PERCENT_RANK() OVER (ORDER BY votes.vote_pct DESC) AS vote_component
    FROM marts.agent_income_sources income
    JOIN latest_income ON latest_income.year = income.year
    JOIN marts.agent_electoral_results votes
      ON votes.municipio_id = income.municipio_id
     AND votes.section_id = income.section_id
    JOIN latest_election ON latest_election.election_year = votes.election_year
    WHERE income.municipio_id = '{operation.municipio_id}'
      AND votes.election_type = 'MUNICIPALES'
      AND UPPER(votes.canonical_party) = '{party_sql}'
      AND income.income_individual IS NOT NULL
      AND votes.vote_pct IS NOT NULL
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    income_individual,
    vote_pct,
    ROUND(((income_component + vote_component) / 2.0)::numeric, 4) AS score
FROM joined
ORDER BY score DESC, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="cross_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=f"Combino renta alta y voto a {party_sql} mediante percentiles normalizados.",
            confidence="medium",
            sources=["marts.agent_income_sources", "marts.agent_electoral_results"],
            chartSpec={"type": "scatter", "x": "income_individual", "y": "vote_pct"},
            caveats=["Ranking beta: el score combina percentiles simples, no un modelo causal."],
        )

    def _semantic_rank_sections_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan | None:
        metric = self.semantic_catalog.metric(operation.metric)
        if not metric or metric.pending:
            return None
        order = operation.order.upper()
        limit = max(1, min(operation.limit, 50))
        election_filter = ""
        temporal_column = "year"
        if metric.view == "marts.agent_electoral_summary":
            temporal_column = "election_year"
            election_type = operation.election_type or "MUNICIPALES"
            election_filter = f"AND election_type = '{self._election_code(election_type)}'"
        year_filter = f"{temporal_column} = {int(operation.year)}" if operation.year else "TRUE"
        sql = f"""
WITH filtered AS (
    SELECT
        section_id AS section_id,
        section_name,
        municipio_id,
        municipio_nombre,
        {temporal_column} AS year,
        {metric.field} AS {metric.metric_id}
    FROM {metric.view}
    WHERE municipio_id = '{operation.municipio_id}'
      AND {year_filter}
      {election_filter}
      AND {metric.field} IS NOT NULL
),
latest AS (
    SELECT MAX(year) AS year
    FROM filtered
)
SELECT
    section_id,
    section_name,
    municipio_nombre,
    {metric.metric_id},
    filtered.year
FROM filtered
JOIN latest ON latest.year = filtered.year
ORDER BY {metric.metric_id} {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology=f"Comparo {metric.label} entre las secciones del municipio y ordeno el resultado.",
            confidence=operation.confidence,
            sources=[metric.view],
            chartSpec={"type": "bar", "x": "section_name", "y": metric.metric_id} if limit > 1 else None,
            caveats=list(metric.caveats),
        )

    def _semantic_party_strength_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan:
        party_sql = (operation.party or "PP").replace("'", "''").upper()
        order = operation.order.upper()
        limit = max(1, min(operation.limit, 50))
        election_type = self._election_code(operation.election_type or "MUNICIPALES")
        year_filter = f"AND election_year = {int(operation.election_year)}" if operation.election_year else ""
        sql = f"""
WITH filtered AS (
    SELECT
        section_id AS section_id,
        section_name,
        municipio_nombre,
        canonical_party AS party,
        vote_pct,
        election_year AS year
    FROM marts.agent_electoral_results
    WHERE municipio_id = '{operation.municipio_id}'
      AND election_type = '{election_type}'
      AND UPPER(canonical_party) = '{party_sql}'
      {year_filter}
      AND vote_pct IS NOT NULL
),
latest AS (
    SELECT MAX(year) AS year
    FROM filtered
)
SELECT section_id, section_name, municipio_nombre, party, vote_pct, filtered.year
FROM filtered
JOIN latest ON latest.year = filtered.year
ORDER BY vote_pct {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology=f"Comparo el porcentaje de voto de {party_sql} por sección en la elección seleccionada.",
            confidence=operation.confidence,
            sources=["marts.agent_electoral_results"],
            chartSpec={"type": "bar", "x": "section_name", "y": "vote_pct"} if limit > 1 else None,
        )

    def _semantic_persistent_winners_plan(self, question: str, operation: AnalyticalOperation) -> SemanticPlan:
        party_sql = (operation.party or "PP").replace("'", "''").upper()
        election_filter = f"AND election_type = '{self._election_code(operation.election_type)}'" if operation.election_type else ""
        sql = f"""
WITH winners AS (
    SELECT
        section_id AS section_id,
        section_name,
        election_id,
        winner_party
    FROM marts.agent_electoral_summary
    WHERE municipio_id = '{operation.municipio_id}'
      {election_filter}
),
section_counts AS (
    SELECT
        section_id,
        section_name,
        COUNT(*) AS elections_checked,
        COUNT(*) FILTER (WHERE UPPER(winner_party) = '{party_sql}') AS party_wins
    FROM winners
    GROUP BY section_id, section_name
)
SELECT
    section_id,
    section_name,
    elections_checked,
    party_wins,
    ROUND(party_wins::numeric / NULLIF(elections_checked, 0) * 100, 2) AS win_rate_pct,
    party_wins = elections_checked AS always_wins
FROM section_counts
ORDER BY always_wins DESC, party_wins DESC, section_name
LIMIT 50
""".strip()
        return SemanticPlan(
            intent="party_always_wins_by_section",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=f"Cuento elecciones disponibles por sección y comparo cuántas ganó {party_sql}.",
            confidence=operation.confidence,
            sources=["marts.agent_electoral_summary"],
            chartSpec={"type": "bar", "x": "section_name", "y": "win_rate_pct"},
        )

    def _plan_from_analytical_intent(
        self,
        question: str,
        analytical_intent: AnalyticalIntent,
        municipality_id: str,
    ) -> SemanticPlan | None:
        if analytical_intent.metric == "persistent_winner":
            party = str(analytical_intent.filters.get("party") or extract_party(question) or "PSOE")
            return self._always_wins_plan(question, municipality_id, party)

        if analytical_intent.entity != "section":
            return None

        metric = analytical_intent.metric
        if metric not in {
            "average_age",
            "population_total",
            "population_under_30",
            "population_under_30_pct",
            "population_over_65",
            "population_over_65_pct",
            "income_individual",
            "income_household",
            "abstention_pct",
            "participation_pct",
            "vote_pct",
            "winner_party",
        }:
            return None

        asks_for_sections = bool(
            re.search(r"que secciones|qué secciones|secciones tienen|donde|zonas|areas|ranking|ordena|lista", normalize(question))
        )
        limit = 1 if analytical_intent.intent == "single_extreme" and not asks_for_sections else 50
        direction = analytical_intent.direction or "desc"
        order = "ASC" if direction in {"asc", "min"} else "DESC"

        if metric == "average_age":
            return self._section_age_structure_metric_plan(question, municipality_id, metric, order, limit)
        if metric in {"population_under_30", "population_under_30_pct", "population_over_65", "population_over_65_pct"}:
            return self._section_age_cohort_metric_plan(question, municipality_id, metric, order, limit)
        if metric == "population_total":
            return self._section_population_metric_plan(question, municipality_id, order, limit)
        if metric in {"income_individual", "income_household"}:
            return self._section_income_metric_plan(question, municipality_id, metric, order, limit)
        if metric in {"abstention_pct", "participation_pct", "winner_party"}:
            return self._section_electoral_metric_plan(question, municipality_id, metric, order, limit)
        if metric == "vote_pct":
            party = str(analytical_intent.filters.get("party") or extract_party(question) or "")
            if not party:
                return None
            return self._section_party_vote_metric_plan(question, municipality_id, party, order, limit)

        return None

    def _contextual_followup_plan(
        self,
        question: str,
        municipality_id: str,
        resolved_references: dict[str, Any],
    ) -> SemanticPlan | None:
        text = normalize(question)
        last_metric = str(resolved_references.get("lastMetric") or "")
        asks_percentage = bool(re.search(r"\bporcentaje\b|\bpct\b|%\b|peso relativo|proporcion", text))
        asks_count = bool(re.search(r"\bnumero\b|\bnúmero\b|\babsolut|personas|cuantas|cuántas", text))
        asks_same = bool(re.search(r"^y\b|haz lo mismo|lo mismo|ordenamelas|ordénamelas|dame las", text))
        limit = self._extract_limit(question, default=50 if re.search(r"todas|ranking|ordena", text) else 1)
        if last_metric in {"population_under_30", "population_under_30_pct"} and (asks_percentage or asks_count or asks_same):
            metric = "population_under_30_pct" if asks_percentage else "population_under_30"
            return self._section_age_cohort_metric_plan(question, municipality_id, metric, "DESC", limit)
        if last_metric in {"population_over_65", "population_over_65_pct"} and (asks_percentage or asks_count or asks_same):
            metric = "population_over_65_pct" if asks_percentage else "population_over_65"
            return self._section_age_cohort_metric_plan(question, municipality_id, metric, "DESC", limit)
        return None

    def _direct_age_population_plan(self, question: str, municipality_id: str) -> SemanticPlan | None:
        text = normalize(question)
        if re.search(r"abstencion|abstuv|no vot|vot[oó]|votar|participacion", text):
            return None
        asks_for_sections = bool(
            re.search(r"ranking|ordena|dame las|todas|que secciones|qué secciones|secciones tienen|donde|zonas|areas", text)
        )
        limit = self._extract_limit(question, default=50 if asks_for_sections else 1)
        asks_pct = bool(re.search(r"\bporcentaje\b|\bpct\b|%\b|peso relativo|proporcion", text))
        if re.search(r"jovenes|menores de 30|poblacion joven", text):
            metric = "population_under_30_pct" if asks_pct else "population_under_30"
            return self._section_age_cohort_metric_plan(question, municipality_id, metric, "DESC", limit)
        if re.search(r"mayores de 65|mayores|poblacion mayor|senior", text) and not re.search(r"abstencion|vot", text):
            metric = "population_over_65_pct" if asks_pct else "population_over_65"
            return self._section_age_cohort_metric_plan(question, municipality_id, metric, "DESC", limit)
        return None

    def _section_age_cohort_metric_plan(
        self,
        question: str,
        municipality_id: str,
        metric: str,
        order: str,
        limit: int,
    ) -> SemanticPlan:
        is_under_30 = metric.startswith("population_under_30")
        is_pct = metric.endswith("_pct")
        cohort_filter = (
            "edad_cohorte IN ('0-4', '5-9', '10-14', '15-19', '20-24', '25-29')"
            if is_under_30
            else "edad_cohorte IN ('65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95-99', '100+', '85 y más', '85+')"
        )
        count_alias = "population_under_30" if is_under_30 else "population_over_65"
        pct_alias = f"{count_alias}_pct"
        order_expr = pct_alias if is_pct else count_alias
        sql = f"""
WITH latest AS (
    SELECT COALESCE(MAX(anio) FILTER (WHERE anio = 2023), MAX(anio)) AS year
    FROM core.poblacion_edad
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
),
section_age AS (
    SELECT
        pop.seccion_id AS section_id,
        pop.anio AS year,
        SUM(pop.poblacion) FILTER (WHERE pop.edad_cohorte <> 'TOTAL') AS total_population,
        SUM(pop.poblacion) FILTER (WHERE {cohort_filter}) AS {count_alias}
    FROM core.poblacion_edad pop
    JOIN latest ON latest.year = pop.anio
    WHERE LEFT(pop.seccion_id, 5) = '{municipality_id}'
      AND pop.genero IN ('H', 'M')
    GROUP BY pop.seccion_id, pop.anio
)
SELECT
    age.section_id,
    COALESCE(display.label_cliente, age.section_id) AS section_name,
    age.{count_alias}::bigint AS {count_alias},
    ROUND(age.{count_alias}::numeric / NULLIF(age.total_population, 0) * 100, 2) AS {pct_alias},
    age.total_population::bigint AS total_population,
    age.year
FROM section_age age
LEFT JOIN marts.dim_seccion_display display
  ON display.seccion_id = age.section_id
WHERE age.{count_alias} IS NOT NULL
ORDER BY {order_expr} {order}, section_name
LIMIT {limit}
""".strip()
        cohort_label = "menor de 30 años" if is_under_30 else "mayor de 65 años"
        natural_metric = "porcentaje" if is_pct else "numero absoluto"
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology=(
                f"Interpreto la pregunta como {natural_metric} de poblacion {cohort_label} por seccion. "
                "Si no se pide porcentaje, uso numero absoluto de personas."
            ),
            confidence="high",
            sources=["core.poblacion_edad", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": order_expr} if limit > 1 else None,
            caveats=[
                "Dato calculado a partir de cohortes de edad disponibles.",
                "La poblacion joven se interpreta como menores de 30 años.",
            ] if is_under_30 else ["Dato calculado a partir de cohortes de edad disponibles."],
        )

    def _section_age_structure_metric_plan(
        self,
        question: str,
        municipality_id: str,
        metric: str,
        order: str,
        limit: int,
    ) -> SemanticPlan:
        sql = f"""
SELECT
    age.seccion_id AS section_id,
    COALESCE(display.label_cliente, age.seccion_id) AS section_name,
    ROUND(age.average_age::numeric, 2) AS average_age,
    2023 AS year
FROM marts.v_mapa_age_structure_2023 age
LEFT JOIN marts.dim_seccion_display display
  ON display.seccion_id = age.seccion_id
WHERE LEFT(age.seccion_id, 5) = '{municipality_id}'
  AND age.average_age IS NOT NULL
ORDER BY age.average_age {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology="Interpreto la pregunta como una ordenacion de secciones por edad media.",
            confidence="high",
            sources=["marts.v_mapa_age_structure_2023", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": metric} if limit > 1 else None,
            caveats=["La vista de estructura de edad disponible para este indicador es la capa 2023."],
        )

    def _section_population_metric_plan(
        self,
        question: str,
        municipality_id: str,
        order: str,
        limit: int,
    ) -> SemanticPlan:
        sql = f"""
WITH latest AS (
    SELECT MAX(anio) AS year
    FROM marts.v_poblacion_seccion_anio
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
),
ranked AS (
    SELECT
        pop.seccion_id AS section_id,
        COALESCE(display.label_cliente, pop.seccion_id) AS section_name,
        pop.pob_total AS population_total,
        pop.anio AS year
    FROM marts.v_poblacion_seccion_anio pop
    JOIN latest ON latest.year = pop.anio
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = pop.seccion_id
    WHERE LEFT(pop.seccion_id, 5) = '{municipality_id}'
      AND pop.pob_total IS NOT NULL
)
SELECT section_id, section_name, population_total, year
FROM ranked
ORDER BY population_total {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology="Uso el ultimo año disponible de poblacion y ordeno las secciones por habitantes.",
            confidence="high",
            sources=["marts.v_poblacion_seccion_anio", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": "population_total"} if limit > 1 else None,
        )

    def _section_income_metric_plan(
        self,
        question: str,
        municipality_id: str,
        metric: str,
        order: str,
        limit: int,
    ) -> SemanticPlan:
        field = "renta_media_hogar" if metric == "income_household" else "renta_media_persona"
        alias = "income_household" if metric == "income_household" else "income_individual"
        sql = f"""
WITH latest AS (
    SELECT MAX(anio) AS year
    FROM marts.v_income_level_layer
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
),
ranked AS (
    SELECT
        income.seccion_id AS section_id,
        COALESCE(display.label_cliente, income.seccion_id) AS section_name,
        income.{field} AS {alias},
        income.anio AS year
    FROM marts.v_income_level_layer income
    JOIN latest ON latest.year = income.anio
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = income.seccion_id
    WHERE LEFT(income.seccion_id, 5) = '{municipality_id}'
      AND income.{field} IS NOT NULL
)
SELECT section_id, section_name, {alias}, year
FROM ranked
ORDER BY {alias} {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology="Uso el ultimo año disponible de renta y ordeno las secciones por renta.",
            confidence="high",
            sources=["marts.v_income_level_layer", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": alias} if limit > 1 else None,
        )

    def _section_electoral_metric_plan(
        self,
        question: str,
        municipality_id: str,
        metric: str,
        order: str,
        limit: int,
    ) -> SemanticPlan:
        if metric == "winner_party":
            order_expr = "winning_party_pct"
            select_metric = "winning_party, winning_party_pct"
        else:
            order_expr = metric
            select_metric = metric
        sql = f"""
WITH latest AS (
    SELECT MAX(anio) AS year
    FROM marts.mv_electoral_behavior
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
      AND tipo_eleccion_code = 'MUNICIPALES'
),
ranked AS (
    SELECT
        eb.seccion_id AS section_id,
        COALESCE(display.label_cliente, eb.seccion_id) AS section_name,
        ROUND((MAX(eb.censo) - MAX(eb.votos_emitidos))::numeric / NULLIF(MAX(eb.censo), 0) * 100, 2) AS abstention_pct,
        ROUND(MAX(eb.votos_emitidos)::numeric / NULLIF(MAX(eb.censo), 0) * 100, 2) AS participation_pct,
        MAX(eb.winning_party_family) AS winning_party,
        MAX(eb.winning_party_pct) AS winning_party_pct,
        MAX(eb.anio) AS year
    FROM marts.mv_electoral_behavior eb
    JOIN latest ON latest.year = eb.anio
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = eb.seccion_id
    WHERE LEFT(eb.seccion_id, 5) = '{municipality_id}'
      AND eb.tipo_eleccion_code = 'MUNICIPALES'
    GROUP BY eb.seccion_id, display.label_cliente
)
SELECT section_id, section_name, {select_metric}, year
FROM ranked
ORDER BY {order_expr} {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology="Uso la ultima eleccion municipal disponible y ordeno las secciones por la metrica electoral solicitada.",
            confidence="high",
            sources=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": order_expr} if limit > 1 else None,
        )

    def _section_party_vote_metric_plan(
        self,
        question: str,
        municipality_id: str,
        party: str,
        order: str,
        limit: int,
    ) -> SemanticPlan:
        party_sql = party.replace("'", "''")
        sql = f"""
WITH latest AS (
    SELECT MAX(anio) AS year
    FROM marts.mv_electoral_behavior
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
      AND tipo_eleccion_code = 'MUNICIPALES'
),
party_vote AS (
    SELECT
        eb.seccion_id AS section_id,
        COALESCE(display.label_cliente, eb.seccion_id) AS section_name,
        (party_result->>'normalized_party_family') AS party,
        ROUND(((party_result->>'pct')::numeric * 100), 2) AS vote_pct,
        eb.anio AS year
    FROM marts.mv_electoral_behavior eb
    JOIN latest ON latest.year = eb.anio
    CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = eb.seccion_id
    WHERE LEFT(eb.seccion_id, 5) = '{municipality_id}'
      AND eb.tipo_eleccion_code = 'MUNICIPALES'
      AND party_result->>'normalized_party_family' = '{party_sql}'
)
SELECT section_id, section_name, party, vote_pct, year
FROM party_vote
ORDER BY vote_pct {order}, section_name
LIMIT {limit}
""".strip()
        return SemanticPlan(
            intent="section_metric_extreme" if limit == 1 else "section_metric_ranking",
            question=question,
            sql=sql,
            expectedOutput="single_value" if limit == 1 else "ranking",
            methodology=f"Uso la ultima eleccion municipal disponible y ordeno las secciones por porcentaje de voto a {party}.",
            confidence="high",
            sources=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": "vote_pct"} if limit > 1 else None,
        )

    def _age_abstention_plan(
        self,
        question: str,
        municipality_id: str,
        year: int,
        election_type: str,
        age_range: tuple[int, int | None],
    ) -> SemanticPlan:
        min_age, max_age = age_range
        effective_max = max_age if max_age is not None else 120
        age_label = f"{min_age}+" if max_age is None else f"{min_age}-{max_age}"
        election_code = self._election_code(election_type)
        sql = f"""
WITH normalized_population AS (
    SELECT
        CASE
            WHEN anio = 2021 AND seccion_id = '2907001006' THEN '2907001021'
            WHEN anio = 2021 AND seccion_id = '2907001021' THEN '2907001006'
            ELSE seccion_id
        END AS section_id,
        anio AS year,
        genero AS gender,
        poblacion AS people,
        lower(trim(edad_cohorte)) AS age_cohort_norm
    FROM core.poblacion_edad
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
      AND anio = {year}
      AND genero IN ('H', 'M')
      AND edad_cohorte <> 'TOTAL'
),
cohorts AS (
    SELECT
        *,
        CASE
            WHEN age_cohort_norm ~ '^[0-9]+\\s*-\\s*[0-9]+$'
            THEN split_part(regexp_replace(age_cohort_norm, '\\s+', '', 'g'), '-', 1)::int
            WHEN age_cohort_norm ~ '^[0-9]+\\s*(\\+|y\\s*m[aá]s)$'
            THEN substring(age_cohort_norm FROM '^[0-9]+')::int
            ELSE NULL
        END AS cohort_min_age,
        CASE
            WHEN age_cohort_norm ~ '^[0-9]+\\s*-\\s*[0-9]+$'
            THEN split_part(regexp_replace(age_cohort_norm, '\\s+', '', 'g'), '-', 2)::int
            WHEN age_cohort_norm ~ '^[0-9]+\\s*(\\+|y\\s*m[aá]s)$'
            THEN 120
            ELSE NULL
        END AS cohort_max_age
    FROM normalized_population
),
age_by_section AS (
    SELECT
        section_id,
        ROUND(SUM(
            people::numeric
            * GREATEST(LEAST(cohort_max_age, {effective_max}) - GREATEST(cohort_min_age, {min_age}) + 1, 0)
            / NULLIF(cohort_max_age - cohort_min_age + 1, 0)
        ))::bigint AS age_range_population
    FROM cohorts
    WHERE cohort_min_age IS NOT NULL
      AND cohort_max_age IS NOT NULL
      AND cohort_max_age >= {min_age}
      AND cohort_min_age <= {effective_max}
    GROUP BY section_id
),
electoral AS (
    SELECT
        section_id AS section_id,
        ROUND((MAX(censo) - MAX(votos_emitidos))::numeric / NULLIF(MAX(censo), 0) * 100, 4) AS abstention_pct,
        ROUND(MAX(votos_emitidos)::numeric / NULLIF(MAX(censo), 0) * 100, 4) AS participation_pct
    FROM marts.mv_electoral_behavior
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
      AND anio = {year}
      AND tipo_eleccion_code = '{election_code}'
    GROUP BY seccion_id
),
joined AS (
    SELECT
        age.section_id,
        COALESCE(display.label_cliente, age.section_id) AS section_name,
        age.age_range_population,
        electoral.abstention_pct,
        electoral.participation_pct,
        ROUND(age.age_range_population * electoral.abstention_pct / 100.0)::bigint AS estimated_abstainers,
        ROUND(age.age_range_population * electoral.participation_pct / 100.0)::bigint AS estimated_voters
    FROM age_by_section age
    JOIN electoral USING (section_id)
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = age.section_id
)
SELECT
    section_id,
    section_name,
    age_range_population,
    abstention_pct,
    participation_pct,
    estimated_abstainers,
    estimated_voters,
    SUM(age_range_population) OVER () AS municipality_age_range_population,
    SUM(estimated_abstainers) OVER () AS municipality_estimated_abstainers,
    SUM(estimated_voters) OVER () AS municipality_estimated_voters
FROM joined
ORDER BY estimated_abstainers DESC, section_name
LIMIT 50
""".strip()
        return SemanticPlan(
            intent="age_cohort_turnout_estimation",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=(
                f"Estimo poblacion {age_label} por seccion con prorrateo de cohortes y aplico la tasa "
                f"de abstencion/participacion seccional de {election_type} {year}."
            ),
            confidence="high",
            sources=["core.poblacion_edad", "marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": "estimated_abstainers"},
            caveats=[
                "Este cálculo es una estimación ecológica: no sabemos el voto real individual por edad.",
                "La poblacion por edad se estima proporcionalmente cuando el rango corta cohortes quinquenales.",
            ],
        )

    def _always_wins_plan(self, question: str, municipality_id: str, party: str) -> SemanticPlan:
        party_sql = party.replace("'", "''")
        sql = f"""
WITH winners AS (
    SELECT
        eb.seccion_id AS section_id,
        COALESCE(display.label_cliente, eb.seccion_id) AS section_name,
        eb.election_id,
        COALESCE(eb.winning_party_family, eb.winning_party) AS winning_party
    FROM marts.mv_electoral_behavior eb
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = eb.seccion_id
    WHERE LEFT(eb.seccion_id, 5) = '{municipality_id}'
),
section_counts AS (
    SELECT
        section_id,
        section_name,
        COUNT(*) AS elections_checked,
        COUNT(*) FILTER (WHERE UPPER(winning_party) = '{party_sql}') AS party_wins
    FROM winners
    GROUP BY section_id, section_name
)
SELECT
    section_id,
    section_name,
    elections_checked,
    party_wins,
    ROUND(party_wins::numeric / NULLIF(elections_checked, 0) * 100, 2) AS win_rate_pct,
    party_wins = elections_checked AS always_wins
FROM section_counts
ORDER BY always_wins DESC, party_wins DESC, section_name
LIMIT 50
""".strip()
        return SemanticPlan(
            intent="party_always_wins_by_section",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=f"Cuento elecciones disponibles por seccion y comparo cuantas gano {party}.",
            confidence="high",
            sources=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": "win_rate_pct"},
        )

    def _young_abstention_plan(self, question: str, municipality_id: str, year: int) -> SemanticPlan:
        sql = f"""
WITH electoral AS (
    SELECT
        section_id AS section_id,
        ROUND((MAX(censo) - MAX(votos_emitidos))::numeric / NULLIF(MAX(censo), 0) * 100, 2) AS abstention_pct
    FROM marts.mv_electoral_behavior
    WHERE LEFT(seccion_id, 5) = '{municipality_id}'
      AND anio = {year}
      AND tipo_eleccion_code = 'MUNICIPALES'
    GROUP BY seccion_id
)
SELECT
    electoral.section_id,
    COALESCE(display.label_cliente, electoral.section_id) AS section_name,
    age.under_30_pct,
    electoral.abstention_pct,
    ROUND((COALESCE(age.under_30_pct, 0) / 100.0) * electoral.abstention_pct, 2) AS young_abstention_score
FROM electoral
JOIN marts.v_mapa_age_structure_2023 age
  ON age.seccion_id = electoral.section_id
LEFT JOIN marts.dim_seccion_display display
  ON display.seccion_id = electoral.section_id
ORDER BY young_abstention_score DESC, abstention_pct DESC
LIMIT 15
""".strip()
        return SemanticPlan(
            intent="young_population_high_abstention_sections",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology="Ordeno secciones combinando porcentaje menor de 30 y abstencion municipal observada.",
            confidence="medium",
            sources=["marts.v_mapa_age_structure_2023", "marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": "young_abstention_score"},
            caveats=["El score es una priorizacion compuesta, no una medida directa de abstencion joven real."],
        )

    def _historical_party_average_plan(self, question: str, municipality_id: str, party: str) -> SemanticPlan:
        party_sql = party.replace("'", "''")
        sql = f"""
WITH party_rows AS (
    SELECT
        eb.seccion_id AS section_id,
        COALESCE(display.label_cliente, eb.seccion_id) AS section_name,
        eb.election_id,
        eb.anio AS year,
        (party_result->>'normalized_party_family') AS party,
        ((party_result->>'pct')::numeric * 100) AS vote_pct
    FROM marts.mv_electoral_behavior eb
    CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = eb.seccion_id
    WHERE LEFT(eb.seccion_id, 5) = '{municipality_id}'
      AND party_result->>'normalized_party_family' = '{party_sql}'
)
SELECT
    section_id,
    section_name,
    ROUND(AVG(vote_pct), 2) AS average_vote_pct,
    ROUND(MIN(vote_pct), 2) AS min_vote_pct,
    ROUND(MAX(vote_pct), 2) AS max_vote_pct,
    COUNT(*) AS elections_included
FROM party_rows
GROUP BY section_id, section_name
ORDER BY average_vote_pct DESC, section_name
LIMIT 50
""".strip()
        return SemanticPlan(
            intent="historical_party_average_by_section",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=f"Calculo la media historica del porcentaje de voto valido de {party} por seccion.",
            confidence="high",
            sources=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "bar", "x": "section_name", "y": "average_vote_pct"},
        )

    def _high_income_high_party_plan(self, question: str, municipality_id: str, party: str, year: int) -> SemanticPlan:
        party_sql = party.replace("'", "''")
        sql = f"""
WITH party_vote AS (
    SELECT
        eb.seccion_id AS section_id,
        ((party_result->>'pct')::numeric * 100) AS vote_pct
    FROM marts.mv_electoral_behavior eb
    CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
    WHERE LEFT(eb.seccion_id, 5) = '{municipality_id}'
      AND eb.anio = {year}
      AND eb.tipo_eleccion_code = 'MUNICIPALES'
      AND party_result->>'normalized_party_family' = '{party_sql}'
)
SELECT
    vote.section_id,
    COALESCE(display.label_cliente, vote.section_id) AS section_name,
    income.renta_media_persona AS individual_income,
    vote.vote_pct,
    ROUND(
      percent_rank() OVER (ORDER BY income.renta_media_persona)::numeric
      + percent_rank() OVER (ORDER BY vote.vote_pct)::numeric,
      4
    ) AS combined_score
FROM party_vote vote
JOIN marts.v_income_level_layer income
  ON income.seccion_id = vote.section_id
 AND income.anio = {year}
LEFT JOIN marts.dim_seccion_display display
  ON display.seccion_id = vote.section_id
ORDER BY combined_score DESC, individual_income DESC, vote_pct DESC
LIMIT 15
""".strip()
        return SemanticPlan(
            intent="high_income_high_party_vote_sections",
            question=question,
            sql=sql,
            expectedOutput="ranking",
            methodology=f"Combino ranking relativo de renta individual y voto a {party} en municipales {year}.",
            confidence="medium",
            sources=["marts.v_income_level_layer", "marts.mv_electoral_behavior", "marts.dim_seccion_display"],
            chartSpec={"type": "scatter", "x": "individual_income", "y": "vote_pct"},
            caveats=["El score combina rankings; no implica causalidad entre renta y voto."],
        )

    def _previous_sections_winner_count_plan(
        self,
        question: str,
        sections: list[dict[str, Any]],
        party: str,
        year: int,
    ) -> SemanticPlan:
        ids = [section["sectionId"] for section in sections if section.get("sectionId")]
        values = ", ".join(f"('{section_id}')" for section_id in ids)
        party_sql = party.replace("'", "''")
        sql = f"""
WITH previous_sections(section_id) AS (
    VALUES {values}
),
winners AS (
    SELECT
        eb.seccion_id AS section_id,
        COALESCE(display.label_cliente, eb.seccion_id) AS section_name,
        COALESCE(eb.winning_party_family, eb.winning_party) AS winning_party,
        eb.winning_party_pct
    FROM previous_sections previous
    JOIN marts.mv_electoral_behavior eb
      ON eb.seccion_id = previous.section_id
    LEFT JOIN marts.dim_seccion_display display
      ON display.seccion_id = eb.seccion_id
    WHERE eb.anio = {year}
      AND eb.tipo_eleccion_code = 'MUNICIPALES'
)
SELECT
    section_id,
    section_name,
    winning_party,
    winning_party_pct,
    COUNT(*) FILTER (WHERE UPPER(winning_party) = '{party_sql}') OVER () AS matching_sections,
    COUNT(*) OVER () AS total_sections
FROM winners
ORDER BY winning_party = '{party_sql}' DESC, section_name
LIMIT 100
""".strip()
        return SemanticPlan(
            intent="previous_sections_winner_count",
            question=question,
            sql=sql,
            expectedOutput="table",
            methodology="Uso el conjunto de secciones guardado en memoria y consulto ganador observado por seccion.",
            confidence="high",
            sources=["marts.mv_electoral_behavior", "marts.dim_seccion_display"],
        )

    def _extract_age_range(self, question: str) -> tuple[int, int | None] | None:
        text = normalize(question)
        if re.search(r"personas mayores|poblacion senior|jubilad", text):
            return (65, None)
        older = re.search(r"(?:mayores de|mas de|m[aá]s de)\s+(\d{1,3})", text)
        if older:
            return (int(older.group(1)), None)
        plus = re.search(r"\b(\d{1,3})\s*(?:anos|años)?\s*o\s+m[aá]s\b", text)
        if plus:
            return (int(plus.group(1)), None)
        under = re.search(r"(?:menores de|menos de)\s+(\d{1,3})", text)
        if under:
            return (0, max(int(under.group(1)) - 1, 0))
        between = re.search(r"\b(\d{1,3})\s*(?:a|-)\s*(\d{1,3})\s*(?:anos|años)?\b", text)
        if between:
            first = int(between.group(1))
            second = int(between.group(2))
            if first < 120 and second < 120:
                return (min(first, second), max(first, second))
        return None

    def _extract_limit(self, question: str, default: int = 1) -> int:
        text = normalize(question)
        match = re.search(r"\b(?:top|primeras|primeros|dame las|dame los|muestrame las|mu[eé]strame las)\s+(\d{1,2})\b", text)
        if match:
            return max(1, min(int(match.group(1)), 50))
        if re.search(r"\btodas\b|\btodos\b|\branking\b|\bordena", text):
            return 50
        return default

    def _asks_age_turnout_or_abstention(self, text: str) -> bool:
        return bool(
            re.search(r"edad|anos|años|mayores|menores|joven|senior|jubilad", text)
            and re.search(r"abstencion|abstuv|no vot|vot[oó]|votar|participacion", text)
        )

    def _asks_future_first_time_voters(self, text: str) -> bool:
        return bool(
            re.search(r"tendran\s+18|tendrán\s+18|18\s+anos\s+en\s+2027|18\s+años\s+en\s+2027", text)
            or re.search(r"podran\s+votar|podrán\s+votar|primer voto|votar por primera vez|nuevos votantes|nuevas votantes", text)
        )

    def _extract_year(self, question: str) -> int | None:
        match = re.search(r"\b(20\d{2})\b", question)
        return int(match.group(1)) if match else None

    def _extract_election_type(self, question: str) -> str | None:
        text = normalize(question)
        if "andaluz" in text:
            return "andaluzas"
        if "congreso" in text or "generales" in text:
            return "congreso"
        if "europe" in text:
            return "europeas"
        if "municip" in text:
            return "municipales"
        return None

    def _election_code(self, election_type: str) -> str:
        return {
            "municipales": "MUNICIPALES",
            "andaluzas": "ANDALUZAS",
            "congreso": "CONGRESO",
            "europeas": "EUROPEAS",
        }.get(election_type.lower(), election_type.upper())

    def _municipality_id(self, active_municipality: str | None) -> str:
        value = normalize(active_municipality or "29070")
        return "29070" if value in {"mijas", "29070"} else active_municipality or "29070"

    def _is_dataset_inventory_question(self, text: str) -> bool:
        return bool(re.search(r"que datos tienes|datos disponibles|datasets disponibles|fuentes disponibles", text))
