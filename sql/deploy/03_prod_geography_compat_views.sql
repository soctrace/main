-- soctrace MVP Supabase deployment: geography compatibility views.
-- These views avoid relying on legacy core.seccion population. The current
-- backend can serve map and municipality endpoints from core.seccion_historica.

CREATE SCHEMA IF NOT EXISTS marts;

CREATE OR REPLACE VIEW marts.v_geografia_seccion AS
WITH latest AS (
    SELECT DISTINCT ON (seccion_id)
        seccion_id,
        geom,
        area_m2,
        area_km2
    FROM core.seccion_historica
    WHERE geom IS NOT NULL
    ORDER BY seccion_id, anio DESC
)
SELECT
    seccion_id,
    COALESCE(area_m2, ST_Area(ST_Transform(geom, 25830)))::numeric AS area_m2,
    COALESCE(area_km2, ST_Area(ST_Transform(geom, 25830)) / 1000000.0)::numeric AS area_km2
FROM latest;

CREATE OR REPLACE VIEW marts.v_mapa_seccion_2023 AS
SELECT
    seccion_id,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    geom,
    geom_json
FROM marts.v_mapa_seccion_anio
WHERE anio = 2023;
