CREATE OR REPLACE VIEW marts.v_population_layer AS
WITH joined AS (
    SELECT
        g.seccion_id,
        g.anio,
        g.seccion_numero_visible,
        g.nombre_barrio,
        g.zona_macro,
        g.label_cliente,
        g.area_m2,
        g.area_km2,
        g.geom,
        g.geom_json,
        p.pob_total,
        ROUND(p.pob_total::numeric / NULLIF(g.area_km2, 0), 6) AS densidad,
        p.pob_h,
        p.pob_m,
        p.pct_h,
        p.pct_m,
        p.pob_0_19,
        p.pob_0_14,
        p.pob_15_29,
        p.pob_30_44,
        p.pob_45_64,
        p.pob_65p,
        p.pct_0_14,
        p.pct_15_29,
        p.pct_30_44,
        p.pct_45_64,
        p.pct_65p,
        p.dependency_ratio
    FROM marts.v_mapa_seccion_anio g
    LEFT JOIN marts.v_poblacion_seccion_anio p
      ON p.seccion_id = g.seccion_id
     AND p.anio = g.anio
    WHERE g.anio IN (2021, 2022, 2023, 2024, 2025)
),
ranked AS (
    SELECT
        joined.*,
        CASE
            WHEN pob_total IS NULL THEN NULL
            ELSE NTILE(5) OVER (PARTITION BY anio ORDER BY pob_total)
        END AS population_quintile,
        CASE
            WHEN densidad IS NULL THEN NULL
            ELSE NTILE(5) OVER (PARTITION BY anio ORDER BY densidad)
        END AS density_quintile
    FROM joined
)
SELECT
    seccion_id,
    anio,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    area_m2,
    area_km2,
    geom,
    geom_json,
    pob_total,
    densidad,
    pob_h,
    pob_m,
    pct_h,
    pct_m,
    pob_0_19,
    pob_0_14,
    pob_15_29,
    pob_30_44,
    pob_45_64,
    pob_65p,
    pct_0_14,
    pct_15_29,
    pct_30_44,
    pct_45_64,
    pct_65p,
    dependency_ratio,
    population_quintile,
    density_quintile,
    CASE density_quintile
        WHEN 1 THEN 'Very Low Density'
        WHEN 2 THEN 'Low Density'
        WHEN 3 THEN 'Moderate / Medium Density'
        WHEN 4 THEN 'High Density'
        WHEN 5 THEN 'Very High / Ultra-High Density'
        ELSE NULL
    END AS density_level
FROM ranked;
