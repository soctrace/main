SELECT COUNT(*) AS n_secciones_2019
FROM core.seccion_historica
WHERE anio = 2019;

SELECT
    seccion_id,
    cod_distrito,
    cod_seccion,
    ROUND(area_km2::numeric, 4) AS area_km2
FROM core.seccion_historica
WHERE anio = 2019
ORDER BY seccion_id;

SELECT DISTINCT ST_SRID(geom) AS srid
FROM core.seccion_historica
WHERE anio = 2019;

SELECT COUNT(*) AS invalid_geometries
FROM core.seccion_historica
WHERE anio = 2019
  AND NOT ST_IsValid(geom);

SELECT COUNT(*) AS empty_geometries
FROM core.seccion_historica
WHERE anio = 2019
  AND ST_IsEmpty(geom);

SELECT seccion_id, anio, COUNT(*) AS n
FROM core.seccion_historica
WHERE anio = 2019
GROUP BY seccion_id, anio
HAVING COUNT(*) > 1;

SELECT
    '2019' AS anio,
    COUNT(*) AS num_secciones
FROM core.seccion_historica
WHERE anio = 2019

UNION ALL

SELECT
    '2023' AS anio,
    COUNT(*) AS num_secciones
FROM core.seccion;
