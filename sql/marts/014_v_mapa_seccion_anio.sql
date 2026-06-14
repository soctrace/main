CREATE OR REPLACE VIEW marts.v_mapa_seccion_anio AS
WITH normalized AS (
    SELECT
        CASE
            -- In the 2021 geography source for Mijas, sections 06 and 21 are
            -- encoded with the opposite stable dashboard identity. Normalize
            -- the feature identity before joining display metadata so map
            -- clicks select the section represented by the clicked geometry.
            WHEN h.anio = 2021 AND h.seccion_id = '2907001006' THEN '2907001021'
            WHEN h.anio = 2021 AND h.seccion_id = '2907001021' THEN '2907001006'
            ELSE h.seccion_id
        END AS seccion_id,
        h.anio,
        h.area_m2,
        h.area_km2,
        h.geom
    FROM core.seccion_historica h
)
SELECT
    n.seccion_id,
    n.anio,
    COALESCE(d.seccion_numero_visible, RIGHT(n.seccion_id, 3)) AS seccion_numero_visible,
    d.nombre_barrio,
    d.zona_macro,
    COALESCE(d.label_cliente, 'Mijas - Section ' || RIGHT(n.seccion_id, 3)) AS label_cliente,
    n.area_m2,
    n.area_km2,
    n.geom,
    ST_AsGeoJSON(ST_Transform(ST_Force2D(n.geom), 4326))::json AS geom_json
FROM normalized n
LEFT JOIN marts.dim_seccion_display d
  ON n.seccion_id = d.seccion_id;
