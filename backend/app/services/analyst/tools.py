from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services.dataset_access import ApprovedDatasetAccess
from app.services.local_analyst_service import DHondtCalculator


def _municipality_id(value: str) -> str:
    return "29070" if value.strip().lower() == "mijas" else value.strip()


def _election_type(value: str | None) -> str:
    if not value:
        return "MUNICIPALES"
    return {
        "municipales": "MUNICIPALES",
        "municipal": "MUNICIPALES",
        "andaluzas": "ANDALUZAS",
        "congreso": "CONGRESO",
        "europeas": "EUROPEAS",
    }.get(value.strip().lower(), value.strip().upper())


@dataclass(slots=True)
class AnalystToolResult:
    name: str
    rows: list[dict[str, Any]]
    data_used: list[str]
    methodology: str
    warnings: list[str]


class PoliticalAnalystTools:
    def __init__(self, session: Session):
        self.session = session
        self.datasets = ApprovedDatasetAccess()
        self.dhondt = DHondtCalculator()

    def get_section_profile(self, municipality_id: str, section_id: str, year: int = 2023) -> AnalystToolResult:
        data_used = [
            "marts.dim_seccion_display",
            "marts.v_population_layer",
            "marts.v_mapa_age_structure_2023",
            "marts.v_income_level_layer",
            "marts.v_land_built_environment",
            "marts.mv_electoral_behavior",
        ]
        self.datasets.require(*data_used)
        row = self.session.execute(
            text(
                """
                SELECT
                    display.seccion_id AS section_id,
                    COALESCE(display.label_cliente, display.seccion_id) AS section_name,
                    display.nombre_barrio,
                    display.zona_macro,
                    pop.pob_total AS population_total,
                    pop.densidad AS population_density,
                    age.average_age,
                    age.under_30_pct,
                    age.over_65_pct,
                    income.renta_media_persona AS individual_income,
                    income.renta_media_hogar AS household_income,
                    land.urban_intensity_index,
                    land.densidad_parcelaria AS parcel_density,
                    eb.winning_party_family AS winning_party,
                    ROUND(eb.winning_party_pct::numeric, 2) AS winning_party_pct,
                    ROUND(100 * (eb.censo - eb.votos_emitidos)::numeric / NULLIF(eb.censo, 0), 2) AS abstention_rate_pct
                FROM marts.dim_seccion_display display
                LEFT JOIN marts.v_population_layer pop
                  ON pop.seccion_id = display.seccion_id
                 AND pop.anio = :year
                LEFT JOIN marts.v_mapa_age_structure_2023 age
                  ON age.seccion_id = display.seccion_id
                LEFT JOIN marts.v_income_level_layer income
                  ON income.seccion_id = display.seccion_id
                 AND income.anio = :year
                LEFT JOIN marts.v_land_built_environment land
                  ON land.seccion_id = display.seccion_id
                 AND land.anio = :year
                LEFT JOIN marts.mv_electoral_behavior eb
                  ON eb.seccion_id = display.seccion_id
                 AND eb.anio = :year
                 AND eb.tipo_eleccion_code = 'MUNICIPALES'
                WHERE LEFT(display.seccion_id, 5) = :municipality_id
                  AND display.seccion_id = :section_id
                LIMIT 1
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "section_id": section_id, "year": year},
        ).mappings().first()
        return AnalystToolResult(
            name="get_section_profile",
            rows=[dict(row)] if row else [],
            data_used=data_used,
            methodology="Perfil seccional construido con joins parametrizados sobre vistas internas aprobadas.",
            warnings=[] if row else ["No section profile was found for the requested section."],
        )

    def get_population_trend(self, municipality_id: str, year: int = 2023, limit: int = 10) -> AnalystToolResult:
        data_used = ["marts.v_population_layer", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH population AS (
                    SELECT
                        seccion_id,
                        anio,
                        pob_total
                    FROM marts.v_population_layer
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND anio IN (:year, :previous_year)
                ),
                pivoted AS (
                    SELECT
                        seccion_id,
                        MAX(pob_total) FILTER (WHERE anio = :year) AS population_current,
                        MAX(pob_total) FILTER (WHERE anio = :previous_year) AS population_previous
                    FROM population
                    GROUP BY seccion_id
                )
                SELECT
                    p.seccion_id AS section_id,
                    COALESCE(d.label_cliente, p.seccion_id) AS section_name,
                    p.population_current,
                    p.population_previous,
                    ROUND(
                        100 * (p.population_current - p.population_previous)::numeric
                        / NULLIF(p.population_previous, 0),
                        2
                    ) AS population_growth_pct
                FROM pivoted p
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = p.seccion_id
                WHERE p.population_current IS NOT NULL
                  AND p.population_previous IS NOT NULL
                ORDER BY population_growth_pct DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "year": year,
                "previous_year": year - 4,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="get_population_trend",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=f"Comparacion de poblacion por seccion entre {year - 4} y {year}.",
            warnings=[],
        )

    def get_population_ranking(self, municipality_id: str, year: int | None = 2023, limit: int = 10) -> AnalystToolResult:
        data_used = ["marts.v_population_layer", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH filtered_population AS (
                    SELECT
                        seccion_id,
                        anio,
                        pob_total,
                        densidad
                    FROM marts.v_population_layer
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND (:year IS NULL OR anio = :year)
                ),
                selected_year AS (
                    SELECT MAX(anio) AS anio
                    FROM filtered_population
                )
                SELECT
                    pop.seccion_id AS section_id,
                    COALESCE(d.label_cliente, pop.seccion_id) AS section_name,
                    pop.anio AS year,
                    pop.pob_total AS population_total,
                    pop.densidad AS population_density
                FROM filtered_population pop
                JOIN selected_year selected
                  ON selected.anio = pop.anio
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = pop.seccion_id
                ORDER BY pop.pob_total DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year, "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="get_population_ranking",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=(
                f"Ranking de secciones por poblacion total observada en {year}."
                if year
                else "Ranking de secciones por poblacion total observada en el ultimo año disponible."
            ),
            warnings=[] if rows else ["No population rows were found for the requested year."],
        )

    def get_elderly_population_ranking(self, municipality_id: str, year: int | None = None, limit: int = 10) -> AnalystToolResult:
        data_used = ["marts.v_population_layer", "marts.v_mapa_age_structure_2023", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH filtered_population AS (
                    SELECT
                        seccion_id,
                        anio,
                        pob_total
                    FROM marts.v_population_layer
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND (:year IS NULL OR anio = :year)
                ),
                selected_year AS (
                    SELECT MAX(anio) AS anio
                    FROM filtered_population
                )
                SELECT
                    pop.seccion_id AS section_id,
                    COALESCE(d.label_cliente, pop.seccion_id) AS section_name,
                    pop.anio AS year,
                    pop.pob_total AS population_total,
                    age.over_65_pct,
                    ROUND(pop.pob_total * age.over_65_pct / 100.0)::bigint AS elderly_population
                FROM filtered_population pop
                JOIN selected_year selected
                  ON selected.anio = pop.anio
                JOIN marts.v_mapa_age_structure_2023 age
                  ON age.seccion_id = pop.seccion_id
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = pop.seccion_id
                WHERE age.over_65_pct IS NOT NULL
                ORDER BY elderly_population DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year, "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="get_age_structure",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=(
                "Ranking de secciones por número estimado de personas mayores: "
                "poblacion total por seccion multiplicada por porcentaje over_65_pct de la capa de edad."
            ),
            warnings=[] if rows else ["No age-structure rows were found for the requested query."],
        )

    def get_population_change_ranking(
        self,
        municipality_id: str,
        *,
        start_year: int,
        end_year: int,
        limit: int = 10,
    ) -> AnalystToolResult:
        data_used = ["marts.v_population_layer", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH population AS (
                    SELECT
                        seccion_id,
                        anio,
                        pob_total
                    FROM marts.v_population_layer
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND anio IN (:start_year, :end_year)
                ),
                pivoted AS (
                    SELECT
                        seccion_id,
                        MAX(pob_total) FILTER (WHERE anio = :start_year) AS population_start,
                        MAX(pob_total) FILTER (WHERE anio = :end_year) AS population_end
                    FROM population
                    GROUP BY seccion_id
                )
                SELECT
                    p.seccion_id AS section_id,
                    COALESCE(d.label_cliente, p.seccion_id) AS section_name,
                    p.population_start,
                    p.population_end,
                    p.population_end - p.population_start AS population_change,
                    ROUND(
                        100 * (p.population_end - p.population_start)::numeric
                        / NULLIF(p.population_start, 0),
                        2
                    ) AS population_change_pct
                FROM pivoted p
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = p.seccion_id
                WHERE p.population_start IS NOT NULL
                  AND p.population_end IS NOT NULL
                ORDER BY ABS(p.population_end - p.population_start) DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "start_year": start_year,
                "end_year": end_year,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="get_population_change_ranking",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=f"Comparacion de cambio absoluto de poblacion por seccion entre {start_year} y {end_year}.",
            warnings=[] if rows else ["No population rows were found for both requested years."],
        )

    def get_electoral_change_ranking(
        self,
        municipality_id: str,
        *,
        start_year: int,
        end_year: int,
        limit: int = 10,
    ) -> AnalystToolResult:
        data_used = ["marts.mv_electoral_behavior", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH electoral AS (
                    SELECT
                        seccion_id,
                        anio,
                        ROUND(100 * votos_emitidos::numeric / NULLIF(censo, 0), 2) AS turnout_pct,
                        ROUND(100 * (censo - votos_emitidos)::numeric / NULLIF(censo, 0), 2) AS abstention_rate_pct,
                        COALESCE(winning_party_family, winning_party) AS winning_party,
                        ROUND(winning_party_pct::numeric, 2) AS winning_party_pct
                    FROM marts.mv_electoral_behavior
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND anio IN (:start_year, :end_year)
                      AND tipo_eleccion_code = 'MUNICIPALES'
                ),
                pivoted AS (
                    SELECT
                        seccion_id,
                        MAX(turnout_pct) FILTER (WHERE anio = :start_year) AS turnout_start,
                        MAX(turnout_pct) FILTER (WHERE anio = :end_year) AS turnout_end,
                        MAX(abstention_rate_pct) FILTER (WHERE anio = :start_year) AS abstention_start,
                        MAX(abstention_rate_pct) FILTER (WHERE anio = :end_year) AS abstention_end,
                        MAX(winning_party) FILTER (WHERE anio = :start_year) AS winning_party_start,
                        MAX(winning_party) FILTER (WHERE anio = :end_year) AS winning_party_end,
                        MAX(winning_party_pct) FILTER (WHERE anio = :start_year) AS winning_party_pct_start,
                        MAX(winning_party_pct) FILTER (WHERE anio = :end_year) AS winning_party_pct_end
                    FROM electoral
                    GROUP BY seccion_id
                )
                SELECT
                    p.seccion_id AS section_id,
                    COALESCE(d.label_cliente, p.seccion_id) AS section_name,
                    p.turnout_start,
                    p.turnout_end,
                    p.turnout_end - p.turnout_start AS turnout_change_pct,
                    p.abstention_start,
                    p.abstention_end,
                    p.abstention_end - p.abstention_start AS abstention_change_pct,
                    p.winning_party_start,
                    p.winning_party_end,
                    p.winning_party_pct_start,
                    p.winning_party_pct_end,
                    p.winning_party_pct_end - p.winning_party_pct_start AS winning_party_change_pct
                FROM pivoted p
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = p.seccion_id
                WHERE p.turnout_start IS NOT NULL
                  AND p.turnout_end IS NOT NULL
                ORDER BY ABS(p.turnout_end - p.turnout_start) DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "start_year": start_year,
                "end_year": end_year,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="get_electoral_change_ranking",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=f"Comparacion electoral municipal por seccion entre {start_year} y {end_year}, ordenada por cambio absoluto de participacion.",
            warnings=[] if rows else ["No electoral rows were found for both requested years."],
        )

    def get_income_change_ranking(
        self,
        municipality_id: str,
        *,
        start_year: int,
        end_year: int,
        limit: int = 10,
    ) -> AnalystToolResult:
        data_used = ["marts.v_income_level_layer", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH income AS (
                    SELECT
                        seccion_id,
                        anio,
                        renta_media_persona,
                        renta_media_hogar
                    FROM marts.v_income_level_layer
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND anio IN (:start_year, :end_year)
                ),
                pivoted AS (
                    SELECT
                        seccion_id,
                        MAX(renta_media_persona) FILTER (WHERE anio = :start_year) AS individual_income_start,
                        MAX(renta_media_persona) FILTER (WHERE anio = :end_year) AS individual_income_end,
                        MAX(renta_media_hogar) FILTER (WHERE anio = :start_year) AS household_income_start,
                        MAX(renta_media_hogar) FILTER (WHERE anio = :end_year) AS household_income_end
                    FROM income
                    GROUP BY seccion_id
                )
                SELECT
                    p.seccion_id AS section_id,
                    COALESCE(d.label_cliente, p.seccion_id) AS section_name,
                    p.individual_income_start,
                    p.individual_income_end,
                    p.individual_income_end - p.individual_income_start AS individual_income_change,
                    ROUND(
                        100 * (p.individual_income_end - p.individual_income_start)::numeric
                        / NULLIF(p.individual_income_start, 0),
                        2
                    ) AS individual_income_change_pct,
                    p.household_income_start,
                    p.household_income_end,
                    p.household_income_end - p.household_income_start AS household_income_change
                FROM pivoted p
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = p.seccion_id
                WHERE p.individual_income_start IS NOT NULL
                  AND p.individual_income_end IS NOT NULL
                ORDER BY ABS(p.individual_income_end - p.individual_income_start) DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "start_year": start_year,
                "end_year": end_year,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="get_income_change_ranking",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=f"Comparacion de renta media por persona entre {start_year} y {end_year}.",
            warnings=[] if rows else ["No income rows were found for both requested years."],
        )

    def get_population_density(
        self,
        municipality_id: str,
        year: int = 2023,
        section_id: str | None = None,
        limit: int = 10,
    ) -> AnalystToolResult:
        result = self.get_population_ranking(municipality_id, year=year, limit=limit)
        rows = result.rows
        if section_id:
            rows = [row for row in rows if row.get("section_id") == section_id]
        return AnalystToolResult(
            name="get_population_density",
            rows=rows,
            data_used=result.data_used,
            methodology="Densidad y poblacion por seccion desde la capa de poblacion aprobada.",
            warnings=result.warnings,
        )

    def get_election_results(
        self,
        municipality_id: str,
        *,
        party: str | None = None,
        year: int = 2023,
        election_type: str | None = "MUNICIPALES",
        limit: int = 10,
    ) -> AnalystToolResult:
        data_used = ["marts.mv_electoral_behavior", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        party_filter = "AND party_result->>'normalized_party_family' = :party" if party else ""
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    eb.seccion_id AS section_id,
                    COALESCE(d.label_cliente, eb.seccion_id) AS section_name,
                    party_result->>'normalized_party_family' AS party,
                    ROUND(((party_result->>'pct')::numeric * 100), 2) AS vote_pct,
                    (party_result->>'votes')::int AS votes,
                    COALESCE(eb.winning_party_family, eb.winning_party) AS winning_party,
                    ROUND(eb.winning_party_pct::numeric, 2) AS winning_party_pct,
                    ROUND(100 * (eb.censo - eb.votos_emitidos)::numeric / NULLIF(eb.censo, 0), 2) AS abstention_rate_pct
                FROM marts.mv_electoral_behavior eb
                CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = eb.seccion_id
                WHERE LEFT(eb.seccion_id, 5) = :municipality_id
                  AND eb.anio = :year
                  AND eb.tipo_eleccion_code = :election_type
                  {party_filter}
                ORDER BY vote_pct DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "year": year,
                "election_type": _election_type(election_type),
                "party": party,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="get_election_results",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Resultados electorales observados por seccion desde la vista electoral aprobada.",
            warnings=[],
        )

    def get_turnout_analysis(self, municipality_id: str, year: int = 2023, limit: int = 10) -> AnalystToolResult:
        data_used = ["marts.mv_electoral_behavior", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                SELECT
                    eb.seccion_id AS section_id,
                    COALESCE(d.label_cliente, eb.seccion_id) AS section_name,
                    eb.censo AS census,
                    eb.votos_emitidos AS votes_cast,
                    ROUND(100 * eb.votos_emitidos::numeric / NULLIF(eb.censo, 0), 2) AS turnout_pct,
                    ROUND(100 * (eb.censo - eb.votos_emitidos)::numeric / NULLIF(eb.censo, 0), 2) AS abstention_rate_pct,
                    (eb.censo - eb.votos_emitidos)::int AS abstainers
                FROM marts.mv_electoral_behavior eb
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = eb.seccion_id
                WHERE LEFT(eb.seccion_id, 5) = :municipality_id
                  AND eb.anio = :year
                  AND eb.tipo_eleccion_code = 'MUNICIPALES'
                ORDER BY abstention_rate_pct DESC NULLS LAST, abstainers DESC, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year, "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="get_turnout_analysis",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Abstencion calculada como censo menos votos emitidos dividido por censo.",
            warnings=[],
        )

    def get_income_profile(self, municipality_id: str, year: int = 2023, limit: int = 10) -> AnalystToolResult:
        data_used = ["marts.v_income_level_layer", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                SELECT
                    income.seccion_id AS section_id,
                    COALESCE(d.label_cliente, income.seccion_id) AS section_name,
                    income.renta_media_persona AS individual_income,
                    income.renta_media_hogar AS household_income,
                    income.income_quintile
                FROM marts.v_income_level_layer income
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = income.seccion_id
                WHERE LEFT(income.seccion_id, 5) = :municipality_id
                  AND income.anio = :year
                ORDER BY individual_income DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year, "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="get_income_profile",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Ranking de renta por seccion desde la capa de renta aprobada.",
            warnings=[],
        )

    def get_socioeconomic_profile(
        self,
        municipality_id: str,
        year: int = 2023,
        section_id: str | None = None,
        limit: int = 10,
    ) -> AnalystToolResult:
        result = self.get_income_profile(municipality_id, year=year, limit=limit)
        rows = result.rows
        if section_id:
            rows = [row for row in rows if row.get("section_id") == section_id]
        return AnalystToolResult(
            name="get_socioeconomic_profile",
            rows=rows,
            data_used=result.data_used,
            methodology="Perfil socioeconomico proxy usando renta seccional disponible.",
            warnings=["Indicadores educativos o de origen no estan disponibles en esta herramienta; se usan proxies socioeconomicos."] + result.warnings,
        )

    def get_socioeconomic_intelligence_profile(
        self,
        municipality_id: str,
        year: int = 2023,
        section_id: str | None = None,
        limit: int = 10,
    ) -> AnalystToolResult:
        data_used = ["marts.socioeconomic_intelligence_signals", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        section_filter = "AND sis.seccion_id = :section_id" if section_id else ""
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    sis.seccion_id AS section_id,
                    COALESCE(d.label_cliente, sis.seccion_id) AS section_name,
                    sis.anio AS year,
                    sis.pct_employed,
                    sis.pct_unemployed,
                    sis.pct_self_employed,
                    sis.pct_employee,
                    sis.pct_services,
                    sis.pct_construction,
                    sis.pct_industry,
                    sis.pct_qualified_occupations,
                    sis.income_unemployment_benefits,
                    sis.education_high_norm,
                    sis.low_education_norm,
                    sis.qualified_occupation_norm,
                    sis.employment_norm,
                    sis.unemployment_norm,
                    sis.unemployment_benefits_norm,
                    sis.business_activity_norm,
                    sis.self_employment_norm,
                    sis.human_capital_index,
                    sis.vulnerability_index,
                    sis.resilience_index,
                    sis.productive_complexity_index,
                    sis.productive_complexity_completeness_pct,
                    sis.productive_complexity_label
                FROM marts.socioeconomic_intelligence_signals sis
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = sis.seccion_id
                WHERE LEFT(sis.seccion_id, 5) = :municipality_id
                  AND sis.anio = :year
                  {section_filter}
                ORDER BY
                    sis.productive_complexity_index DESC NULLS LAST,
                    sis.vulnerability_index DESC NULLS LAST,
                    section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "year": year,
                "section_id": section_id,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="get_socioeconomic_intelligence_profile",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Perfil de Inteligencia Socioeconomica por seccion desde la vista aprobada de señales socioeconomicas.",
            warnings=[],
        )

    def rank_sections_for_labor_training_outreach(
        self,
        municipality_id: str,
        year: int = 2023,
        limit: int = 10,
    ) -> AnalystToolResult:
        data_used = [
            "marts.socioeconomic_intelligence_signals",
            "marts.v_population_layer",
            "marts.v_mapa_age_structure_2023",
            "marts.v_income_level_layer",
            "marts.dim_seccion_display",
        ]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                SELECT
                    sis.seccion_id AS section_id,
                    COALESCE(d.label_cliente, sis.seccion_id) AS section_name,
                    pop.pob_total AS population_total,
                    pop.densidad AS population_density,
                    age.under_30_pct,
                    age.over_65_pct,
                    income.renta_media_persona AS individual_income,
                    sis.pct_employed,
                    sis.pct_unemployed,
                    sis.pct_qualified_occupations,
                    sis.employment_norm,
                    sis.unemployment_norm,
                    sis.qualified_occupation_norm,
                    sis.education_high_norm,
                    sis.low_education_norm,
                    sis.vulnerability_index,
                    sis.human_capital_index,
                    sis.resilience_index,
                    sis.productive_complexity_index,
                    sis.productive_complexity_label,
                    ROUND(
                        (
                            COALESCE(sis.productive_complexity_index, 50) * 0.24
                          + COALESCE(sis.vulnerability_index, 50) * 0.22
                          + COALESCE(sis.employment_norm, 50) * 0.16
                          + COALESCE(sis.unemployment_norm, 50) * 0.16
                          + COALESCE(sis.low_education_norm, 50) * 0.12
                          + LEAST(COALESCE(pop.pob_total, 0)::numeric / 25, 100) * 0.10
                        )::numeric,
                        2
                    ) AS labor_training_score
                FROM marts.socioeconomic_intelligence_signals sis
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = sis.seccion_id
                LEFT JOIN marts.v_population_layer pop
                  ON pop.seccion_id = sis.seccion_id
                 AND pop.anio = :year
                LEFT JOIN marts.v_mapa_age_structure_2023 age
                  ON age.seccion_id = sis.seccion_id
                LEFT JOIN marts.v_income_level_layer income
                  ON income.seccion_id = sis.seccion_id
                 AND income.anio = :year
                WHERE LEFT(sis.seccion_id, 5) = :municipality_id
                  AND sis.anio = :year
                ORDER BY labor_training_score DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year, "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="rank_sections_for_labor_training_outreach",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=(
                "Ranking para formacion laboral: combina complejidad productiva, vulnerabilidad, empleo/desempleo, "
                "nivel educativo proxy, poblacion y densidad. No inventa variables ausentes."
            ),
            warnings=[],
        )

    def get_age_structure(self, municipality_id: str, limit: int = 10, youngest: bool = True) -> AnalystToolResult:
        data_used = ["marts.v_mapa_age_structure_2023", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        direction = "ASC" if youngest else "DESC"
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    age.seccion_id AS section_id,
                    COALESCE(d.label_cliente, age.seccion_id) AS section_name,
                    age.average_age,
                    age.under_30_pct,
                    age.over_65_pct
                FROM marts.v_mapa_age_structure_2023 age
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = age.seccion_id
                WHERE LEFT(age.seccion_id, 5) = :municipality_id
                  AND age.average_age IS NOT NULL
                ORDER BY age.average_age {direction}, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="get_age_structure",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Estructura de edad 2023 ordenada por edad media seccional.",
            warnings=[],
        )

    def get_family_youth_profile(
        self,
        municipality_id: str,
        year: int = 2023,
        section_id: str | None = None,
        limit: int = 10,
    ) -> AnalystToolResult:
        result = self.get_age_structure(municipality_id, limit=limit, youngest=True)
        rows = result.rows
        if section_id:
            rows = [row for row in rows if row.get("section_id") == section_id]
        return AnalystToolResult(
            name="get_family_youth_profile",
            rows=rows,
            data_used=result.data_used,
            methodology="Proxy de familias/jovenes usando estructura de edad disponible.",
            warnings=["No hay campo familiar directo en esta herramienta; se usa porcentaje joven y edad media como proxy."] + result.warnings,
        )

    def get_foreign_population_profile(
        self,
        municipality_id: str,
        year: int = 2023,
        section_id: str | None = None,
        limit: int = 10,
    ) -> AnalystToolResult:
        return AnalystToolResult(
            name="get_foreign_population_profile",
            rows=[],
            data_used=[],
            methodology="No hay fuente de poblacion extranjera expuesta en las herramientas aprobadas actuales.",
            warnings=["Poblacion extranjera/origen no disponible; no se infiere este indicador."],
        )

    def get_land_built_profile(self, municipality_id: str, year: int = 2023, limit: int = 10) -> AnalystToolResult:
        data_used = ["marts.v_land_built_environment", "marts.dim_seccion_display"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                SELECT
                    land.seccion_id AS section_id,
                    COALESCE(d.label_cliente, land.seccion_id) AS section_name,
                    land.urban_intensity_index,
                    land.densidad_parcelaria AS parcel_density,
                    land.indice_construido AS built_index
                FROM marts.v_land_built_environment land
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = land.seccion_id
                WHERE LEFT(land.seccion_id, 5) = :municipality_id
                  AND land.anio = :year
                ORDER BY urban_intensity_index DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year, "limit": limit},
        ).mappings().all()
        return AnalystToolResult(
            name="get_land_built_profile",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Perfil urbano construido desde la capa catastral y territorial aprobada.",
            warnings=[],
        )

    def compare_sections(self, section_ids: list[str], year: int = 2023) -> AnalystToolResult:
        data_used = [
            "marts.dim_seccion_display",
            "marts.v_population_layer",
            "marts.v_mapa_age_structure_2023",
            "marts.v_income_level_layer",
            "marts.mv_electoral_behavior",
        ]
        self.datasets.require(*data_used)
        query = text(
            """
            SELECT
                display.seccion_id AS section_id,
                COALESCE(display.label_cliente, display.seccion_id) AS section_name,
                pop.pob_total AS population_total,
                age.average_age,
                age.under_30_pct,
                age.over_65_pct,
                income.renta_media_persona AS individual_income,
                COALESCE(eb.winning_party_family, eb.winning_party) AS winning_party,
                ROUND(eb.winning_party_pct::numeric, 2) AS winning_party_pct,
                ROUND(100 * (eb.censo - eb.votos_emitidos)::numeric / NULLIF(eb.censo, 0), 2) AS abstention_rate_pct
            FROM marts.dim_seccion_display display
            LEFT JOIN marts.v_population_layer pop
              ON pop.seccion_id = display.seccion_id
             AND pop.anio = :year
            LEFT JOIN marts.v_mapa_age_structure_2023 age
              ON age.seccion_id = display.seccion_id
            LEFT JOIN marts.v_income_level_layer income
              ON income.seccion_id = display.seccion_id
             AND income.anio = :year
            LEFT JOIN marts.mv_electoral_behavior eb
              ON eb.seccion_id = display.seccion_id
             AND eb.anio = :year
             AND eb.tipo_eleccion_code = 'MUNICIPALES'
            WHERE display.seccion_id IN :section_ids
            ORDER BY section_name
            """
        ).bindparams(bindparam("section_ids", expanding=True))
        rows = self.session.execute(query, {"section_ids": section_ids, "year": year}).mappings().all()
        return AnalystToolResult(
            name="compare_sections",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology="Comparacion parametrizada de secciones sobre indicadores demograficos, renta y voto observado.",
            warnings=[],
        )

    def calculate_dhondt(self, municipality_id: str, year: int = 2023, seats: int = 25) -> AnalystToolResult:
        data_used = ["core.resultados_seccion", "core.candidatura_alias"]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                SELECT
                    COALESCE(a.normalized_party_family, r.siglas, r.denominacion) AS party,
                    SUM(r.votos_partido)::bigint AS votes
                FROM core.resultados_seccion r
                LEFT JOIN core.candidatura_alias a
                  ON a.election_id = r.election_id
                 AND a.cod_candidatura = r.cod_candidatura
                WHERE LEFT(r.seccion_id, 5) = :municipality_id
                  AND r.tipo_eleccion_code = 'MUNICIPALES'
                  AND r.anio = :year
                GROUP BY COALESCE(a.normalized_party_family, r.siglas, r.denominacion)
                ORDER BY votes DESC, party
                """
            ),
            {"municipality_id": _municipality_id(municipality_id), "year": year},
        ).mappings().all()
        parties = [dict(row) for row in rows]
        result = self.dhondt.calculate(parties, total_seats=seats)
        output_rows = [
            {"party": item.party, "divisor": item.divisor, "quotient": round(item.value, 2)}
            for item in result["winners"]
        ]
        return AnalystToolResult(
            name="calculate_dhondt",
            rows=output_rows,
            data_used=data_used,
            methodology=f"Metodo D'Hondt determinista con {seats} concejales y umbral del 5%.",
            warnings=[],
        )

    def rank_sections_by_opportunity(
        self,
        municipality_id: str,
        *,
        target_party: str = "PP",
        year: int = 2023,
        limit: int = 8,
    ) -> AnalystToolResult:
        data_used = [
            "marts.mv_electoral_behavior",
            "marts.dim_seccion_display",
            "marts.v_population_layer",
            "marts.v_mapa_age_structure_2023",
            "marts.v_income_level_layer",
        ]
        self.datasets.require(*data_used)
        rows = self.session.execute(
            text(
                """
                WITH electoral AS (
                    SELECT
                        eb.seccion_id,
                        COALESCE(d.label_cliente, eb.seccion_id) AS section_name,
                        eb.censo,
                        eb.votos_emitidos,
                        COALESCE(eb.winning_party_family, eb.winning_party) AS winning_party,
                        eb.winning_party_pct,
                        eb.runner_up_pct,
                        eb.victory_margin_pct,
                        MAX(((party_result->>'pct')::numeric * 100)) FILTER (
                            WHERE party_result->>'normalized_party_family' = :target_party
                        ) AS target_party_vote_pct,
                        MAX(((party_result->>'pct')::numeric * 100)) AS max_party_pct
                    FROM marts.mv_electoral_behavior eb
                    CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
                    LEFT JOIN marts.dim_seccion_display d
                      ON d.seccion_id = eb.seccion_id
                    WHERE LEFT(eb.seccion_id, 5) = :municipality_id
                      AND eb.anio = :year
                      AND eb.tipo_eleccion_code = 'MUNICIPALES'
                    GROUP BY eb.seccion_id, d.label_cliente, eb.censo, eb.votos_emitidos, eb.winning_party_family, eb.winning_party, eb.winning_party_pct, eb.runner_up_pct, eb.victory_margin_pct
                ),
                enriched AS (
                    SELECT
                        electoral.*,
                        pop.pob_total AS population_total,
                        age.under_30_pct,
                        age.over_65_pct,
                        income.renta_media_persona AS individual_income,
                        ROUND(100 * (electoral.censo - electoral.votos_emitidos)::numeric / NULLIF(electoral.censo, 0), 2) AS abstention_rate_pct,
                        ROUND(ABS(COALESCE(electoral.winning_party_pct, 0) - COALESCE(electoral.target_party_vote_pct, 0))::numeric, 2) AS distance_to_winner_pct
                    FROM electoral
                    LEFT JOIN marts.v_population_layer pop
                      ON pop.seccion_id = electoral.seccion_id
                     AND pop.anio = :year
                    LEFT JOIN marts.v_mapa_age_structure_2023 age
                      ON age.seccion_id = electoral.seccion_id
                    LEFT JOIN marts.v_income_level_layer income
                      ON income.seccion_id = electoral.seccion_id
                     AND income.anio = :year
                )
                SELECT
                    seccion_id AS section_id,
                    section_name,
                    population_total,
                    winning_party,
                    ROUND(winning_party_pct::numeric, 2) AS winning_party_pct,
                    ROUND(runner_up_pct::numeric, 2) AS runner_up_pct,
                    ROUND(victory_margin_pct::numeric, 2) AS victory_margin_pct,
                    ROUND(target_party_vote_pct::numeric, 2) AS target_party_vote_pct,
                    distance_to_winner_pct,
                    abstention_rate_pct,
                    under_30_pct,
                    over_65_pct,
                    individual_income,
                    ROUND(
                        (
                            LEAST(COALESCE(abstention_rate_pct, 0), 50) * 0.9
                            + GREATEST(35 - COALESCE(distance_to_winner_pct, 35), 0) * 1.1
                            + LEAST(COALESCE(population_total, 0)::numeric / 100, 20)
                        ),
                        2
                    ) AS opportunity_score
                FROM enriched
                WHERE target_party_vote_pct IS NOT NULL
                ORDER BY opportunity_score DESC NULLS LAST, section_name
                LIMIT :limit
                """
            ),
            {
                "municipality_id": _municipality_id(municipality_id),
                "target_party": target_party.upper(),
                "year": year,
                "limit": limit,
            },
        ).mappings().all()
        return AnalystToolResult(
            name="rank_sections_by_opportunity",
            rows=[dict(row) for row in rows],
            data_used=data_used,
            methodology=(
                "Ranking determinista de oportunidad: abstencion, distancia al ganador y tamano seccional. "
                "No es forecast ni encuesta."
            ),
            warnings=[],
        )

    def build_campaign_recommendation(self, municipality_id: str, target_party: str = "PP", year: int = 2023) -> AnalystToolResult:
        opportunity = self.rank_sections_by_opportunity(municipality_id, target_party=target_party, year=year, limit=8)
        turnout = self.get_turnout_analysis(municipality_id, year=year, limit=8)
        population = self.get_population_trend(municipality_id, year=year, limit=8)
        age = self.get_age_structure(municipality_id, limit=8, youngest=True)
        income = self.get_income_profile(municipality_id, year=year, limit=8)
        by_section: dict[str, dict[str, Any]] = {}
        for result in [opportunity, turnout, population, age, income]:
            for source in result.rows:
                section_id = str(source.get("section_id") or "")
                if not section_id:
                    continue
                row = by_section.setdefault(
                    section_id,
                    {
                        "section_id": section_id,
                        "section_name": source.get("section_name") or section_id,
                        "population_total": None,
                        "winning_party": None,
                        "winning_party_pct": None,
                        "runner_up_pct": None,
                        "victory_margin_pct": None,
                        "target_party_vote_pct": None,
                        "abstention_rate_pct": None,
                        "population_growth_pct": None,
                        "avg_age": None,
                        "income": None,
                        "opportunity_score": None,
                        "strategic_label": None,
                        "reason": None,
                    },
                )
                row["section_name"] = source.get("section_name") or row["section_name"]
                for key in [
                    "population_total",
                    "winning_party",
                    "winning_party_pct",
                    "runner_up_pct",
                    "victory_margin_pct",
                    "target_party_vote_pct",
                    "abstention_rate_pct",
                    "population_growth_pct",
                    "opportunity_score",
                ]:
                    if source.get(key) is not None:
                        row[key] = source.get(key)
                if source.get("average_age") is not None:
                    row["avg_age"] = source.get("average_age")
                if source.get("individual_income") is not None:
                    row["income"] = source.get("individual_income")

        rows = list(by_section.values())
        for row in rows:
            abstention = _number(row.get("abstention_rate_pct")) or 0
            margin = _number(row.get("victory_margin_pct")) or 99
            if abstention >= 45:
                row["strategic_label"] = "movilizacion"
            elif margin <= 7:
                row["strategic_label"] = "persuasion"
            elif row.get("winning_party") == target_party.upper():
                row["strategic_label"] = "retencion"
            else:
                row["strategic_label"] = "expansion"
            row["reason"] = (
                "Recomendacion basada en fuerza electoral, abstencion, margen de victoria, "
                "tamano poblacional, edad, renta y dinamica demografica disponibles."
            )
        rows.sort(
            key=lambda row: (
                _number(row.get("opportunity_score")) or 0,
                _number(row.get("abstention_rate_pct")) or 0,
                _number(row.get("population_total")) or 0,
            ),
            reverse=True,
        )
        data_used = sorted({source for result in [opportunity, turnout, population, age, income] for source in result.data_used})
        warnings = [warning for result in [opportunity, turnout, population, age, income] for warning in result.warnings]
        return AnalystToolResult(
            name="build_campaign_recommendation",
            rows=rows[:10],
            data_used=data_used,
            methodology=(
                "Recomendacion estructurada de campana que agrega fuerza electoral, abstencion, margen de victoria, "
                "poblacion, estructura demografica, renta, dinamica de crecimiento y etiquetas seccionales. "
                "No es forecast ni encuesta; traduce datos observados en prioridades operativas."
            ),
            warnings=warnings,
        )


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
