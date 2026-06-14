CREATE OR REPLACE VIEW marts.v_poblacion_seccion_anio AS
WITH base AS (
    SELECT
        CASE
            -- INE 2021 carries Mijas sections 06 and 21 under the opposite
            -- stable dashboard identity. Normalize before aggregation so
            -- maps, detail cards and temporal charts use section_id as key.
            WHEN anio = 2021 AND seccion_id = '2907001006' THEN '2907001021'
            WHEN anio = 2021 AND seccion_id = '2907001021' THEN '2907001006'
            ELSE seccion_id
        END AS seccion_id,
        anio,
        genero,
        edad_cohorte,
        poblacion
    FROM core.poblacion_edad
),
agg AS (
    SELECT
        seccion_id,
        anio,

        SUM(poblacion) AS pob_total,

        SUM(CASE WHEN genero = 'H' THEN poblacion ELSE 0 END) AS pob_h,
        SUM(CASE WHEN genero = 'M' THEN poblacion ELSE 0 END) AS pob_m,

        SUM(CASE WHEN edad_cohorte IN ('0-4', '5-9', '10-14', '15-19') THEN poblacion ELSE 0 END) AS pob_0_19,

        SUM(CASE WHEN edad_cohorte IN ('0-4', '5-9', '10-14') THEN poblacion ELSE 0 END) AS pob_0_14,
        SUM(CASE WHEN edad_cohorte IN ('15-19', '20-24', '25-29') THEN poblacion ELSE 0 END) AS pob_15_29,
        SUM(CASE WHEN edad_cohorte IN ('30-34', '35-39', '40-44') THEN poblacion ELSE 0 END) AS pob_30_44,
        SUM(CASE WHEN edad_cohorte IN ('45-49', '50-54', '55-59', '60-64') THEN poblacion ELSE 0 END) AS pob_45_64,
        SUM(CASE WHEN edad_cohorte IN ('65-69', '70-74', '75-79', '80-84', '85-89', '90-94', '95-99', '100+', '85 y más', '85+') THEN poblacion ELSE 0 END) AS pob_65p

    FROM base
    GROUP BY seccion_id, anio
)
SELECT
    seccion_id,
    anio,
    pob_total,
    pob_h,
    pob_m,

    ROUND(CASE WHEN pob_total > 0 THEN pob_h::numeric / pob_total ELSE NULL END, 6) AS pct_h,
    ROUND(CASE WHEN pob_total > 0 THEN pob_m::numeric / pob_total ELSE NULL END, 6) AS pct_m,

    pob_0_19,
    pob_0_14,
    pob_15_29,
    pob_30_44,
    pob_45_64,
    pob_65p,

    ROUND(CASE WHEN pob_total > 0 THEN pob_0_14::numeric / pob_total ELSE NULL END, 6) AS pct_0_14,
    ROUND(CASE WHEN pob_total > 0 THEN pob_15_29::numeric / pob_total ELSE NULL END, 6) AS pct_15_29,
    ROUND(CASE WHEN pob_total > 0 THEN pob_30_44::numeric / pob_total ELSE NULL END, 6) AS pct_30_44,
    ROUND(CASE WHEN pob_total > 0 THEN pob_45_64::numeric / pob_total ELSE NULL END, 6) AS pct_45_64,
    ROUND(CASE WHEN pob_total > 0 THEN pob_65p::numeric / pob_total ELSE NULL END, 6) AS pct_65p,

    ROUND(
        CASE
            WHEN pob_15_29 + pob_30_44 + pob_45_64 > 0
            THEN (pob_0_14 + pob_65p)::numeric / (pob_15_29 + pob_30_44 + pob_45_64)
            ELSE NULL
        END,
        6
    ) AS dependency_ratio

FROM agg;
