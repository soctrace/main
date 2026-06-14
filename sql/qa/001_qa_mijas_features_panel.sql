-- 1. Número total de filas
SELECT COUNT(*) AS total_filas
FROM marts.mijas_features_panel;

-- 2. Duplicados por clave de grano
SELECT
    seccion_id,
    anio,
    election_id,
    COUNT(*) AS n
FROM marts.mijas_features_panel
GROUP BY seccion_id, anio, election_id
HAVING COUNT(*) > 1;

-- 3. Nulls en claves principales
SELECT
    seccion_id,
    anio,
    election_id
FROM marts.mijas_features_panel
WHERE seccion_id IS NULL
   OR anio IS NULL
   OR election_id IS NULL;

-- 4. Métricas electorales fuera de rango [0, 1]
SELECT
    seccion_id,
    anio,
    election_id,
    participacion,
    blanco_pct,
    nulos_pct,
    pct_pp,
    pct_psoe,
    pct_vox
FROM marts.mijas_features_panel
WHERE participacion < 0
   OR participacion > 1
   OR blanco_pct < 0 OR blanco_pct > 1
   OR nulos_pct < 0 OR nulos_pct > 1
   OR pct_pp < 0 OR pct_pp > 1
   OR pct_psoe < 0 OR pct_psoe > 1
   OR pct_vox < 0 OR pct_vox > 1;

-- 5. Ratios demográficos fuera de rango [0, 1]
SELECT
    seccion_id,
    anio,
    election_id,
    pct_h,
    pct_m,
    pct_0_14,
    pct_15_29,
    pct_30_44,
    pct_45_64,
    pct_65p
FROM marts.mijas_features_panel
WHERE pct_h < 0 OR pct_h > 1
   OR pct_m < 0 OR pct_m > 1
   OR pct_0_14 < 0 OR pct_0_14 > 1
   OR pct_15_29 < 0 OR pct_15_29 > 1
   OR pct_30_44 < 0 OR pct_30_44 > 1
   OR pct_45_64 < 0 OR pct_45_64 > 1
   OR pct_65p < 0 OR pct_65p > 1;

-- 6. Coherencia simple de población total vs sexo
SELECT
    seccion_id,
    anio,
    election_id,
    pob_total,
    pob_h,
    pob_m,
    (pob_h + pob_m) AS suma_h_m
FROM marts.mijas_features_panel
WHERE pob_total <> (pob_h + pob_m);

-- 7. Coherencia simple de voto emitido
SELECT
    seccion_id,
    anio,
    election_id,
    votos_emitidos,
    votos_validos,
    votos_blanco,
    votos_nulos,
    (votos_validos + votos_blanco + votos_nulos) AS votos_emitidos_recalculado
FROM marts.mijas_features_panel
WHERE votos_emitidos <> (votos_validos + votos_blanco + votos_nulos);

-- 8. Coherencia aproximada de distribución por sexo (redondeo permitido)
SELECT
    seccion_id,
    anio,
    election_id,
    pct_h,
    pct_m,
    (pct_h + pct_m) AS pct_h_m_suma
FROM marts.mijas_features_panel
WHERE ABS((pct_h + pct_m) - 1.0) > 0.002;

-- 9. Coherencia aproximada de distribución por edad (redondeo permitido)
SELECT
    seccion_id,
    anio,
    election_id,
    pct_0_14,
    pct_15_29,
    pct_30_44,
    pct_45_64,
    pct_65p,
    (pct_0_14 + pct_15_29 + pct_30_44 + pct_45_64 + pct_65p) AS pct_edad_suma
FROM marts.mijas_features_panel
WHERE ABS((pct_0_14 + pct_15_29 + pct_30_44 + pct_45_64 + pct_65p) - 1.0) > 0.01;

-- 10. Cobertura por año y elección
SELECT
    anio,
    election_id,
    COUNT(*) AS n_filas
FROM marts.mijas_features_panel
GROUP BY anio, election_id
ORDER BY anio, election_id;
