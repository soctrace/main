DROP MATERIALIZED VIEW IF EXISTS marts.mijas_features_panel CASCADE;

CREATE MATERIALIZED VIEW marts.mijas_features_panel AS
WITH base AS (
    SELECT
        p.seccion_id,
        p.anio,
        r.election_id,
        g.area_m2,
        g.area_km2,
        p.pob_total,
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
        p.dependency_ratio,
        r.censo,
        r.votos_emitidos,
        r.votos_validos,
        r.votos_blanco,
        r.votos_nulos,
        r.participacion,
        r.blanco_pct,
        r.nulos_pct,
        r.cod_candidatura_ganadora,
        r.sigla_ganadora,
        r.votos_ganador,
        r.votos_pp,
        r.votos_psoe,
        r.votos_vox,
        r.pct_pp,
        r.pct_psoe,
        r.pct_vox,
        il.renta_media_persona,
        il.renta_media_hogar,
        il.income_quintile,
        il.income_level,
        il.income_rank_municipal,
        il.income_index
    FROM marts.v_poblacion_seccion_anio p
    LEFT JOIN marts.v_resultados_seccion_anio r
      ON r.seccion_id = p.seccion_id
     AND r.anio = p.anio
    LEFT JOIN marts.v_geografia_seccion g
      ON g.seccion_id = p.seccion_id
    LEFT JOIN marts.v_income_level il
      ON il.seccion_id = p.seccion_id
     AND il.anio = p.anio
    WHERE p.anio = 2023
)
SELECT
    b.seccion_id,
    b.anio,
    b.election_id,

    -- Geografía
    b.area_m2,
    b.area_km2,
    ROUND(
        CASE
            WHEN b.area_km2 > 0 THEN b.pob_total::numeric / b.area_km2::numeric
            ELSE NULL
        END,
        6
    ) AS densidad,

    -- Demografía
    b.pob_total,
    b.pob_h,
    b.pob_m,
    b.pct_h,
    b.pct_m,
    b.pob_0_19,
    b.pob_0_14,
    b.pob_15_29,
    b.pob_30_44,
    b.pob_45_64,
    b.pob_65p,
    b.pct_0_14,
    b.pct_15_29,
    b.pct_30_44,
    b.pct_45_64,
    b.pct_65p,
    b.dependency_ratio,

    -- Electorales
    b.censo,
    b.votos_emitidos,
    b.votos_validos,
    b.votos_blanco,
    b.votos_nulos,
    b.participacion,
    b.blanco_pct,
    b.nulos_pct,
    b.cod_candidatura_ganadora,
    b.sigla_ganadora,
    b.votos_ganador,
    b.votos_pp,
    b.votos_psoe,
    b.votos_vox,
    b.pct_pp,
    b.pct_psoe,
    b.pct_vox,

    -- Renta
    b.renta_media_persona,
    b.renta_media_hogar,
    b.income_quintile,
    b.income_level,
    b.income_rank_municipal,
    b.income_index,

    -- Ratios útiles
    ROUND(
        CASE
            WHEN b.pob_total > 0 THEN b.censo::numeric / b.pob_total
            ELSE NULL
        END,
        6
    ) AS ratio_censo_poblacion,

    ROUND(
        CASE
            WHEN b.pob_total > 0 THEN b.votos_emitidos::numeric / b.pob_total
            ELSE NULL
        END,
        6
    ) AS ratio_votantes_poblacion

FROM base b;
