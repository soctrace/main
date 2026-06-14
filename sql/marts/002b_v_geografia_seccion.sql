DROP VIEW IF EXISTS marts.v_geografia_seccion CASCADE;

CREATE VIEW marts.v_geografia_seccion AS
WITH base AS (
    SELECT
        LPAD(s.cod_provincia::text, 2, '0')
            || LPAD(s.cod_municipio::text, 3, '0')
            || LPAD(s.cod_distrito::text, 2, '0')
            || s.cod_seccion AS seccion_id,
        s.geom
    FROM core.seccion s
)
SELECT
    b.seccion_id,
    ST_Area(ST_Transform(b.geom, 25830))::numeric AS area_m2,
    (ST_Area(ST_Transform(b.geom, 25830)) / 1000000.0)::numeric AS area_km2
FROM base b;
