CREATE OR REPLACE VIEW marts.v_income_level AS
WITH ranked AS (
    SELECT
        r.seccion_id,
        r.anio,
        r.renta_media_persona,
        r.renta_media_hogar,
        NTILE(5) OVER (
            PARTITION BY r.anio
            ORDER BY r.renta_media_persona
        ) AS income_quintile,
        RANK() OVER (
            PARTITION BY r.anio
            ORDER BY r.renta_media_persona DESC
        ) AS income_rank_municipal,
        MIN(r.renta_media_persona) OVER (PARTITION BY r.anio) AS min_renta_media_persona,
        MAX(r.renta_media_persona) OVER (PARTITION BY r.anio) AS max_renta_media_persona
    FROM core.renta_seccion r
)
SELECT
    seccion_id,
    anio,
    renta_media_persona,
    renta_media_hogar,
    income_quintile,
    CASE income_quintile
        WHEN 1 THEN 'Very Low Income'
        WHEN 2 THEN 'Low Income'
        WHEN 3 THEN 'Medium Income'
        WHEN 4 THEN 'High Income'
        WHEN 5 THEN 'Very High Income'
    END AS income_level,
    income_rank_municipal,
    ROUND(
        100 * (
            renta_media_persona - min_renta_media_persona
        ) / NULLIF(
            max_renta_media_persona - min_renta_media_persona,
            0
        ),
        2
    ) AS income_index
FROM ranked;

CREATE OR REPLACE VIEW marts.v_income_level_layer AS
SELECT
    i.seccion_id,
    i.anio,
    g.seccion_numero_visible,
    g.nombre_barrio,
    g.zona_macro,
    g.label_cliente,
    g.area_m2,
    g.area_km2,
    g.geom,
    g.geom_json,
    i.renta_media_persona,
    i.renta_media_hogar,
    i.income_quintile,
    i.income_level,
    i.income_rank_municipal,
    i.income_index
FROM marts.v_income_level i
JOIN marts.v_mapa_seccion_anio g
  ON g.seccion_id = i.seccion_id
 AND g.anio = i.anio;
