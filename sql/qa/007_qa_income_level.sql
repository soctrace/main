-- 1. Número de secciones con renta 2023
SELECT COUNT(*) AS n_secciones_2023
FROM core.renta_seccion
WHERE anio = 2023;

-- 2. Nulos en métricas core
SELECT *
FROM core.renta_seccion
WHERE anio = 2023
  AND (
      renta_media_persona IS NULL
   OR renta_media_hogar IS NULL
  );

-- 3. Cobertura contra core.seccion para Mijas
WITH secciones_core AS (
    SELECT
        LPAD(s.cod_provincia::text, 2, '0')
            || LPAD(s.cod_municipio::text, 3, '0')
            || LPAD(s.cod_distrito::text, 2, '0')
            || s.cod_seccion AS seccion_id
    FROM core.seccion s
    WHERE LPAD(s.cod_provincia::text, 2, '0')
        || LPAD(s.cod_municipio::text, 3, '0') = '29070'
)
SELECT s.seccion_id
FROM secciones_core s
LEFT JOIN core.renta_seccion r
  ON s.seccion_id = r.seccion_id
 AND r.anio = 2023
WHERE r.seccion_id IS NULL;

-- 4. Rangos razonables
SELECT
    MIN(renta_media_persona) AS min_renta_media_persona,
    MAX(renta_media_persona) AS max_renta_media_persona,
    MIN(renta_media_hogar) AS min_renta_media_hogar,
    MAX(renta_media_hogar) AS max_renta_media_hogar
FROM core.renta_seccion
WHERE anio = 2023;

-- 5. Contrato dashboard
SELECT
    seccion_id,
    anio,
    renta_media_persona,
    renta_media_hogar,
    income_level,
    income_quintile,
    income_index,
    income_rank_municipal
FROM marts.v_income_level
WHERE anio = 2023
ORDER BY income_rank_municipal;
