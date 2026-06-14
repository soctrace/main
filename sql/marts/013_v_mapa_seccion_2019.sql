CREATE OR REPLACE VIEW marts.v_mapa_seccion_2019 AS
SELECT
    h.seccion_id,
    h.anio,
    COALESCE(d.seccion_numero_visible, RIGHT(h.seccion_id, 3)) AS seccion_numero_visible,
    d.nombre_barrio,
    d.zona_macro,
    COALESCE(d.label_cliente, 'Mijas - Section ' || RIGHT(h.seccion_id, 3)) AS label_cliente,
    h.area_m2,
    h.area_km2,
    h.geom,
    ST_AsGeoJSON(h.geom)::json AS geom_json
FROM core.seccion_historica h
LEFT JOIN marts.dim_seccion_display d
  ON h.seccion_id = d.seccion_id
WHERE h.anio = 2019;
