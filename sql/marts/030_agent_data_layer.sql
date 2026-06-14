CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW marts.agent_section_lookup AS
SELECT
    LEFT(d.seccion_id, 5) AS municipio_id,
    CASE LEFT(d.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(d.seccion_id, 5)
    END AS municipio_nombre,
    d.seccion_id AS section_id,
    d.seccion_numero_visible AS section_number,
    COALESCE(d.label_cliente, 'Sección ' || d.seccion_numero_visible, d.seccion_id) AS section_name,
    COALESCE(d.label_cliente, 'Sección ' || d.seccion_numero_visible, d.seccion_id) AS display_name
FROM marts.dim_seccion_display d;

COMMENT ON VIEW marts.agent_section_lookup IS
    'Canonical Agent section lookup. Grain: municipality + section. Currently populated for Mijas, structurally multi-municipality ready through section_id prefix.';

CREATE OR REPLACE VIEW marts.agent_population_age AS
WITH normalized AS (
    SELECT
        LEFT(p.seccion_id, 5) AS municipio_id,
        CASE LEFT(p.seccion_id, 5)
            WHEN '29070' THEN 'Mijas'
            ELSE 'Municipio ' || LEFT(p.seccion_id, 5)
        END AS municipio_nombre,
        p.seccion_id AS section_id,
        COALESCE(l.section_name, p.seccion_id) AS section_name,
        p.anio AS year,
        CASE WHEN p.genero IN ('H', 'M') THEN p.genero ELSE 'all' END AS gender,
        p.edad_cohorte AS age_cohort,
        lower(trim(p.edad_cohorte)) AS age_cohort_norm,
        p.poblacion::bigint AS people
    FROM core.poblacion_edad p
    LEFT JOIN marts.agent_section_lookup l
      ON l.section_id = p.seccion_id
    WHERE p.edad_cohorte IS NOT NULL
      AND upper(trim(p.edad_cohorte)) <> 'TOTAL'
)
SELECT
    municipio_id,
    municipio_nombre,
    section_id,
    section_name,
    year,
    gender,
    age_cohort,
    CASE
        WHEN age_cohort_norm ~ '^[0-9]+\s*-\s*[0-9]+$'
        THEN split_part(regexp_replace(age_cohort_norm, '\s+', '', 'g'), '-', 1)::integer
        WHEN age_cohort_norm ~ '^[0-9]+\s*(\+|y\s*m[aá]s)$'
        THEN substring(age_cohort_norm FROM '^[0-9]+')::integer
        WHEN age_cohort_norm ~ '^[0-9]+$'
        THEN age_cohort_norm::integer
        ELSE NULL::integer
    END AS age_min,
    CASE
        WHEN age_cohort_norm ~ '^[0-9]+\s*-\s*[0-9]+$'
        THEN split_part(regexp_replace(age_cohort_norm, '\s+', '', 'g'), '-', 2)::integer
        WHEN age_cohort_norm ~ '^[0-9]+\s*(\+|y\s*m[aá]s)$'
        THEN 120
        WHEN age_cohort_norm ~ '^[0-9]+$'
        THEN age_cohort_norm::integer
        ELSE NULL::integer
    END AS age_max,
    people
FROM normalized;

COMMENT ON VIEW marts.agent_population_age IS
    'Canonical Agent population by age cohort, gender, section and year. Preserves original cohort and parses age_min/age_max for cohort calculations.';

CREATE OR REPLACE VIEW marts.agent_electoral_results AS
SELECT
    LEFT(r.seccion_id, 5) AS municipio_id,
    CASE LEFT(r.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(r.seccion_id, 5)
    END AS municipio_nombre,
    r.seccion_id AS section_id,
    COALESCE(l.section_name, r.seccion_id) AS section_name,
    r.election_id::text AS election_id,
    r.tipo_eleccion_code AS election_type,
    r.anio AS election_year,
    r.mes AS election_month,
    CONCAT(COALESCE(r.tipo_eleccion_nombre, r.tipo_eleccion_code), ' ', r.anio) AS election_label,
    COALESCE(r.siglas, r.denominacion, r.normalized_party_family) AS party,
    CASE
        WHEN upper(COALESCE(r.normalized_party_family, '')) IN ('PP', 'PSOE', 'VOX', 'CS', 'SUMAR_PODEMOS_IU')
            THEN upper(r.normalized_party_family)
        WHEN COALESCE(r.siglas, '') ILIKE '%ADELANTE%'
            THEN 'Adelante Andalucía'
        WHEN COALESCE(r.siglas, '') ILIKE '%MIJAS 100%'
          OR COALESCE(r.denominacion, '') ILIKE '%MIJAS 100%'
            THEN 'Mijas 100%'
        WHEN COALESCE(r.siglas, '') ILIKE '%POR MI PUEBLO%'
            THEN 'Por Mi Pueblo'
        WHEN COALESCE(r.normalized_party_family, '') = 'LOCAL'
            THEN COALESCE(NULLIF(r.siglas, ''), 'LOCAL')
        ELSE COALESCE(NULLIF(r.normalized_party_family, ''), NULLIF(r.siglas, ''), 'OTHER')
    END AS canonical_party,
    r.votos_partido::bigint AS votes,
    r.votos_validos::bigint AS valid_votes,
    ROUND(
        CASE WHEN r.pct_voto <= 1 THEN r.pct_voto * 100 ELSE r.pct_voto END,
        4
    ) AS vote_pct
FROM marts.v_resultados_seccion_eleccion r
LEFT JOIN marts.agent_section_lookup l
  ON l.section_id = r.seccion_id
WHERE r.seccion_id IS NOT NULL;

COMMENT ON VIEW marts.agent_electoral_results IS
    'Canonical Agent electoral results by section, election and party. Does not aggregate election detail.';

CREATE OR REPLACE VIEW marts.agent_electoral_summary AS
WITH ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.section_id, r.election_id
            ORDER BY r.vote_pct DESC, r.votes DESC, r.canonical_party
        ) AS party_rank
    FROM marts.agent_electoral_results r
),
section_totals AS (
    SELECT
        e.election_id::text AS election_id,
        e.seccion_id AS section_id,
        MAX(e.censo)::bigint AS census,
        MAX(e.votos_validos)::bigint AS valid_votes,
        MAX(e.votos_emitidos)::bigint AS total_votes,
        ROUND(MAX(e.participacion)::numeric * 100, 4) AS participation_pct,
        ROUND((1 - MAX(e.participacion)::numeric) * 100, 4) AS abstention_pct
    FROM marts.mv_electoral_behavior e
    GROUP BY e.election_id, e.seccion_id
)
SELECT
    MAX(r.municipio_id) AS municipio_id,
    MAX(r.municipio_nombre) AS municipio_nombre,
    r.section_id,
    MAX(r.section_name) AS section_name,
    r.election_id,
    MAX(r.election_type) AS election_type,
    MAX(r.election_year) AS election_year,
    MAX(r.election_label) AS election_label,
    MAX(t.census) AS census,
    MAX(t.valid_votes) AS valid_votes,
    MAX(t.total_votes) AS total_votes,
    MAX(t.participation_pct) AS participation_pct,
    MAX(t.abstention_pct) AS abstention_pct,
    MAX(r.canonical_party) FILTER (WHERE r.party_rank = 1) AS winner_party,
    MAX(r.vote_pct) FILTER (WHERE r.party_rank = 1) AS winner_vote_pct,
    MAX(r.canonical_party) FILTER (WHERE r.party_rank = 2) AS second_party,
    MAX(r.vote_pct) FILTER (WHERE r.party_rank = 2) AS second_vote_pct,
    ROUND(
        COALESCE(MAX(r.vote_pct) FILTER (WHERE r.party_rank = 1), 0)
        - COALESCE(MAX(r.vote_pct) FILTER (WHERE r.party_rank = 2), 0),
        4
    ) AS margin_pct
FROM ranked r
LEFT JOIN section_totals t
  ON t.election_id = r.election_id
 AND t.section_id = r.section_id
GROUP BY r.section_id, r.election_id;

COMMENT ON VIEW marts.agent_electoral_summary IS
    'Canonical Agent electoral summary by section and election. Winner, runner-up and margin are derived from agent_electoral_results.';

CREATE OR REPLACE VIEW marts.agent_income_sources AS
SELECT
    COALESCE(LEFT(i.seccion_id, 5), LEFT(s.seccion_id, 5)) AS municipio_id,
    CASE COALESCE(LEFT(i.seccion_id, 5), LEFT(s.seccion_id, 5))
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || COALESCE(LEFT(i.seccion_id, 5), LEFT(s.seccion_id, 5))
    END AS municipio_nombre,
    COALESCE(i.seccion_id, s.seccion_id) AS section_id,
    COALESCE(l.section_name, i.label_cliente, s.label_cliente, COALESCE(i.seccion_id, s.seccion_id)) AS section_name,
    COALESCE(i.anio, s.anio) AS year,
    i.renta_media_persona AS income_individual,
    i.renta_media_hogar AS income_household,
    s.income_salary AS salary_share,
    s.income_pension AS pension_share,
    s.income_unemployment AS unemployment_share,
    COALESCE(s.income_other, 0) + COALESCE(s.income_social_benefits, 0) AS other_income_share
FROM marts.v_income_level_layer i
FULL JOIN marts.v_income_sources_profile s
  ON s.seccion_id = i.seccion_id
 AND s.anio = i.anio
LEFT JOIN marts.agent_section_lookup l
  ON l.section_id = COALESCE(i.seccion_id, s.seccion_id);

COMMENT ON VIEW marts.agent_income_sources IS
    'Canonical Agent income and income-source profile by section and year. Income-source shares currently come from INE income source percentages.';

CREATE OR REPLACE VIEW marts.agent_housing_profile AS
SELECT
    COALESCE(LEFT(lbe.seccion_id, 5), LEFT(h.seccion_id, 5), LEFT(p.seccion_id, 5)) AS municipio_id,
    CASE COALESCE(LEFT(lbe.seccion_id, 5), LEFT(h.seccion_id, 5), LEFT(p.seccion_id, 5))
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || COALESCE(LEFT(lbe.seccion_id, 5), LEFT(h.seccion_id, 5), LEFT(p.seccion_id, 5))
    END AS municipio_nombre,
    COALESCE(lbe.seccion_id, h.seccion_id, p.seccion_id) AS section_id,
    COALESCE(l.section_name, lbe.label_cliente, h.label_cliente, COALESCE(lbe.seccion_id, h.seccion_id, p.seccion_id)) AS section_name,
    COALESCE(lbe.anio, h.anio, p.anio, 2023) AS year,
    lbe.densidad_parcelaria AS parcel_density,
    lbe.huella_construida_m2 AS built_footprint,
    lbe.superficie_media_parcela_m2 AS avg_plot_size,
    lbe.indice_construido AS building_intensity,
    p.valor_catastral_estimado_m2 AS estimated_cadastral_value_m2,
    COALESCE(p.precio_mercado_m2, h.market_reference_m2, h.precio_m2_observado) AS market_price_estimated_m2,
    p.ratio_mercado_catastro AS market_to_cadastral_ratio,
    COALESCE(p.clasificacion_inmobiliaria, h.strategic_profile_label) AS housing_classification,
    COALESCE(h.market_pressure_index, h.housing_stress_index, h.residential_saturation_index) AS residential_pressure_index
FROM marts.v_land_built_environment lbe
FULL JOIN marts.housing_intelligence_features_2023 h
  ON h.seccion_id = lbe.seccion_id
 AND h.anio = lbe.anio
FULL JOIN marts.real_estate_section_premium_2023 p
  ON p.seccion_id = COALESCE(lbe.seccion_id, h.seccion_id)
 AND p.anio = COALESCE(lbe.anio, h.anio, 2023)
LEFT JOIN marts.agent_section_lookup l
  ON l.section_id = COALESCE(lbe.seccion_id, h.seccion_id, p.seccion_id);

COMMENT ON VIEW marts.agent_housing_profile IS
    'Canonical Agent housing, land and built environment profile. Currently populated from 2023 housing and built-environment marts.';

DO $$
BEGIN
    IF to_regclass('marts.agent_section_profile') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'marts'
              AND c.relname = 'agent_section_profile'
              AND c.relkind = 'm'
        ) THEN
            DROP MATERIALIZED VIEW marts.agent_section_profile;
        ELSE
            DROP VIEW marts.agent_section_profile;
        END IF;
    END IF;
    IF to_regclass('marts.agent_section_profile_base') IS NOT NULL THEN
        DROP MATERIALIZED VIEW marts.agent_section_profile_base;
    END IF;
END $$;

CREATE MATERIALIZED VIEW marts.agent_section_profile_base AS
WITH population AS (
    SELECT
        p.municipio_id,
        p.municipio_nombre,
        p.seccion_id AS section_id,
        p.section_name,
        p.year,
        p.population_total,
        p.population_density,
        p.average_age,
        p.population_under_18,
        ROUND(p.population_under_18::numeric / NULLIF(p.population_total, 0) * 100, 2) AS population_under_18_pct,
        p.population_under_30,
        p.population_under_30_pct,
        p.population_over_65,
        p.population_over_65_pct
    FROM marts.ask_population_profile p
),
latest_municipal_election AS (
    SELECT DISTINCT ON (municipio_id)
        municipio_id,
        election_year,
        election_id
    FROM marts.agent_electoral_summary
    WHERE election_type = 'MUNICIPALES'
    ORDER BY municipio_id, election_year DESC, election_id DESC
)
SELECT
    p.municipio_id,
    p.municipio_nombre,
    p.section_id,
    p.section_name,
    p.year,
    p.population_total,
    p.population_density,
    p.average_age,
    p.population_under_18,
    p.population_under_18_pct,
    p.population_under_30,
    p.population_under_30_pct,
    p.population_over_65,
    p.population_over_65_pct,
    inc.income_individual,
    inc.income_household,
    es.participation_pct,
    es.abstention_pct,
    es.winner_party,
    hp.built_footprint,
    hp.parcel_density,
    hp.building_intensity,
    hp.estimated_cadastral_value_m2 AS estimated_real_estate_value_m2,
    hp.market_price_estimated_m2,
    hp.housing_classification AS housing_pressure_label
FROM population p
LEFT JOIN marts.agent_income_sources inc
  ON inc.section_id = p.section_id
 AND inc.year = p.year
LEFT JOIN latest_municipal_election latest
  ON latest.municipio_id = p.municipio_id
LEFT JOIN marts.agent_electoral_summary es
  ON es.section_id = p.section_id
 AND es.election_id = latest.election_id
LEFT JOIN marts.agent_housing_profile hp
  ON hp.section_id = p.section_id
 AND hp.year = p.year;

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_section_profile_pk
    ON marts.agent_section_profile_base (municipio_id, section_id, year);

CREATE INDEX IF NOT EXISTS idx_agent_section_profile_municipio_year
    ON marts.agent_section_profile_base (municipio_id, year);

CREATE OR REPLACE VIEW marts.agent_section_profile AS
SELECT *
FROM marts.agent_section_profile_base;

COMMENT ON MATERIALIZED VIEW marts.agent_section_profile_base IS
    'Materialized base for marts.agent_section_profile. Refresh when canonical source views change.';

COMMENT ON VIEW marts.agent_section_profile IS
    'Canonical Agent section profile materialized for fast agent reads. Grain: municipality + section + population year. Income joins by same year; electoral fields use latest municipal election; housing is present for 2023 where available.';
