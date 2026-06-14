DROP MATERIALIZED VIEW IF EXISTS marts.mv_seccion_edad_media CASCADE;

CREATE MATERIALIZED VIEW marts.mv_seccion_edad_media AS
WITH cohortes AS (
    SELECT
        seccion_id,
        anio,
        edad_cohorte,
        poblacion,
        lower(trim(edad_cohorte)) AS edad_cohorte_norm
    FROM core.poblacion_edad
),
cohortes_representativas AS (
    SELECT
        seccion_id,
        anio,
        poblacion,
        CASE
            WHEN edad_cohorte_norm ~ '^[0-9]+\s*-\s*[0-9]+$'
            THEN (
                split_part(regexp_replace(edad_cohorte_norm, '\s+', '', 'g'), '-', 1)::numeric
                + split_part(regexp_replace(edad_cohorte_norm, '\s+', '', 'g'), '-', 2)::numeric
            ) / 2.0

            WHEN edad_cohorte_norm ~ '^[0-9]+\s*(\+|y\s*m[aá]s)$'
            THEN substring(edad_cohorte_norm FROM '^[0-9]+')::numeric + 2.5

            ELSE NULL
        END AS edad_representativa
    FROM cohortes
),
agg AS (
    SELECT
        seccion_id,
        anio,
        SUM(poblacion) AS total_poblacion,
        SUM(poblacion) FILTER (WHERE edad_representativa IS NOT NULL) AS poblacion_mapeada,
        SUM(edad_representativa * poblacion) FILTER (WHERE edad_representativa IS NOT NULL) AS edad_ponderada
    FROM cohortes_representativas
    GROUP BY seccion_id, anio
)
SELECT
    seccion_id,
    anio,
    ROUND(
        CASE
            WHEN poblacion_mapeada > 0 THEN edad_ponderada / poblacion_mapeada
            ELSE NULL
        END,
        6
    ) AS edad_media,
    total_poblacion,
    now() AS fecha_refresh
FROM agg;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_seccion_edad_media
    ON marts.mv_seccion_edad_media (seccion_id, anio);

CREATE INDEX IF NOT EXISTS ix_mv_seccion_edad_media_anio
    ON marts.mv_seccion_edad_media (anio);

CREATE INDEX IF NOT EXISTS ix_mv_seccion_edad_media_edad_media
    ON marts.mv_seccion_edad_media (edad_media);
