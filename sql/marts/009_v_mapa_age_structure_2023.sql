CREATE OR REPLACE VIEW marts.v_mapa_age_structure AS
WITH poblacion_base AS (
    SELECT
        CASE
            -- Keep the same 2021 stable dashboard identity used by the
            -- temporal population and map views.
            WHEN anio = 2021 AND seccion_id = '2907001006' THEN '2907001021'
            WHEN anio = 2021 AND seccion_id = '2907001021' THEN '2907001006'
            ELSE seccion_id
        END AS seccion_id,
        anio,
        genero,
        edad_cohorte,
        poblacion,
        lower(trim(edad_cohorte)) AS edad_cohorte_norm
    FROM core.poblacion_edad
    WHERE anio BETWEEN 2021 AND 2025
      AND genero IN ('H', 'M')
      AND edad_cohorte <> 'TOTAL'
),
cohortes AS (
    SELECT
        seccion_id,
        anio,
        edad_cohorte,
        poblacion,
        CASE
            WHEN edad_cohorte_norm ~ '^[0-9]+\s*-\s*[0-9]+$'
            THEN (
                split_part(regexp_replace(edad_cohorte_norm, '\s+', '', 'g'), '-', 1)::numeric
                + split_part(regexp_replace(edad_cohorte_norm, '\s+', '', 'g'), '-', 2)::numeric
            ) / 2.0

            -- Open-ended cohorts use lower bound + 2.5 years. In this source
            -- that means 100+ is represented as 102.5; an 85+ source would be
            -- represented as 87.5.
            WHEN edad_cohorte_norm ~ '^[0-9]+\s*(\+|y\s*m[aá]s)$'
            THEN substring(edad_cohorte_norm FROM '^[0-9]+')::numeric + 2.5

            ELSE NULL
        END AS edad_representativa
    FROM poblacion_base
),
poblacion_agg AS (
    SELECT
        seccion_id,
        anio,
        SUM(poblacion) AS total_poblacion,
        SUM(edad_representativa * poblacion) FILTER (WHERE edad_representativa IS NOT NULL) AS edad_ponderada,
        SUM(poblacion) FILTER (WHERE edad_representativa IS NOT NULL) AS poblacion_mapeada,
        SUM(poblacion) FILTER (
            WHERE edad_cohorte IN ('0-4', '5-9', '10-14', '15-19', '20-24', '25-29')
        ) AS under_30_poblacion,
        SUM(poblacion) FILTER (
            WHERE edad_cohorte IN ('65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95-99', '100+', '85 y más', '85+')
        ) AS over_65_poblacion
    FROM cohortes
    GROUP BY seccion_id, anio
),
base AS (
    SELECT
        g.seccion_id,
        g.anio,
        g.seccion_numero_visible,
        g.nombre_barrio,
        g.zona_macro,
        g.label_cliente,
        g.geom,
        g.geom_json,
        ROUND(
            CASE
                WHEN p.poblacion_mapeada > 0 THEN p.edad_ponderada / p.poblacion_mapeada
                ELSE NULL
            END,
            2
        ) AS average_age,
        p.total_poblacion,
        ROUND(
            CASE WHEN p.total_poblacion > 0 THEN p.over_65_poblacion::numeric / p.total_poblacion * 100 ELSE NULL END,
            2
        ) AS over_65_pct,
        ROUND(
            CASE WHEN p.total_poblacion > 0 THEN p.under_30_poblacion::numeric / p.total_poblacion * 100 ELSE NULL END,
            2
        ) AS under_30_pct,
        ROUND(
            CASE WHEN g.area_km2 > 0 THEN p.total_poblacion::numeric / g.area_km2 ELSE NULL END,
            2
        ) AS densidad
    FROM marts.v_mapa_seccion_anio g
    JOIN poblacion_agg p
      ON p.seccion_id = g.seccion_id
     AND p.anio = g.anio
    WHERE g.anio BETWEEN 2021 AND 2025
      AND g.geom IS NOT NULL
      AND ST_IsValid(g.geom)
),
ranked AS (
    SELECT
        *,
        NTILE(5) OVER (PARTITION BY anio ORDER BY densidad NULLS LAST) AS density_quintile
    FROM base
)
SELECT
    seccion_id,
    anio,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    geom,
    geom_json,
    average_age,
    CASE
        WHEN average_age < 36 THEN 1
        WHEN average_age >= 36 AND average_age < 39 THEN 2
        WHEN average_age >= 39 AND average_age < 42 THEN 3
        WHEN average_age >= 42 AND average_age <= 44.5 THEN 4
        WHEN average_age > 44.5 THEN 5
        ELSE NULL
    END AS age_group,
    CASE
        WHEN average_age < 36 THEN 'Young'
        WHEN average_age >= 36 AND average_age < 39 THEN 'Young Adult'
        WHEN average_age >= 39 AND average_age < 42 THEN 'Balanced'
        WHEN average_age >= 42 AND average_age <= 44.5 THEN 'Mature'
        WHEN average_age > 44.5 THEN 'Senior'
        ELSE NULL
    END AS age_group_label,
    CASE
        WHEN average_age < 36 THEN 'young'
        WHEN average_age >= 36 AND average_age < 39 THEN 'young_adult'
        WHEN average_age >= 39 AND average_age < 42 THEN 'balanced'
        WHEN average_age >= 42 AND average_age <= 44.5 THEN 'mature'
        WHEN average_age > 44.5 THEN 'senior'
        ELSE NULL
    END AS age_color_key,
    total_poblacion,
    over_65_pct,
    under_30_pct,
    densidad,
    CASE density_quintile
        WHEN 1 THEN 'Very Low Density'
        WHEN 2 THEN 'Low Density'
        WHEN 3 THEN 'Moderate / Medium Density'
        WHEN 4 THEN 'High Density'
        WHEN 5 THEN 'Very High / Ultra-High Density'
        ELSE NULL
    END AS density_level
FROM ranked;

CREATE OR REPLACE VIEW marts.v_mapa_age_structure_2023 AS
SELECT
    seccion_id,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    geom,
    anio,
    average_age,
    age_group,
    age_group_label,
    age_color_key,
    total_poblacion,
    over_65_pct,
    under_30_pct,
    densidad,
    density_level
FROM marts.v_mapa_age_structure
WHERE anio = 2023;
