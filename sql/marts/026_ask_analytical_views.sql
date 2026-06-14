CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW marts.ask_section_lookup AS
SELECT
    LEFT(d.seccion_id, 5) AS municipio_id,
    CASE LEFT(d.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(d.seccion_id, 5)
    END AS municipio_nombre,
    d.seccion_id,
    COALESCE(d.label_cliente, 'Sección ' || RIGHT(d.seccion_id, 3)) AS section_name,
    d.seccion_numero_visible,
    d.nombre_barrio,
    d.zona_macro
FROM marts.dim_seccion_display d;

CREATE OR REPLACE VIEW marts.ask_population_age AS
SELECT
    LEFT(p.seccion_id, 5) AS municipio_id,
    CASE LEFT(p.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(p.seccion_id, 5)
    END AS municipio_nombre,
    p.seccion_id,
    COALESCE(l.section_name, p.seccion_id) AS section_name,
    p.anio AS year,
    p.genero AS gender,
    p.edad_cohorte AS age_cohort,
    p.poblacion AS population
FROM core.poblacion_edad p
LEFT JOIN marts.ask_section_lookup l
  ON l.seccion_id = p.seccion_id;

CREATE OR REPLACE VIEW marts.ask_population_age_range AS
SELECT
    LEFT(a.seccion_id, 5) AS municipio_id,
    CASE LEFT(a.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(a.seccion_id, 5)
    END AS municipio_nombre,
    a.seccion_id,
    COALESCE(a.label_cliente, l.section_name, a.seccion_id) AS section_name,
    a.anio AS year,
    a.total_poblacion::bigint AS population_total,
    ROUND(a.densidad::numeric, 2) AS population_density,
    ROUND(a.average_age::numeric, 2) AS average_age,
    ROUND((a.total_poblacion * a.under_30_pct / 100.0)::numeric, 0)::bigint AS population_under_30,
    ROUND(a.under_30_pct::numeric, 2) AS population_under_30_pct,
    ROUND((a.total_poblacion * a.over_65_pct / 100.0)::numeric, 0)::bigint AS population_over_65,
    ROUND(a.over_65_pct::numeric, 2) AS population_over_65_pct
FROM marts.v_mapa_age_structure a
LEFT JOIN marts.ask_section_lookup l
  ON l.seccion_id = a.seccion_id;

CREATE OR REPLACE VIEW marts.ask_income AS
SELECT
    LEFT(i.seccion_id, 5) AS municipio_id,
    CASE LEFT(i.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(i.seccion_id, 5)
    END AS municipio_nombre,
    i.seccion_id,
    COALESCE(i.label_cliente, l.section_name, i.seccion_id) AS section_name,
    i.anio AS year,
    i.renta_media_persona AS income_individual,
    i.renta_media_hogar AS income_household,
    i.income_quintile,
    i.income_level,
    i.income_rank_municipal,
    i.income_index
FROM marts.v_income_level_layer i
LEFT JOIN marts.ask_section_lookup l
  ON l.seccion_id = i.seccion_id;

CREATE OR REPLACE VIEW marts.ask_electoral_results AS
SELECT
    LEFT(r.seccion_id, 5) AS municipio_id,
    CASE LEFT(r.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(r.seccion_id, 5)
    END AS municipio_nombre,
    r.seccion_id,
    COALESCE(l.section_name, r.seccion_id) AS section_name,
    r.election_id,
    r.tipo_eleccion_code AS election_type,
    r.tipo_eleccion_nombre AS election_name,
    r.anio AS election_year,
    r.anio AS year,
    r.election_date,
    r.siglas AS party,
    r.normalized_party_family AS canonical_party,
    r.ideological_bloc,
    r.is_local_party,
    r.votos_partido AS votes,
    r.votos_validos AS valid_votes,
    r.votos_emitidos AS votes_cast,
    r.censo AS census,
    ROUND(
        CASE WHEN r.pct_voto <= 1 THEN r.pct_voto * 100 ELSE r.pct_voto END,
        6
    ) AS vote_pct
FROM marts.v_resultados_seccion_eleccion r
LEFT JOIN marts.ask_section_lookup l
  ON l.seccion_id = r.seccion_id;

CREATE OR REPLACE VIEW marts.ask_electoral_summary AS
SELECT
    LEFT(e.seccion_id, 5) AS municipio_id,
    CASE LEFT(e.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(e.seccion_id, 5)
    END AS municipio_nombre,
    e.seccion_id,
    COALESCE(l.section_name, e.seccion_id) AS section_name,
    e.election_id,
    e.tipo_eleccion_code AS election_type,
    e.tipo_eleccion_nombre AS election_name,
    e.anio AS election_year,
    e.anio AS year,
    e.election_date,
    e.censo AS census,
    e.votos_emitidos AS votes_cast,
    e.votos_validos AS valid_votes,
    ROUND(e.participacion::numeric * 100, 2) AS participation_pct,
    ROUND((1 - e.participacion)::numeric * 100, 2) AS abstention_pct,
    COALESCE(e.winning_party_family, e.winning_party) AS winner_party,
    e.winning_party_pct,
    e.runner_up_party,
    e.runner_up_pct,
    e.victory_margin_pct,
    e.local_vote_pct,
    e.left_bloc_pct,
    e.right_bloc_pct,
    e.fragmentation_index,
    e.competitive_parties_count
FROM marts.mv_electoral_behavior e
LEFT JOIN marts.ask_section_lookup l
  ON l.seccion_id = e.seccion_id;

CREATE OR REPLACE VIEW marts.ask_housing AS
SELECT
    LEFT(h.seccion_id, 5) AS municipio_id,
    CASE LEFT(h.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(h.seccion_id, 5)
    END AS municipio_nombre,
    h.seccion_id,
    COALESCE(h.label_cliente, l.section_name, h.seccion_id) AS section_name,
    h.anio AS year,
    h.market_reference_m2 AS estimated_real_estate_value_m2,
    h.market_pressure_index AS residential_pressure_index,
    h.housing_signal_score,
    h.opportunity_zone_score,
    h.residential_saturation_index,
    h.housing_stress_index,
    h.num_parcelas AS parcel_count,
    h.densidad_parcelaria AS parcel_density,
    h.indice_construido AS built_intensity,
    h.urban_intensity_index,
    h.housing_reference_confidence
FROM marts.housing_intelligence_features_2023 h
LEFT JOIN marts.ask_section_lookup l
  ON l.seccion_id = h.seccion_id;

CREATE OR REPLACE VIEW marts.ask_section_profile AS
SELECT
    COALESCE(p.municipio_id, a.municipio_id, i.municipio_id, es.municipio_id) AS municipio_id,
    COALESCE(p.municipio_nombre, a.municipio_nombre, i.municipio_nombre, es.municipio_nombre) AS municipio_nombre,
    COALESCE(p.seccion_id, a.seccion_id, i.seccion_id, es.seccion_id) AS seccion_id,
    COALESCE(p.section_name, a.section_name, i.section_name, es.section_name) AS section_name,
    COALESCE(p.year, a.year, i.year, es.year) AS year,
    COALESCE(a.population_total, p.pob_total) AS population_total,
    COALESCE(a.population_density, p.densidad) AS population_density,
    a.average_age,
    a.population_under_30,
    a.population_under_30_pct,
    a.population_over_65,
    a.population_over_65_pct,
    i.income_individual,
    i.income_household,
    es.abstention_pct,
    es.participation_pct,
    es.winner_party,
    es.winning_party_pct
FROM (
    SELECT
        LEFT(seccion_id, 5) AS municipio_id,
        CASE LEFT(seccion_id, 5)
            WHEN '29070' THEN 'Mijas'
            ELSE 'Municipio ' || LEFT(seccion_id, 5)
        END AS municipio_nombre,
        seccion_id,
        label_cliente AS section_name,
        anio AS year,
        pob_total,
        densidad
    FROM marts.v_population_layer
) p
FULL JOIN marts.ask_population_age_range a
  ON a.seccion_id = p.seccion_id
 AND a.year = p.year
FULL JOIN marts.ask_income i
  ON i.seccion_id = COALESCE(p.seccion_id, a.seccion_id)
 AND i.year = COALESCE(p.year, a.year)
FULL JOIN (
    SELECT *
    FROM marts.ask_electoral_summary
    WHERE election_type = 'MUNICIPALES'
) es
  ON es.seccion_id = COALESCE(p.seccion_id, a.seccion_id, i.seccion_id)
 AND es.year = COALESCE(p.year, a.year, i.year);

COMMENT ON VIEW marts.ask_section_profile IS
    'Approved Ask SocTrace section-year profile view. Grain: municipality -> section -> year.';
COMMENT ON VIEW marts.ask_population_age IS
    'Approved Ask SocTrace age cohort view. Grain: municipality -> section -> year -> age cohort -> gender.';
COMMENT ON VIEW marts.ask_population_age_range IS
    'Approved Ask SocTrace derived age metrics by section and year.';
COMMENT ON VIEW marts.ask_electoral_results IS
    'Approved Ask SocTrace party-level electoral results by section and election.';
COMMENT ON VIEW marts.ask_electoral_summary IS
    'Approved Ask SocTrace electoral summary by section and election.';
COMMENT ON VIEW marts.ask_income IS
    'Approved Ask SocTrace income indicators by section and year.';
COMMENT ON VIEW marts.ask_housing IS
    'Approved Ask SocTrace housing and built-environment intelligence by section and year.';
COMMENT ON VIEW marts.ask_section_lookup IS
    'Approved Ask SocTrace human-readable section lookup.';
