DROP VIEW IF EXISTS marts.v_mapa_seccion_2023 CASCADE;

CREATE VIEW marts.v_mapa_seccion_2023 AS
WITH geo AS (
    SELECT
        LPAD(s.cod_provincia::text, 2, '0')
            || LPAD(s.cod_municipio::text, 3, '0')
            || LPAD(s.cod_distrito::text, 2, '0')
            || s.cod_seccion AS seccion_id,
        s.geom
    FROM core.seccion s
),
display_data AS (
    SELECT
        g.seccion_id,
        g.geom,
        COALESCE(
            d.seccion_numero_visible,
            LPAD((RIGHT(g.seccion_id, 3)::int)::text, 2, '0')
        ) AS seccion_numero_visible,
        NULLIF(d.nombre_barrio, '') AS nombre_barrio,
        NULLIF(d.zona_macro, '') AS zona_macro,
        d.label_cliente AS label_cliente_raw
    FROM geo g
    LEFT JOIN marts.dim_seccion_display d
      ON d.seccion_id = g.seccion_id
)
SELECT
    dd.seccion_id,
    dd.seccion_numero_visible,
    dd.nombre_barrio,
    dd.zona_macro,
    COALESCE(
        NULLIF(dd.label_cliente_raw, ''),
        CASE
            WHEN dd.nombre_barrio IS NOT NULL
            THEN 'Sección ' || dd.seccion_numero_visible || ' · ' || dd.nombre_barrio
            ELSE 'Sección ' || dd.seccion_numero_visible
        END
    ) AS label_cliente,
    dd.geom,
    ST_AsGeoJSON(dd.geom) AS geom_json
FROM display_data dd;
