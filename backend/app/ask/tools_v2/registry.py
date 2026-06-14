from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, ClassVar, Type

from pydantic import BaseModel

from app.ask.llm.schemas import LLMToolSchema
from app.ask.semantic_layer import SemanticCatalog
from app.ask.sql import QueryExecutor, SqlValidator
from app.ask.tools_v2.result_normalizer import ResultNormalizer
from app.ask.tools_v2.schemas import (
    AgeCohortProjectionInput,
    AggregateMunicipalityInput,
    CompareYearsInput,
    CorrelationAnalysisInput,
    CrossMetricRankingInput,
    EcologicalVoteProfileByAgeGroupInput,
    ElectoralGrowthOpportunityInput,
    ElectoralViabilityEstimateInput,
    FilterSectionsInput,
    HistoricalPartyAverageInput,
    MobilizableAbstentionOpportunityInput,
    PartyStrengthInput,
    PersistentWinnerInput,
    PopulationGrowthInput,
    RankSectionsInput,
    SectionProfileInput,
    ToolContext,
    ToolDefinition,
    ToolResult,
)
from app.ask.tools_v2.sql_builders import BuiltSql, ToolSqlBuilders


logger = logging.getLogger(__name__)


class BaseTool:
    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[Type[BaseModel]]
    operation: ClassVar[str] = ""
    status: ClassVar[str] = "supported"
    examples: ClassVar[list[str]] = []

    def __init__(self, builders: ToolSqlBuilders, normalizer: ResultNormalizer, query_executor: QueryExecutor, sql_validator: SqlValidator):
        self.builders = builders
        self.normalizer = normalizer
        self.query_executor = query_executor
        self.sql_validator = sql_validator

    def openai_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema.model_json_schema(),
        }

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name=cls.name,
            description=cls.description,
            status=cls.status,
            input_model=cls.input_schema,
            operation=cls.operation or cls.name,
            examples=list(cls.examples),
        )

    @classmethod
    def llm_schema(cls) -> LLMToolSchema:
        return LLMToolSchema(
            name=cls.name,
            description=cls.description,
            parameters=cls.input_schema.model_json_schema(),
        )

    def _execute_sql(self, built, chart_type: str | None, caveats: list[str] | None = None, methodology: str | None = None) -> ToolResult:
        validation = self.sql_validator.validate(built.sql)
        if not validation.ok:
            logger.warning("ask_tool_v2_sql_validation_failed", extra={"tool_name": self.name, "sources": built.sources})
            return ToolResult(
                tool_name=self.name,
                operation=self.name,
                status="error",
                methodology_plain="He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas.",
                caveats=["La consulta interna no cumple el contrato SQL seguro de soctrace."],
                sources=built.sources,
                metadata=built.metadata,
                error_code="sql_validation_failed",
                error_message="No se ha podido validar la consulta interna.",
            )
        rows = self.query_executor.execute(built.sql)
        return self.normalizer.normalize(
            tool_name=self.name,
            operation=self.name,
            rows=rows,
            built=built,
            chart_type=chart_type,
            caveats=caveats,
            methodology=methodology,
        )


class RankSectionsTool(BaseTool):
    name = "rank_sections"
    description = "Ordena secciones censales de un municipio según una métrica aprobada, como población, edad media, renta, abstención o valor inmobiliario."
    input_schema = RankSectionsInput
    examples = ["¿Cuál es la sección con mayor población?", "¿Qué sección tiene más abstención?"]

    def execute(self, payload: RankSectionsInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.rank_sections(payload)
        chart = "metric" if payload.limit == 1 else "bar"
        return self._execute_sql(built, chart)


class AggregateMunicipalityTool(BaseTool):
    name = "aggregate_municipality"
    description = "Agrega una métrica aprobada a nivel municipal, como población total, mayores de 65 años o renta media."
    input_schema = AggregateMunicipalityInput
    examples = ["¿Cuál es la población total de Mijas?"]

    def execute(self, payload: AggregateMunicipalityInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.aggregate_municipality(payload)
        return self._execute_sql(built, "metric")


class CompareYearsTool(BaseTool):
    name = "compare_years"
    description = "Compara una métrica entre dos años para detectar aumentos, descensos, rejuvenecimiento o envejecimiento."
    input_schema = CompareYearsInput
    examples = ["¿Qué sección ha rejuvenecido más desde 2021?"]

    def execute(self, payload: CompareYearsInput, context: ToolContext | None = None) -> ToolResult:
        if payload.metric == "population_total" and payload.entity == "section":
            built = self.builders.population_growth(
                PopulationGrowthInput(
                    municipio_id=payload.municipio_id,
                    start_year=payload.start_year,
                    end_year=payload.end_year,
                    rank_by="growth_pct" if payload.order_by == "delta_pct" else "growth_abs",
                    order="asc" if payload.direction == "largest_decrease" else "desc",
                    limit=payload.limit,
                )
            )
            return self._execute_sql(built, "bar", ["Se usa lineage de secciones para evitar rupturas por splits administrativos."])
        built = self.builders.compare_years(payload)
        return self._execute_sql(built, "bar")


class PopulationGrowthTool(BaseTool):
    name = "population_growth"
    description = "Calcula crecimiento de población por zona histórica teniendo en cuenta cambios y divisiones de secciones."
    input_schema = PopulationGrowthInput
    examples = ["¿Qué zonas han crecido más?"]

    def execute(self, payload: PopulationGrowthInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.population_growth(payload)
        return self._execute_sql(built, "bar", ["Tiene en cuenta divisiones administrativas de secciones cuando hay lineage disponible."])


class FilterSectionsTool(BaseTool):
    name = "filter_sections"
    description = "Devuelve secciones que cumplen condiciones sobre métricas aprobadas, como superar un umbral de población o abstención."
    input_schema = FilterSectionsInput
    examples = ["¿Qué secciones superan los 5.000 habitantes?"]

    def execute(self, payload: FilterSectionsInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.filter_sections(payload)
        return self._execute_sql(built, "bar")


class SectionProfileTool(BaseTool):
    name = "section_profile"
    description = "Devuelve un perfil multidominio de una sección censal: población, renta, electoral y vivienda."
    input_schema = SectionProfileInput
    examples = ["¿Qué perfil tiene Riviera Sur?"]

    def execute(self, payload: SectionProfileInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.section_profile(payload)
        return self._execute_sql(built, None)


class PartyStrengthTool(BaseTool):
    name = "party_strength"
    description = "Ordena secciones según la fortaleza de voto de un partido en una elección o en promedio histórico."
    input_schema = PartyStrengthInput
    examples = ["¿Dónde es más fuerte el PP?"]

    def execute(self, payload: PartyStrengthInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.party_strength(payload)
        return self._execute_sql(built, "bar")


class PersistentWinnerTool(BaseTool):
    name = "persistent_winner"
    description = "Identifica secciones donde un partido ha sido primera fuerza en todas las elecciones disponibles o en un tipo de elección concreto."
    input_schema = PersistentWinnerInput
    examples = ["¿Dónde gana siempre el PP?"]

    def execute(self, payload: PersistentWinnerInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.persistent_winner(payload)
        return self._execute_sql(built, "bar")


class HistoricalPartyAverageTool(BaseTool):
    name = "historical_party_average"
    description = "Calcula la media histórica de voto de partidos por sección o el ranking histórico de secciones para un partido."
    input_schema = HistoricalPartyAverageInput
    examples = ["¿Qué partido es históricamente más fuerte en Riviera Sur?"]

    def execute(self, payload: HistoricalPartyAverageInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.historical_party_average(payload)
        return self._execute_sql(built, "bar")


class AgeCohortProjectionTool(BaseTool):
    name = "age_cohort_projection"
    description = "Calcula o estima población por cohorte de edad, incluyendo proyecciones simples como personas que tendrán 18 años en 2027."
    input_schema = AgeCohortProjectionInput
    examples = ["¿Cuántas personas tendrán 18 años en 2027?"]

    def execute(self, payload: AgeCohortProjectionInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.age_cohort_projection(payload)
        caveats = ["Estimacion basada en cohortes quinquenales."] if built.metadata.get("estimated") else ["Las edades se agregan por cohortes disponibles."]
        return self._execute_sql(built, "bar" if payload.group_by != "municipality" else "metric", caveats)


class EcologicalVoteProfileByAgeGroupTool(BaseTool):
    name = "ecological_vote_profile_by_age_group"
    description = (
        "Estima el perfil electoral territorial de un grupo de edad cruzando población por edad de cada sección "
        "con resultados electorales por sección. Úsala cuando se pregunte qué votan o qué partido domina entre mayores, jóvenes o menores."
    )
    input_schema = EcologicalVoteProfileByAgeGroupInput
    examples = ["¿Qué suelen votar las personas mayores de 45 años?", "¿Qué partido domina entre los jóvenes?"]

    def execute(self, payload: EcologicalVoteProfileByAgeGroupInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.ecological_vote_profile_by_age_group(payload)
        caveat = (
            "Esto no mide el voto individual por edad. soctrace no dispone de voto individual por edad. "
            "Es una estimación territorial: compara resultados electorales por sección con el peso del grupo de edad en esas mismas secciones."
        )
        methodology = (
            "Pondero el porcentaje de voto de cada partido en cada sección por el número estimado de personas del grupo de edad "
            "en esa sección; además calculo la media en secciones con mayor concentración y la correlación territorial."
        )
        return self._execute_sql(built, "age_vote_profile", [caveat], methodology)


class ElectoralViabilityEstimateTool(BaseTool):
    name = "electoral_viability_estimate"
    description = (
        "Estima la viabilidad electoral orientativa de un partido, o compara partidos, usando resultados historicos, "
        "secciones ganadas, margen competitivo y fuerza territorial. No devuelve probabilidad estadistica real."
    )
    input_schema = ElectoralViabilityEstimateInput
    status = "beta"
    examples = ["¿Qué probabilidades tiene el PP de ganar?", "¿Puede ganar el PSOE ahora?", "¿Qué partido tiene más posibilidades ahora?"]

    def execute(self, payload: ElectoralViabilityEstimateInput, context: ToolContext | None = None) -> ToolResult:
        built = self._build_sql(payload)
        validation = self.sql_validator.validate(built.sql)
        if not validation.ok:
            return ToolResult(
                tool_name=self.name,
                operation=self.name,
                status="error",
                methodology_plain="He entendido la consulta, pero ahora mismo no puedo calcularla con las herramientas activas.",
                caveats=["La consulta interna no cumple el contrato SQL seguro de soctrace."],
                sources=built.sources,
                metadata=built.metadata,
                error_code="sql_validation_failed",
                error_message="No se ha podido validar la consulta interna.",
            )
        rows = self.query_executor.execute(built.sql)
        normalized = [self._score_row(row, payload) for row in rows]
        status = "ok" if normalized else "empty"
        summary = self._summary(normalized, payload)
        return ToolResult(
            tool_name=self.name,
            operation=self.name,
            status=status,
            rows=normalized,
            summary=summary,
            metadata={
                **built.metadata,
                "municipio_id": payload.municipio_id,
                "metric": "electoral_viability",
                "metric_label": "viabilidad electoral orientativa",
                "party": None if payload.party == "ALL" else payload.party,
                "estimate_type": "electoral_viability",
                "analysis_type": "electoral_viability",
                "topic": "electoral",
                "intent": "viability_analysis",
                "derived_estimate": True,
                "inputs": payload.model_dump(),
                "result": summary,
            },
            chart_spec={"type": "bar", "title": "Índice orientativo de viabilidad electoral", "x": "party", "y": "viability_index", "rows": normalized} if len(normalized) > 1 else {"type": "metric", "title": "Índice orientativo de viabilidad electoral", "value": normalized[0].get("viability_index") if normalized else None, "label": "viabilidad orientativa", "rows": normalized[:1]},
            methodology_plain=(
                "Estimación orientativa basada en datos históricos y territoriales: porcentaje de voto en las últimas municipales, "
                "posición municipal, secciones donde fue primera fuerza, margen frente al principal rival, media histórica, tendencia y secciones competitivas. "
                "No es una probabilidad estadística real porque no incorpora sondeos actuales ni un modelo probabilístico validado."
            ),
            caveats=[
                "No es una probabilidad estadística real ni una predicción de sondeo.",
                "Es una estimación orientativa construida con datos históricos y territoriales disponibles en soctrace.",
            ],
            suggested_followups=[
                f"¿En qué secciones tendría más margen de crecimiento {payload.party if payload.party != 'ALL' else 'el PP'}?",
                "¿Qué secciones debería priorizar el PP?",
                "¿Y comparado con PSOE?",
            ],
            sources=built.sources,
        )

    def _build_sql(self, payload: ElectoralViabilityEstimateInput):
        election_type = payload.election_type.upper()
        year_filter = f"AND election_year = {int(payload.baseline_year)}" if payload.baseline_year else ""
        party_filter = "" if payload.party == "ALL" else f"AND UPPER(canonical_party) = {self.builders._literal(payload.party)}"
        competitive_select = (
            "COUNT(*) FILTER (WHERE ABS(latest.vote_pct - latest.main_opponent_vote_pct) <= 5)::integer AS competitive_sections,"
            if payload.include_competitiveness
            else "NULL::integer AS competitive_sections,"
        )
        abstention_select = (
            "ROUND(AVG(summary.abstention_pct)::numeric, 2) AS average_abstention_pct,"
            if payload.include_abstention
            else "NULL::numeric AS average_abstention_pct,"
        )
        if payload.include_other_elections:
            historical_party_expr = "UPPER(canonical_party)"
            historical_source = "marts.agent_electoral_results"
            historical_where = f"""
    WHERE municipio_id = {self.builders._literal(payload.municipio_id)}
      AND election_type = {self.builders._literal(election_type)}
      {party_filter}
      AND vote_pct IS NOT NULL
""".rstrip()
        else:
            historical_party_expr = "party"
            historical_source = "latest"
            historical_where = "    WHERE vote_pct IS NOT NULL"
        sql = f"""
WITH selected_year AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_results
    WHERE municipio_id = {self.builders._literal(payload.municipio_id)}
      AND election_type = {self.builders._literal(election_type)}
      {year_filter}
),
raw_latest AS (
    SELECT
        r.section_id,
        r.section_name,
        r.municipio_id,
        r.municipio_nombre,
        r.election_year,
        UPPER(r.canonical_party) AS party,
        r.vote_pct,
        s.winner_party,
        MAX(r.vote_pct) OVER (PARTITION BY r.section_id, r.election_year) AS section_winner_vote_pct,
        MAX(r.vote_pct) FILTER (WHERE UPPER(r.canonical_party) <> UPPER(s.winner_party)) OVER (PARTITION BY r.section_id, r.election_year) AS main_opponent_vote_pct
    FROM marts.agent_electoral_results r
    JOIN selected_year y ON y.election_year = r.election_year
    LEFT JOIN marts.agent_electoral_summary s
      ON s.section_id = r.section_id
     AND s.municipio_id = r.municipio_id
     AND s.election_type = r.election_type
     AND s.election_year = r.election_year
    WHERE r.municipio_id = {self.builders._literal(payload.municipio_id)}
      AND r.election_type = {self.builders._literal(election_type)}
      AND r.vote_pct IS NOT NULL
),
latest AS (
    SELECT *
    FROM raw_latest
    WHERE 1 = 1
      {party_filter.replace('canonical_party', 'party')}
),
party_totals AS (
    SELECT
        party,
        MAX(municipio_id) AS municipio_id,
        MAX(municipio_nombre) AS municipio_nombre,
        MAX(election_year) AS latest_municipal_year,
        ROUND(AVG(vote_pct)::numeric, 2) AS latest_municipal_vote_pct,
        COUNT(*) FILTER (WHERE UPPER(winner_party) = party)::integer AS sections_won,
        COUNT(*)::integer AS sections_total,
        ROUND(AVG(vote_pct - COALESCE(main_opponent_vote_pct, section_winner_vote_pct))::numeric, 2) AS margin_vs_main_opponent,
        {competitive_select}
        ROUND(AVG(section_winner_vote_pct - vote_pct)::numeric, 2) AS average_gap_to_section_winner
    FROM latest
    GROUP BY party
),
historical AS (
    SELECT
        {historical_party_expr} AS party,
        ROUND(AVG(vote_pct)::numeric, 2) AS average_historical_vote_pct,
        ROUND((AVG(vote_pct) FILTER (WHERE election_year = (SELECT MAX(election_year) FROM {historical_source})) - AVG(vote_pct) FILTER (WHERE election_year = (SELECT MIN(election_year) FROM {historical_source})))::numeric, 2) AS trend_delta
    FROM {historical_source}
{historical_where}
    GROUP BY {historical_party_expr}
),
municipal_rank AS (
    SELECT
        party,
        DENSE_RANK() OVER (ORDER BY latest_municipal_vote_pct DESC) AS latest_municipal_position
    FROM party_totals
),
summary AS (
    SELECT municipio_id, election_year, abstention_pct
    FROM marts.agent_electoral_summary
    WHERE municipio_id = {self.builders._literal(payload.municipio_id)}
      AND election_type = {self.builders._literal(election_type)}
      AND election_year = (SELECT election_year FROM selected_year)
)
SELECT
    p.party,
    p.municipio_id,
    p.municipio_nombre,
    p.latest_municipal_year,
    p.latest_municipal_vote_pct,
    r.latest_municipal_position::integer,
    p.sections_won,
    p.sections_total,
    h.average_historical_vote_pct,
    CASE
        WHEN h.trend_delta > 1 THEN 'ascendente'
        WHEN h.trend_delta < -1 THEN 'descendente'
        ELSE 'estable'
    END AS trend_direction,
    h.trend_delta,
    p.margin_vs_main_opponent,
    p.competitive_sections,
    ROUND((p.sections_won::numeric / NULLIF(p.sections_total, 0) * 100)::numeric, 2) AS territorial_strength_score,
    p.average_gap_to_section_winner,
    {abstention_select}
    p.latest_municipal_vote_pct AS value
FROM party_totals p
JOIN historical h USING (party)
JOIN municipal_rank r USING (party)
CROSS JOIN summary
GROUP BY p.party, p.municipio_id, p.municipio_nombre, p.latest_municipal_year, p.latest_municipal_vote_pct, r.latest_municipal_position, p.sections_won, p.sections_total, h.average_historical_vote_pct, h.trend_delta, p.margin_vs_main_opponent, p.competitive_sections, p.average_gap_to_section_winner
ORDER BY p.latest_municipal_vote_pct DESC, p.party
LIMIT {10 if payload.party == 'ALL' else 1}
""".strip()
        return BuiltSql(
            sql=sql,
            sources=["marts.agent_electoral_results", "marts.agent_electoral_summary", "marts.agent_section_profile"],
            metadata={"value_label": "índice orientativo de viabilidad", "election_type": election_type},
        )

    def _score_row(self, row: dict[str, Any], payload: ElectoralViabilityEstimateInput) -> dict[str, Any]:
        result = dict(row)
        vote = self._float(result.get("latest_municipal_vote_pct"))
        historical = self._float(result.get("average_historical_vote_pct"))
        margin = self._float(result.get("margin_vs_main_opponent"))
        territorial = self._float(result.get("territorial_strength_score"))
        trend_delta = self._float(result.get("trend_delta"))
        position = int(result.get("latest_municipal_position") or 9)
        position_score = max(0.0, 100.0 - ((position - 1) * 25.0))
        margin_score = max(0.0, min(100.0, 50.0 + margin * 2.0))
        trend_score = max(0.0, min(100.0, 50.0 + trend_delta * 3.0))
        viability = round(
            (vote * 1.3)
            + (historical * 0.8)
            + (territorial * 0.25)
            + (position_score * 0.15)
            + (margin_score * 0.15)
            + (trend_score * 0.1),
            1,
        )
        viability = max(0.0, min(100.0, viability))
        result["viability_index"] = viability
        result["viability_label"] = self._label(viability)
        result["value"] = viability
        result["value_label"] = "índice orientativo de viabilidad"
        result["derived_estimate"] = True
        result["estimate_type"] = "electoral_viability"
        result["inputs"] = payload.model_dump()
        return result

    def _summary(self, rows: list[dict[str, Any]], payload: ElectoralViabilityEstimateInput) -> dict[str, Any]:
        if not rows:
            return {"row_count": 0, "derived_estimate": True, "estimate_type": "electoral_viability", "inputs": payload.model_dump()}
        first = rows[0]
        return {
            "row_count": len(rows),
            "derived_estimate": True,
            "estimate_type": "electoral_viability",
            "analysis_type": "electoral_viability",
            "topic": "electoral",
            "intent": "viability_analysis",
            "party": None if payload.party == "ALL" else payload.party,
            "label": f"viabilidad electoral {payload.party} ahora" if payload.party != "ALL" else "viabilidad electoral principales partidos ahora",
            "inputs": payload.model_dump(),
            "result": first if payload.party != "ALL" else {"top_party": first.get("party"), "rows": rows},
            "methodology": "Índice orientativo con datos históricos y territoriales; no es una probabilidad estadística real.",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "value_label": "índice orientativo de viabilidad",
            "top_value": first.get("viability_index"),
            "top_party": first.get("party"),
            "year": first.get("latest_municipal_year"),
        }

    def _label(self, score: float) -> str:
        if score >= 75:
            return "alta"
        if score >= 62:
            return "media-alta"
        if score >= 48:
            return "media"
        if score >= 35:
            return "media-baja"
        return "baja"

    def _float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0


class ElectoralGrowthOpportunityTool(BaseTool):
    name = "electoral_growth_opportunity"
    description = "Identifica secciones donde un partido tiene mayor potencial realista de crecimiento electoral por margen, abstención, volatilidad y fortaleza histórica."
    input_schema = ElectoralGrowthOpportunityInput
    status = "beta"
    examples = ["¿Dónde tiene más margen de crecimiento el PP?", "¿Qué zonas debería reforzar el PSOE?"]

    def execute(self, payload: ElectoralGrowthOpportunityInput, context: ToolContext | None = None) -> ToolResult:
        election_type = payload.election_type.upper()
        year_filter = f"AND election_year = {int(payload.election_year)}" if payload.election_year else ""
        sql = f"""
WITH selected_year AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_results
    WHERE municipio_id = {self.builders._literal(payload.municipio_id)}
      AND election_type = {self.builders._literal(election_type)}
      {year_filter}
),
latest_party AS (
    SELECT
        r.section_id,
        r.section_name,
        r.municipio_id,
        r.municipio_nombre,
        r.election_year,
        UPPER(r.canonical_party) AS party,
        r.vote_pct,
        r.votes,
        s.winner_party,
        s.winner_vote_pct,
        s.margin_pct,
        s.abstention_pct,
        s.participation_pct
    FROM marts.agent_electoral_results r
    JOIN selected_year y ON y.election_year = r.election_year
    LEFT JOIN marts.agent_electoral_summary s
      ON s.section_id = r.section_id
     AND s.municipio_id = r.municipio_id
     AND s.election_type = r.election_type
     AND s.election_year = r.election_year
    WHERE r.municipio_id = {self.builders._literal(payload.municipio_id)}
      AND r.election_type = {self.builders._literal(election_type)}
      AND UPPER(r.canonical_party) = {self.builders._literal(payload.party)}
      AND r.vote_pct IS NOT NULL
),
historical AS (
    SELECT
        section_id,
        ROUND(AVG(vote_pct)::numeric, 2) AS historical_vote_pct,
        ROUND(MAX(vote_pct)::numeric, 2) AS historical_best_vote_pct,
        ROUND((MAX(vote_pct) - MIN(vote_pct))::numeric, 2) AS volatility_pct
    FROM marts.agent_electoral_results
    WHERE municipio_id = {self.builders._literal(payload.municipio_id)}
      AND election_type = {self.builders._literal(election_type)}
      AND UPPER(canonical_party) = {self.builders._literal(payload.party)}
      AND vote_pct IS NOT NULL
    GROUP BY section_id
),
scored AS (
    SELECT
        latest_party.*,
        historical.historical_vote_pct,
        historical.historical_best_vote_pct,
        historical.volatility_pct,
        GREATEST(COALESCE(latest_party.winner_vote_pct, latest_party.vote_pct) - latest_party.vote_pct, 0) AS gap_to_first_pct,
        GREATEST(COALESCE(historical.historical_best_vote_pct, latest_party.vote_pct) - latest_party.vote_pct, 0) AS recovery_room_pct
    FROM latest_party
    LEFT JOIN historical USING (section_id)
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    election_year,
    party,
    vote_pct,
    winner_party,
    winner_vote_pct,
    ROUND(gap_to_first_pct::numeric, 2) AS margin_to_first_place,
    historical_vote_pct,
    historical_best_vote_pct,
    ROUND(COALESCE(abstention_pct, 0)::numeric, 2) AS abstention_pct,
    ROUND(COALESCE(volatility_pct, 0)::numeric, 2) AS volatility_pct,
    ROUND(recovery_room_pct::numeric, 2) AS historical_recovery_room_pct,
    ROUND((
        LEAST(GREATEST(30 - gap_to_first_pct, 0), 30) * 1.4
        + LEAST(COALESCE(abstention_pct, 0), 60) * 0.55
        + LEAST(COALESCE(volatility_pct, 0), 25) * 0.7
        + LEAST(recovery_room_pct, 20) * 1.2
        + CASE WHEN UPPER(winner_party) = party THEN 12 ELSE 0 END
    )::numeric, 2) AS growth_score,
    CASE
        WHEN UPPER(winner_party) = party THEN 'defensa y expansión desde posición fuerte'
        WHEN gap_to_first_pct <= 5 THEN 'sección competitiva: pequeña mejora puede cambiar la posición'
        WHEN gap_to_first_pct <= 12 THEN 'oportunidad media: necesita captación y movilización'
        ELSE 'crecimiento posible, pero requiere giro territorial relevante'
    END AS opportunity_explanation,
    ROUND((
        LEAST(GREATEST(30 - gap_to_first_pct, 0), 30) * 1.4
        + LEAST(COALESCE(abstention_pct, 0), 60) * 0.55
        + LEAST(COALESCE(volatility_pct, 0), 25) * 0.7
        + LEAST(recovery_room_pct, 20) * 1.2
        + CASE WHEN UPPER(winner_party) = party THEN 12 ELSE 0 END
    )::numeric, 2) AS value
FROM scored
ORDER BY growth_score DESC, gap_to_first_pct ASC, section_name
LIMIT {int(payload.limit)}
""".strip()
        built = BuiltSql(
            sql=sql,
            sources=["marts.agent_electoral_results", "marts.agent_electoral_summary"],
            metadata={
                "metric": "electoral_growth_opportunity",
                "value_label": "potencial de crecimiento electoral",
                "party": payload.party,
                "election_type": election_type,
            },
        )
        methodology = (
            "Calculo una oportunidad electoral por sección combinando distancia a la primera fuerza, abstención, volatilidad histórica, "
            "capacidad de recuperación frente al mejor resultado histórico y fortaleza local reciente."
        )
        result = self._execute_sql(built, "bar", ["Es una priorización estratégica orientativa, no una predicción de votos."], methodology)
        result.suggested_followups = [
            f"¿Cuántos votos necesitaría {payload.party} en esas secciones?",
            f"Comparar estas oportunidades con PSOE",
            "Construir un escenario con reducción de abstención",
        ]
        result.summary.update({
            "analysis_type": "electoral_growth_opportunity",
            "topic": "electoral",
            "party": payload.party,
            "intent": "electoral_growth_opportunity",
        })
        result.metadata.update({
            "analysis_type": "electoral_growth_opportunity",
            "topic": "electoral",
            "party": payload.party,
            "intent": "electoral_growth_opportunity",
        })
        return result


class MobilizableAbstentionOpportunityTool(BaseTool):
    name = "mobilizable_abstention_opportunity"
    description = "Identifica secciones con mayor oportunidad territorial de movilizar abstención, general o dirigida a un partido/bloque."
    input_schema = MobilizableAbstentionOpportunityInput
    status = "beta"
    examples = ["¿Dónde hay más abstención movilizable?", "¿Qué secciones tienen más abstencionistas potenciales?"]

    def execute(self, payload: MobilizableAbstentionOpportunityInput, context: ToolContext | None = None) -> ToolResult:
        election_type = payload.election_type.upper()
        year_filter = f"AND election_year = {int(payload.election_year)}" if payload.election_year else ""
        target = payload.target
        target_join = ""
        target_select = "NULL::numeric AS target_strength_pct,"
        target_component = "0"
        target_weighted_score = """
        0.45 * abstention_component
        + 0.25 * electoral_weight_component
        + 0.30 * competitiveness_component
"""
        if target in {"PP", "PSOE", "VOX"}:
            target_join = f"""
LEFT JOIN marts.agent_electoral_results target_result
  ON target_result.section_id = summary.section_id
 AND target_result.municipio_id = summary.municipio_id
 AND target_result.election_type = summary.election_type
 AND target_result.election_year = summary.election_year
 AND UPPER(target_result.canonical_party) = {self.builders._literal(target)}
"""
            target_select = "COALESCE(target_result.vote_pct, 0)::numeric AS target_strength_pct,"
            target_component = "LEAST(COALESCE(target_strength_pct, 0), 60) / 60.0"
        elif target in {"left", "right"}:
            bloc_parties = ("'PSOE', 'IU', 'PODEMOS', 'SUMAR', 'MAS PAIS'") if target == "left" else ("'PP', 'VOX', 'CS'")
            target_join = f"""
LEFT JOIN (
    SELECT
        section_id,
        municipio_id,
        election_type,
        election_year,
        SUM(vote_pct)::numeric AS target_strength_pct
    FROM marts.agent_electoral_results
    WHERE UPPER(canonical_party) IN ({bloc_parties})
    GROUP BY section_id, municipio_id, election_type, election_year
) target_result
  ON target_result.section_id = summary.section_id
 AND target_result.municipio_id = summary.municipio_id
 AND target_result.election_type = summary.election_type
 AND target_result.election_year = summary.election_year
"""
            target_select = "COALESCE(target_result.target_strength_pct, 0)::numeric AS target_strength_pct,"
            target_component = "LEAST(COALESCE(target_strength_pct, 0), 70) / 70.0"
        if target != "general":
            target_weighted_score = f"""
        0.35 * abstention_component
        + 0.25 * ({target_component})
        + 0.20 * competitiveness_component
        + 0.20 * electoral_weight_component
"""
        sql = f"""
WITH selected_year AS (
    SELECT MAX(election_year) AS election_year
    FROM marts.agent_electoral_summary
    WHERE municipio_id = {self.builders._literal(payload.municipio_id)}
      AND election_type = {self.builders._literal(election_type)}
      {year_filter}
),
base AS (
    SELECT
        summary.section_id,
        summary.section_name,
        summary.municipio_id,
        summary.municipio_nombre,
        summary.election_year,
        summary.election_type,
        summary.census,
        summary.participation_pct,
        summary.abstention_pct,
        summary.margin_pct,
        summary.winner_party,
        profile.population_total,
        {target_select}
        ROUND((summary.census * summary.abstention_pct / 100.0)::numeric, 0)::bigint AS estimated_abstainers
    FROM marts.agent_electoral_summary summary
    JOIN selected_year ON selected_year.election_year = summary.election_year
    LEFT JOIN marts.agent_section_profile profile
      ON profile.section_id = summary.section_id
     AND profile.municipio_id = summary.municipio_id
     AND profile.year = (SELECT MAX(year) FROM marts.agent_section_profile WHERE municipio_id = {self.builders._literal(payload.municipio_id)})
    {target_join}
    WHERE summary.municipio_id = {self.builders._literal(payload.municipio_id)}
      AND summary.election_type = {self.builders._literal(election_type)}
      AND summary.abstention_pct IS NOT NULL
),
components AS (
    SELECT
        *,
        LEAST(COALESCE(abstention_pct, 0), 60) / 60.0 AS abstention_component,
        COALESCE(census::numeric, population_total::numeric, 0) / NULLIF(MAX(COALESCE(census::numeric, population_total::numeric, 0)) OVER (), 0) AS electoral_weight_component,
        GREATEST(0, 1 - LEAST(COALESCE(margin_pct, 30), 30) / 30.0) AS competitiveness_component
    FROM base
),
scored AS (
    SELECT
        *,
        ROUND(({target_weighted_score})::numeric, 4) AS score
    FROM components
)
SELECT
    section_id,
    section_name,
    municipio_id,
    municipio_nombre,
    election_year,
    abstention_pct,
    participation_pct,
    margin_pct,
    winner_party,
    census,
    population_total,
    target_strength_pct,
    estimated_abstainers,
    score,
    CASE
        WHEN score >= 0.8 THEN 'oportunidad muy alta de movilización territorial'
        WHEN score >= 0.6 THEN 'oportunidad alta de movilización territorial'
        WHEN score >= 0.4 THEN 'oportunidad media de movilización territorial'
        ELSE 'oportunidad baja o condicionada'
    END AS interpretation,
    score AS value
FROM scored
ORDER BY score DESC, estimated_abstainers DESC, section_name
LIMIT {int(payload.limit)}
""".strip()
        built = BuiltSql(
            sql=sql,
            sources=["marts.agent_electoral_summary", "marts.agent_electoral_results", "marts.agent_section_profile"],
            metadata={
                "metric": "mobilizable_abstention",
                "value_label": "Índice de abstención movilizable",
                "target": target,
                "election_type": election_type,
            },
        )
        result = self._execute_sql(
            built,
            "bar",
            ["No predice voto individual; prioriza secciones por oportunidad territorial de movilización."],
            "Combino nivel de abstención, peso electoral, competitividad y afinidad territorial cuando hay un objetivo político definido.",
        )
        result.suggested_followups = [
            "¿Qué secciones tienen mayor abstención?",
            "¿Qué zonas debería priorizar una campaña de movilización?",
            "¿Dónde hay más abstención movilizable para PSOE?",
        ]
        result.summary.update({"analysis_type": "mobilizable_abstention", "target": target, "topic": "electoral"})
        result.metadata.update({"analysis_type": "mobilizable_abstention", "target": target, "topic": "electoral"})
        return result


class CrossMetricRankingTool(BaseTool):
    name = "cross_metric_ranking"
    description = "Ordena secciones mediante un índice beta que combina varias métricas normalizadas, como renta baja y abstención alta."
    input_schema = CrossMetricRankingInput
    status = "beta"
    examples = ["¿Qué secciones combinan renta baja y alta abstención?"]

    def execute(self, payload: CrossMetricRankingInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.cross_metric_ranking(payload)
        return self._execute_sql(built, "bar", ["Es un índice territorial compuesto, no una relación causal."])


class CorrelationAnalysisTool(BaseTool):
    name = "correlation_analysis"
    description = "Explora la correlación beta a nivel de sección entre dos métricas aprobadas, como renta y abstención."
    input_schema = CorrelationAnalysisInput
    status = "beta"
    examples = ["¿Existe relación entre renta y abstención?"]

    def execute(self, payload: CorrelationAnalysisInput, context: ToolContext | None = None) -> ToolResult:
        built = self.builders.correlation_analysis(payload)
        return self._execute_sql(built, "scatter", ["Correlacion no implica causalidad; analisis ecologico por seccion."])


TOOL_CLASSES: dict[str, type[BaseTool]] = {
    "rank_sections": RankSectionsTool,
    "aggregate_municipality": AggregateMunicipalityTool,
    "compare_years": CompareYearsTool,
    "population_growth": PopulationGrowthTool,
    "filter_sections": FilterSectionsTool,
    "section_profile": SectionProfileTool,
    "party_strength": PartyStrengthTool,
    "persistent_winner": PersistentWinnerTool,
    "historical_party_average": HistoricalPartyAverageTool,
    "age_cohort_projection": AgeCohortProjectionTool,
    "ecological_vote_profile_by_age_group": EcologicalVoteProfileByAgeGroupTool,
    "electoral_viability_estimate": ElectoralViabilityEstimateTool,
    "electoral_growth_opportunity": ElectoralGrowthOpportunityTool,
    "mobilizable_abstention_opportunity": MobilizableAbstentionOpportunityTool,
    "cross_metric_ranking": CrossMetricRankingTool,
    "correlation_analysis": CorrelationAnalysisTool,
}


class ToolRegistryV2:
    def __init__(self, query_executor: QueryExecutor, sql_validator: SqlValidator, catalog: SemanticCatalog | None = None, *, debug_mode: bool = False):
        self.catalog = catalog or SemanticCatalog()
        self.debug_mode = debug_mode
        builders = ToolSqlBuilders(self.catalog)
        normalizer = ResultNormalizer(self.catalog)
        self.tools = {
            name: tool_class(builders, normalizer, query_executor, sql_validator)
            for name, tool_class in TOOL_CLASSES.items()
        }

    def get(self, name: str) -> BaseTool | None:
        return self.get_tool(name)

    def get_tool(self, tool_name: str) -> BaseTool | None:
        tool = self.tools.get(tool_name)
        if tool is not None and getattr(tool, "status", "supported") == "hidden" and not self.debug_mode:
            return None
        return tool

    def list_tools(self, status: list[str] | None = None) -> list[BaseTool]:
        allowed = set(status or [])
        tools = list(self.tools.values())
        if not status:
            return tools
        return [tool for tool in tools if getattr(tool, "status", "supported") in allowed]

    def get_llm_tool_schemas(self, include_beta: bool = True) -> list[LLMToolSchema]:
        return get_llm_tool_schemas(include_beta=include_beta)

    def openai_schemas(self) -> list[dict[str, Any]]:
        return [tool.openai_schema() for tool in self.tools.values()]

    def llm_tool_schemas(self, include_beta: bool = True) -> list[LLMToolSchema]:
        return get_llm_tool_schemas(include_beta=include_beta)


TOOL_REGISTRY = TOOL_CLASSES


def get_llm_tool_schemas(include_beta: bool = True) -> list[LLMToolSchema]:
    schemas: list[LLMToolSchema] = []
    seen: set[str] = set()
    for name in sorted(TOOL_CLASSES):
        tool_class = TOOL_CLASSES[name]
        status = getattr(tool_class, "status", "supported")
        if status == "pending":
            continue
        if status == "beta" and not include_beta:
            continue
        if status not in {"supported", "beta"}:
            continue
        if tool_class.name in seen:
            raise ValueError(f"Duplicate Tool v2 name: {tool_class.name}")
        seen.add(tool_class.name)
        schemas.append(tool_class.llm_schema())
    return schemas
