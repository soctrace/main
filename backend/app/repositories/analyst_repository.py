from dataclasses import dataclass
import json

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


@dataclass(slots=True)
class AnalystRepository:
    session: Session

    NORMALIZED_RESULTS_SQL = """
        WITH normalized_rows AS (
            SELECT
                r.election_id,
                e.tipo_eleccion_code,
                COALESCE(e.tipo_eleccion_nombre, et.descripcion, e.tipo_eleccion_code) AS election_type,
                e.anio AS election_year,
                e.mes AS election_month,
                e.election_date,
                r.seccion_id AS section_id,
                COALESCE(d.label_cliente, r.seccion_id) AS section_name,
                CASE
                    WHEN UPPER(COALESCE(a.normalized_party_family, r.siglas, r.denominacion, '')) IN ('PP', 'PARTIDO POPULAR')
                      OR UPPER(COALESCE(r.siglas, r.denominacion, '')) LIKE '%PARTIDO POPULAR%'
                        THEN 'PP'
                    WHEN UPPER(COALESCE(a.normalized_party_family, r.siglas, r.denominacion, '')) IN ('PSOE', 'PSOE-A')
                      OR UPPER(COALESCE(r.siglas, r.denominacion, '')) LIKE '%PARTIDO SOCIALISTA%'
                        THEN 'PSOE'
                    WHEN UPPER(COALESCE(a.normalized_party_family, r.siglas, r.denominacion, '')) = 'VOX'
                        THEN 'VOX'
                    WHEN UPPER(COALESCE(a.normalized_party_family, r.siglas, r.denominacion, '')) IN ('CS', 'CIUDADANOS')
                      OR UPPER(COALESCE(r.siglas, r.denominacion, '')) LIKE '%CIUDADANOS%'
                        THEN 'CS'
                    WHEN UPPER(COALESCE(r.siglas, r.denominacion, '')) LIKE '%POR MI PUEBLO%'
                        THEN 'POR MI PUEBLO'
                    WHEN COALESCE(a.normalized_party_family, '') <> ''
                        THEN UPPER(a.normalized_party_family)
                    WHEN COALESCE(r.siglas, '') <> ''
                        THEN UPPER(r.siglas)
                    ELSE UPPER(COALESCE(r.denominacion, 'OTHER'))
                END AS canonical_party,
                COALESCE(r.votos_partido, 0)::numeric AS votes,
                COALESCE(r.votos_validos, 0)::numeric AS valid_votes
            FROM core.resultados_seccion r
            JOIN core.election e
              ON e.election_id = r.election_id
            LEFT JOIN core.election_type et
              ON et.tipo_eleccion_code = e.tipo_eleccion_code
            LEFT JOIN core.candidatura_alias a
              ON a.election_id = r.election_id
             AND a.cod_candidatura = r.cod_candidatura
            LEFT JOIN marts.dim_seccion_display d
              ON d.seccion_id = r.seccion_id
            WHERE LEFT(r.seccion_id, 5) = :municipality_id
        ),
        per_party AS (
            SELECT
                election_id,
                tipo_eleccion_code,
                election_type,
                election_year,
                election_month,
                election_date,
                section_id,
                section_name,
                canonical_party,
                SUM(votes)::bigint AS votes,
                MAX(valid_votes)::bigint AS valid_votes,
                ROUND(100 * SUM(votes) / NULLIF(MAX(valid_votes), 0), 4) AS vote_pct
            FROM normalized_rows
            GROUP BY
                election_id,
                tipo_eleccion_code,
                election_type,
                election_year,
                election_month,
                election_date,
                section_id,
                section_name,
                canonical_party
        )
        SELECT *
        FROM per_party
        WHERE valid_votes > 0
    """

    def get_normalized_election_results(
        self,
        municipality_id: str,
        party: str | None = None,
        section_id: str | None = None,
        election_type: str | None = None,
        year: int | None = None,
    ) -> list[dict]:
        filters = []
        params: dict[str, str | int] = {"municipality_id": municipality_id}
        if party is not None:
            filters.append("canonical_party = :party")
            params["party"] = party
        if section_id is not None:
            filters.append("section_id = :section_id")
            params["section_id"] = section_id
        if election_type is not None:
            filters.append("tipo_eleccion_code = :election_type")
            params["election_type"] = election_type
        if year is not None:
            filters.append("election_year = :year")
            params["year"] = year
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = text(
            f"""
            SELECT
                section_id,
                section_name,
                tipo_eleccion_code AS election_type_code,
                election_type,
                election_year,
                election_month,
                election_id,
                canonical_party AS party,
                votes,
                valid_votes,
                vote_pct
            FROM ({self.NORMALIZED_RESULTS_SQL}) normalized
            {where_clause}
            ORDER BY election_year, election_month, election_id, section_id, vote_pct DESC, party
            """
        )
        rows = self.session.execute(query, params).mappings().all()
        return [dict(row) for row in rows]

    def get_section_lookup(self, municipality_id: str) -> list[dict]:
        rows = self.session.execute(
            text(
                """
                SELECT
                    seccion_id AS section_id,
                    COALESCE(seccion_numero_visible, LPAD((RIGHT(seccion_id, 3)::int)::text, 2, '0')) AS section_number,
                    COALESCE(label_cliente, nombre_barrio, seccion_id) AS display_name,
                    nombre_barrio,
                    zona_macro
                FROM marts.dim_seccion_display
                WHERE LEFT(seccion_id, 5) = :municipality_id
                ORDER BY seccion_id
                """
            ),
            {"municipality_id": municipality_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_youngest_section(self, municipality_id: str) -> dict | None:
        row = self.session.execute(
            text(
                """
                SELECT
                    age.seccion_id AS section_id,
                    COALESCE(display.seccion_numero_visible, LPAD((RIGHT(age.seccion_id, 3)::int)::text, 2, '0')) AS section_number,
                    COALESCE(age.label_cliente, display.label_cliente, age.seccion_id) AS display_name,
                    display.nombre_barrio,
                    display.zona_macro,
                    age.average_age
                FROM marts.v_mapa_age_structure_2023 age
                LEFT JOIN marts.dim_seccion_display display
                  ON display.seccion_id = age.seccion_id
                WHERE LEFT(age.seccion_id, 5) = :municipality_id
                  AND age.average_age IS NOT NULL
                ORDER BY age.average_age ASC, display_name
                LIMIT 1
                """
            ),
            {"municipality_id": municipality_id},
        ).mappings().first()
        return dict(row) if row else None

    def get_historical_party_average(self, municipality_id: str, party: str, limit: int = 10) -> list[dict]:
        rows = self.session.execute(
            text(
                f"""
                WITH party_results AS (
                    SELECT *
                    FROM ({self.NORMALIZED_RESULTS_SQL}) normalized
                    WHERE canonical_party = :party
                ),
                ranked AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (PARTITION BY section_id ORDER BY election_date NULLS LAST, election_id) AS temporal_index
                    FROM party_results
                ),
                section_stats AS (
                    SELECT
                        section_id,
                        MAX(section_name) AS section_name,
                        COUNT(*)::int AS number_of_elections_available,
                        ROUND(AVG(vote_pct), 2) AS average_vote_pct,
                        ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY vote_pct)::numeric, 2) AS median_vote_pct,
                        ROUND(MIN(vote_pct), 2) AS min_vote_pct,
                        ROUND(MAX(vote_pct), 2) AS max_vote_pct,
                        ROUND((ARRAY_AGG(vote_pct ORDER BY election_date DESC NULLS LAST, election_id DESC))[1], 2) AS latest_vote_pct,
                        ROUND(
                            CASE
                                WHEN COUNT(*) >= 2
                                THEN (
                                    (ARRAY_AGG(vote_pct ORDER BY election_date DESC NULLS LAST, election_id DESC))[1]
                                    - (ARRAY_AGG(vote_pct ORDER BY election_date ASC NULLS LAST, election_id ASC))[1]
                                )
                                ELSE NULL
                            END,
                            2
                        ) AS trend_pp,
                        JSONB_AGG(
                            JSONB_BUILD_OBJECT(
                                'election_id', election_id,
                                'election_type', election_type,
                                'year', election_year,
                                'month', election_month,
                                'vote_pct', ROUND(vote_pct, 2)
                            )
                            ORDER BY election_date NULLS LAST, election_id
                        ) AS elections
                    FROM ranked
                    GROUP BY section_id
                    HAVING COUNT(*) >= 2
                )
                SELECT *
                FROM section_stats
                ORDER BY average_vote_pct DESC, number_of_elections_available DESC, section_name
                LIMIT :limit
                """
            ),
            {"municipality_id": municipality_id, "party": party, "limit": limit},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_available_elections(self, municipality_id: str) -> list[dict]:
        rows = self.session.execute(
            text(
                f"""
                SELECT
                    election_id,
                    tipo_eleccion_code AS election_type_code,
                    election_type,
                    election_year,
                    election_month,
                    COUNT(DISTINCT section_id)::int AS section_count
                FROM ({self.NORMALIZED_RESULTS_SQL}) normalized
                GROUP BY election_id, tipo_eleccion_code, election_type, election_year, election_month
                ORDER BY election_year, election_month, election_id
                """
            ),
            {"municipality_id": municipality_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_demographics_age_range(
        self,
        municipality_id: str,
        year: int,
        min_age: int,
        max_age: int,
        gender: str = "all",
        group_by: str = "municipality",
    ) -> dict:
        gender_filter = "" if gender == "all" else "AND genero = :gender"
        group_expression = {
            "municipality": "LEFT(weighted.seccion_id, 5)",
            "section": "weighted.seccion_id",
            "gender": "weighted.genero",
        }.get(group_by, "LEFT(normalized.seccion_id, 5)")
        label_expression = {
            "municipality": "LEFT(weighted.seccion_id, 5)",
            "section": "COALESCE(MAX(d.label_cliente), weighted.seccion_id)",
            "gender": "weighted.genero",
        }.get(group_by, "LEFT(weighted.seccion_id, 5)")

        rows = self.session.execute(
            text(
                f"""
                WITH normalized AS (
                    SELECT
                        CASE
                            WHEN anio = 2021 AND seccion_id = '2907001006' THEN '2907001021'
                            WHEN anio = 2021 AND seccion_id = '2907001021' THEN '2907001006'
                            ELSE seccion_id
                        END AS seccion_id,
                        anio,
                        genero,
                        poblacion,
                        lower(trim(edad_cohorte)) AS edad_cohorte_norm
                    FROM core.poblacion_edad
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND anio = :year
                      AND edad_cohorte <> 'TOTAL'
                      {gender_filter}
                ),
                cohortes AS (
                    SELECT
                        *,
                        CASE
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*-\\s*[0-9]+$'
                            THEN split_part(regexp_replace(edad_cohorte_norm, '\\s+', '', 'g'), '-', 1)::int
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*(\\+|y\\s*m[aá]s)$'
                            THEN substring(edad_cohorte_norm FROM '^[0-9]+')::int
                            ELSE NULL
                        END AS cohort_min_age,
                        CASE
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*-\\s*[0-9]+$'
                            THEN split_part(regexp_replace(edad_cohorte_norm, '\\s+', '', 'g'), '-', 2)::int
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*(\\+|y\\s*m[aá]s)$'
                            THEN 120
                            ELSE NULL
                        END AS cohort_max_age
                    FROM normalized
                ),
                weighted AS (
                    SELECT
                        *,
                        GREATEST(cohort_min_age, :min_age) AS overlap_min,
                        LEAST(cohort_max_age, :max_age) AS overlap_max
                    FROM cohortes
                    WHERE cohort_min_age IS NOT NULL
                      AND cohort_max_age IS NOT NULL
                      AND cohort_max_age >= :min_age
                      AND cohort_min_age <= :max_age
                )
                SELECT
                    {label_expression} AS label,
                    ROUND(
                        SUM(
                            poblacion::numeric
                            * GREATEST(overlap_max - overlap_min + 1, 0)
                            / NULLIF(cohort_max_age - cohort_min_age + 1, 0)
                        )
                    )::bigint AS total,
                    BOOL_OR(overlap_min > cohort_min_age OR overlap_max < cohort_max_age) AS estimated
                FROM weighted
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = weighted.seccion_id
                GROUP BY {group_expression}
                ORDER BY label
                """
            ),
            {
                "municipality_id": municipality_id,
                "year": year,
                "min_age": min_age,
                "max_age": max_age,
                "gender": gender,
            },
        ).mappings().all()
        grouped = [dict(row) for row in rows]
        return {
            "total": int(sum(int(row["total"] or 0) for row in grouped)),
            "method": "estimated_from_cohorts" if any(row.get("estimated") for row in grouped) else "exact",
            "rows": grouped,
        }

    def get_age_cohort_abstention_by_section(
        self,
        municipality_id: str,
        year: int,
        election_type: str,
        min_age: int,
        max_age: int,
        sort_direction: str = "desc",
    ) -> dict:
        election_type_code = {
            "municipales": "MUNICIPALES",
            "andaluzas": "ANDALUZAS",
            "congreso": "CONGRESO",
            "europeas": "EUROPEAS",
        }.get(election_type.lower(), election_type.upper())
        direction_sql = "ASC" if sort_direction.lower() == "asc" else "DESC"
        rows = self.session.execute(
            text(
                f"""
                WITH normalized_population AS (
                    SELECT
                        CASE
                            WHEN anio = 2021 AND seccion_id = '2907001006' THEN '2907001021'
                            WHEN anio = 2021 AND seccion_id = '2907001021' THEN '2907001006'
                            ELSE seccion_id
                        END AS seccion_id,
                        anio,
                        genero,
                        poblacion,
                        lower(trim(edad_cohorte)) AS edad_cohorte_norm
                    FROM core.poblacion_edad
                    WHERE LEFT(seccion_id, 5) = :municipality_id
                      AND anio = :year
                      AND genero IN ('H', 'M')
                      AND edad_cohorte <> 'TOTAL'
                ),
                cohortes AS (
                    SELECT
                        *,
                        CASE
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*-\\s*[0-9]+$'
                            THEN split_part(regexp_replace(edad_cohorte_norm, '\\s+', '', 'g'), '-', 1)::int
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*(\\+|y\\s*m[aá]s)$'
                            THEN substring(edad_cohorte_norm FROM '^[0-9]+')::int
                            ELSE NULL
                        END AS cohort_min_age,
                        CASE
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*-\\s*[0-9]+$'
                            THEN split_part(regexp_replace(edad_cohorte_norm, '\\s+', '', 'g'), '-', 2)::int
                            WHEN edad_cohorte_norm ~ '^[0-9]+\\s*(\\+|y\\s*m[aá]s)$'
                            THEN 120
                            ELSE NULL
                        END AS cohort_max_age
                    FROM normalized_population
                ),
                weighted_population AS (
                    SELECT
                        seccion_id,
                        poblacion::numeric
                        * GREATEST(LEAST(cohort_max_age, :max_age) - GREATEST(cohort_min_age, :min_age) + 1, 0)
                        / NULLIF(cohort_max_age - cohort_min_age + 1, 0) AS weighted_population
                    FROM cohortes
                    WHERE cohort_min_age IS NOT NULL
                      AND cohort_max_age IS NOT NULL
                      AND cohort_max_age >= :min_age
                      AND cohort_min_age <= :max_age
                ),
                age_by_section AS (
                    SELECT
                        seccion_id,
                        ROUND(SUM(weighted_population))::bigint AS age_range_population
                    FROM weighted_population
                    GROUP BY seccion_id
                ),
                electoral AS (
                    SELECT
                        eb.seccion_id,
                        MAX(eb.censo)::bigint AS censo,
                        MAX(eb.votos_emitidos)::bigint AS votos_emitidos,
                        ROUND(
                            CASE
                                WHEN MAX(eb.censo) > 0
                                THEN (MAX(eb.censo) - MAX(eb.votos_emitidos))::numeric / MAX(eb.censo) * 100
                                ELSE NULL
                            END,
                            4
                        ) AS abstention_rate_pct
                    FROM marts.mv_electoral_behavior eb
                    WHERE LEFT(eb.seccion_id, 5) = :municipality_id
                      AND eb.anio = :year
                      AND eb.tipo_eleccion_code = :election_type_code
                    GROUP BY eb.seccion_id
                ),
                joined AS (
                    SELECT
                        age.seccion_id,
                        COALESCE(d.label_cliente, age.seccion_id) AS section_name,
                        age.age_range_population,
                        electoral.abstention_rate_pct,
                        electoral.censo,
                        electoral.votos_emitidos,
                        ROUND(age.age_range_population * electoral.abstention_rate_pct / 100)::bigint AS estimated_abstainers,
                        GREATEST(
                            age.age_range_population
                            - ROUND(age.age_range_population * electoral.abstention_rate_pct / 100)::bigint,
                            0
                        )::bigint AS estimated_voters
                    FROM age_by_section age
                    JOIN electoral
                      ON electoral.seccion_id = age.seccion_id
                    LEFT JOIN marts.dim_seccion_display d
                      ON d.seccion_id = age.seccion_id
                    WHERE electoral.abstention_rate_pct IS NOT NULL
                )
                SELECT
                    seccion_id AS section_id,
                    section_name,
                    age_range_population,
                    abstention_rate_pct,
                    estimated_abstainers,
                    estimated_voters,
                    censo AS total_electoral_census,
                    votos_emitidos AS total_votes
                FROM joined
                ORDER BY estimated_abstainers {direction_sql}, section_name
                """
            ),
            {
                "municipality_id": municipality_id,
                "year": year,
                "election_type_code": election_type_code,
                "min_age": min_age,
                "max_age": max_age,
            },
        ).mappings().all()
        section_rows = [dict(row) for row in rows]
        age_total = sum(int(row["age_range_population"] or 0) for row in section_rows)
        abstainers_total = sum(int(row["estimated_abstainers"] or 0) for row in section_rows)
        voters_total = sum(int(row["estimated_voters"] or 0) for row in section_rows)
        return {
            "rows": section_rows,
            "totals": {
                "ageRangePopulation": age_total,
                "estimatedAbstainers": abstainers_total,
                "estimatedVoters": voters_total,
                "weightedAbstentionRatePct": round(100 * abstainers_total / age_total, 2) if age_total else 0,
            },
        }

    def get_available_demographic_years(self, municipality_id: str) -> list[int]:
        rows = self.session.execute(
            text(
                """
                SELECT DISTINCT anio
                FROM core.poblacion_edad
                WHERE LEFT(seccion_id, 5) = :municipality_id
                ORDER BY anio
                """
            ),
            {"municipality_id": municipality_id},
        ).scalars().all()
        return [int(row) for row in rows]

    def get_available_socioeconomic_years(self, municipality_id: str) -> list[int]:
        rows = self.session.execute(
            text(
                """
                SELECT DISTINCT anio
                FROM marts.v_income_level_layer
                WHERE LEFT(seccion_id, 5) = :municipality_id
                ORDER BY anio
                """
            ),
            {"municipality_id": municipality_id},
        ).scalars().all()
        return [int(row) for row in rows]

    def get_available_housing_years(self, municipality_id: str) -> list[int]:
        rows = self.session.execute(
            text(
                """
                SELECT DISTINCT anio
                FROM marts.v_land_built_environment
                WHERE LEFT(seccion_id, 5) = :municipality_id
                ORDER BY anio
                """
            ),
            {"municipality_id": municipality_id},
        ).scalars().all()
        return [int(row) for row in rows]

    def get_section_similarity_profile(self, municipality_id: str, section_ids: list[str]) -> list[dict]:
        if not section_ids:
            return []

        query = text(
            """
            WITH section_features AS (
                SELECT
                    vm.seccion_id AS section_id,
                    vm.label_cliente AS section_name,
                    pop.densidad AS population_density,
                    age.average_age,
                    age.over_65_pct,
                    age.under_30_pct,
                    income.renta_media_persona AS individual_income,
                    income.renta_media_hogar AS household_income,
                    lbe.densidad_parcelaria AS parcel_density,
                    lbe.indice_construido AS building_intensity,
                    lbe.urban_intensity_index,
                    ti.market_reference_m2,
                    ti.valor_catastral_distrito_baseline,
                    ti.market_pressure_index
                FROM marts.v_mapa_seccion_2023 vm
                LEFT JOIN marts.v_population_layer pop
                  ON pop.seccion_id = vm.seccion_id
                 AND pop.anio = 2023
                LEFT JOIN marts.v_mapa_age_structure_2023 age
                  ON age.seccion_id = vm.seccion_id
                LEFT JOIN marts.v_income_level_layer income
                  ON income.seccion_id = vm.seccion_id
                 AND income.anio = 2023
                LEFT JOIN marts.v_land_built_environment lbe
                  ON lbe.seccion_id = vm.seccion_id
                 AND lbe.anio = 2023
                LEFT JOIN marts.territorial_intelligence_section_2023 ti
                  ON ti.seccion_id = vm.seccion_id
                WHERE LEFT(vm.seccion_id, 5) = :municipality_id
            ),
            municipal_avg AS (
                SELECT
                    AVG(population_density) AS municipality_population_density,
                    AVG(average_age) AS municipality_average_age,
                    AVG(over_65_pct) AS municipality_over_65_pct,
                    AVG(under_30_pct) AS municipality_under_30_pct,
                    AVG(individual_income) AS municipality_individual_income,
                    AVG(household_income) AS municipality_household_income,
                    AVG(parcel_density) AS municipality_parcel_density,
                    AVG(building_intensity) AS municipality_building_intensity,
                    AVG(urban_intensity_index) AS municipality_urban_intensity_index,
                    AVG(market_reference_m2) AS municipality_market_reference_m2,
                    AVG(valor_catastral_distrito_baseline) AS municipality_valor_catastral_distrito_baseline,
                    AVG(market_pressure_index) AS municipality_market_pressure_index
                FROM section_features
            )
            SELECT
                sf.*,
                ma.*
            FROM section_features sf
            CROSS JOIN municipal_avg ma
            WHERE sf.section_id IN :section_ids
            ORDER BY sf.section_name
            """
        ).bindparams(bindparam("section_ids", expanding=True))

        rows = self.session.execute(
            query,
            {"municipality_id": municipality_id, "section_ids": section_ids},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_winner_party_by_section_set(
        self,
        section_ids: list[str],
        election_type: str,
        year: int,
    ) -> list[dict]:
        if not section_ids:
            return []
        election_type_code = {
            "municipales": "MUNICIPALES",
            "andaluzas": "ANDALUZAS",
            "congreso": "CONGRESO",
            "europeas": "EUROPEAS",
        }.get(election_type.lower(), election_type.upper())
        query = text(
            """
            SELECT
                eb.seccion_id AS section_id,
                COALESCE(d.label_cliente, eb.seccion_id) AS section_name,
                COALESCE(eb.winning_party_family, eb.winning_party) AS winning_party,
                eb.winning_party AS winning_party_label,
                ROUND(eb.winning_party_pct::numeric, 2) AS winning_vote_pct
            FROM marts.mv_electoral_behavior eb
            LEFT JOIN marts.dim_seccion_display d
              ON d.seccion_id = eb.seccion_id
            WHERE eb.seccion_id IN :section_ids
              AND eb.tipo_eleccion_code = :election_type_code
              AND eb.anio = :year
            ORDER BY section_name
            """
        ).bindparams(bindparam("section_ids", expanding=True))
        rows = self.session.execute(
            query,
            {
                "section_ids": section_ids,
                "election_type_code": election_type_code,
                "year": year,
            },
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_municipal_party_votes(self, municipality_id: str, year: int = 2023) -> list[dict]:
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
            {"municipality_id": municipality_id, "year": year},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_turnout_comparison(self, municipality_id: str) -> list[dict]:
        rows = self.session.execute(
            text(
                """
                SELECT
                    anio AS year,
                    ROUND(100 * SUM(votos_emitidos)::numeric / NULLIF(SUM(censo), 0), 2) AS turnout
                FROM marts.mv_electoral_behavior
                WHERE LEFT(seccion_id, 5) = :municipality_id
                  AND tipo_eleccion_code = 'MUNICIPALES'
                  AND anio IN (2019, 2023)
                GROUP BY anio
                ORDER BY anio
                """
            ),
            {"municipality_id": municipality_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_party_strength(self, municipality_id: str, party: str, year: int = 2023) -> list[dict]:
        rows = self.session.execute(
            text(
                """
                SELECT
                    COALESCE(d.label_cliente, eb.seccion_id) AS section,
                    ROUND(SUM((party_result->>'pct')::numeric * 100), 2) AS percentage
                FROM marts.mv_electoral_behavior eb
                CROSS JOIN LATERAL jsonb_array_elements(eb.party_results_json) AS party_result
                LEFT JOIN marts.dim_seccion_display d
                  ON d.seccion_id = eb.seccion_id
                WHERE LEFT(eb.seccion_id, 5) = :municipality_id
                  AND eb.tipo_eleccion_code = 'MUNICIPALES'
                  AND eb.anio = :year
                  AND party_result->>'normalized_party_family' = :party
                GROUP BY eb.seccion_id, d.label_cliente
                ORDER BY percentage DESC, section
                LIMIT 5
                """
            ),
            {"municipality_id": municipality_id, "party": party, "year": year},
        ).mappings().all()
        return [dict(row) for row in rows]

    def audit(
        self,
        *,
        question: str,
        municipality_id: str,
        intent: str,
        tools: list[str],
        datasets: list[str],
        answer: str,
        confidence_level: str,
        methodological_notes: list[str],
        error: str | None = None,
    ) -> str:
        row = self.session.execute(
            text(
                """
                INSERT INTO core.agent_audit_log (
                    question,
                    municipality_id,
                    datasets_used,
                    variables_used,
                    models_used,
                    confidence_level,
                    response_category,
                    metadata
                ) VALUES (
                    :question,
                    :municipality_id,
                    CAST(:datasets AS jsonb),
                    '[]'::jsonb,
                    CAST(:tools AS jsonb),
                    :confidence_level,
                    :intent,
                    CAST(:metadata AS jsonb)
                )
                RETURNING audit_id
                """
            ),
            {
                "question": question,
                "municipality_id": municipality_id,
                "datasets": json.dumps(datasets),
                "tools": json.dumps(tools),
                "confidence_level": confidence_level,
                "intent": intent,
                "metadata": json.dumps(
                    {
                        "final_answer": answer,
                        "methodological_notes": methodological_notes,
                        "error": error,
                    }
                ),
            },
        ).mappings().one()
        self.session.commit()
        return str(row["audit_id"])
