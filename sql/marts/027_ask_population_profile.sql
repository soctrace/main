CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW marts.ask_population_profile AS
WITH cohort_midpoints AS (
    SELECT *
    FROM (VALUES
        ('0-4', 2.5::numeric),
        ('5-9', 7.5::numeric),
        ('10-14', 12.5::numeric),
        ('15-19', 17.5::numeric),
        ('20-24', 22.5::numeric),
        ('25-29', 27.5::numeric),
        ('30-34', 32.5::numeric),
        ('35-39', 37.5::numeric),
        ('40-44', 42.5::numeric),
        ('45-49', 47.5::numeric),
        ('50-54', 52.5::numeric),
        ('55-59', 57.5::numeric),
        ('60-64', 62.5::numeric),
        ('65-69', 67.5::numeric),
        ('70-74', 72.5::numeric),
        ('75-79', 77.5::numeric),
        ('80-84', 82.5::numeric),
        ('85-89', 87.5::numeric),
        ('90-94', 92.5::numeric),
        ('95-99', 97.5::numeric),
        ('100+', 102.5::numeric)
    ) AS midpoint(age_cohort, midpoint_age)
),
age_metrics AS (
    SELECT
        p.seccion_id,
        p.anio AS year,
        SUM(p.poblacion) FILTER (WHERE p.edad_cohorte IN ('0-4', '5-9', '10-14')) AS population_0_14,
        SUM(p.poblacion) FILTER (WHERE p.edad_cohorte = '15-19') AS population_15_19,
        SUM(p.poblacion) FILTER (WHERE p.edad_cohorte IN ('20-24', '25-29')) AS population_20_29,
        SUM(p.poblacion) FILTER (WHERE p.edad_cohorte IN ('20-24', '25-29', '30-34')) AS population_20_34,
        SUM(p.poblacion) FILTER (WHERE p.edad_cohorte = '35-39') AS population_35_39,
        SUM(p.poblacion) FILTER (
            WHERE p.edad_cohorte IN ('65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95-99', '100+')
        ) AS population_over_65,
        SUM(p.poblacion * c.midpoint_age) / NULLIF(SUM(p.poblacion), 0) AS average_age
    FROM core.poblacion_edad p
    LEFT JOIN cohort_midpoints c
      ON c.age_cohort = p.edad_cohorte
    WHERE p.genero IN ('H', 'M')
    GROUP BY p.seccion_id, p.anio
)
SELECT
    LEFT(v.seccion_id, 5) AS municipio_id,
    CASE LEFT(v.seccion_id, 5)
        WHEN '29070' THEN 'Mijas'
        ELSE 'Municipio ' || LEFT(v.seccion_id, 5)
    END AS municipio_nombre,
    v.seccion_id,
    COALESCE(v.label_cliente, d.label_cliente, v.seccion_id) AS section_name,
    v.anio AS year,
    v.pob_total::bigint AS population_total,
    v.pob_total::bigint AS total_population,
    ROUND((COALESCE(a.population_0_14, 0) + COALESCE(a.population_15_19, 0) * 0.6)::numeric, 0)::bigint AS population_under_18,
    COALESCE(v.pob_0_14, 0)::bigint + COALESCE(v.pob_15_29, 0)::bigint AS population_under_30,
    ROUND(
        (
            COALESCE(a.population_15_19, 0) * 0.4
            + COALESCE(a.population_20_34, 0)
            + COALESCE(a.population_35_39, 0) * 0.2
        )::numeric,
        0
    )::bigint AS population_18_35,
    COALESCE(v.pob_65p, a.population_over_65, 0)::bigint AS population_over_65,
    ROUND(a.average_age::numeric, 2) AS average_age,
    ROUND(v.densidad::numeric, 2) AS population_density,
    ROUND((COALESCE(v.pob_0_14, 0) + COALESCE(v.pob_15_29, 0))::numeric / NULLIF(v.pob_total, 0) * 100, 2) AS population_under_30_pct,
    ROUND(COALESCE(v.pob_65p, a.population_over_65, 0)::numeric / NULLIF(v.pob_total, 0) * 100, 2) AS population_over_65_pct
FROM marts.v_population_layer v
LEFT JOIN age_metrics a
  ON a.seccion_id = v.seccion_id
 AND a.year = v.anio
LEFT JOIN marts.dim_seccion_display d
  ON d.seccion_id = v.seccion_id;

CREATE OR REPLACE VIEW marts.ask_section_profile AS
SELECT
    municipio_id,
    municipio_nombre,
    seccion_id,
    section_name,
    year,
    population_total,
    population_density,
    average_age,
    population_under_30,
    population_under_30_pct,
    population_over_65,
    population_over_65_pct,
    NULL::numeric AS income_individual,
    NULL::numeric AS income_household,
    NULL::numeric AS abstention_pct,
    NULL::numeric AS participation_pct,
    NULL::text AS winner_party,
    NULL::numeric AS winning_party_pct
FROM marts.ask_population_profile;

COMMENT ON VIEW marts.ask_population_profile IS
    'Approved Ask SocTrace population profile. Grain: municipality -> section -> year. Built from marts.v_population_layer and core.poblacion_edad.';

COMMENT ON COLUMN marts.ask_population_profile.population_under_18 IS
    'Estimated from grouped age cohorts: 0-14 plus 3/5 of 15-19.';

COMMENT ON COLUMN marts.ask_population_profile.population_18_35 IS
    'Estimated from grouped age cohorts: 2/5 of 15-19, 20-34, and 1/5 of 35-39.';
