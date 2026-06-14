SELECT 'core_rows_by_year' AS check_name, anio::text AS key, COUNT(*)::text AS value
FROM core.poblacion_edad
WHERE anio IN (2021, 2022, 2023, 2024, 2025)
GROUP BY anio
ORDER BY anio;

SELECT 'population_sections_by_year' AS check_name, anio::text AS key, COUNT(DISTINCT seccion_id)::text AS value
FROM core.poblacion_edad
WHERE anio IN (2021, 2022, 2023, 2024, 2025)
GROUP BY anio
ORDER BY anio;

SELECT 'geographic_sections_by_year' AS check_name, anio::text AS key, COUNT(*)::text AS value
FROM core.seccion_historica
WHERE anio IN (2020, 2021, 2022, 2023, 2024, 2025, 2026)
GROUP BY anio
ORDER BY anio;

SELECT 'population_without_geometry' AS check_name, p.anio::text AS key, p.seccion_id AS value
FROM marts.v_poblacion_seccion_anio p
LEFT JOIN core.seccion_historica h
  ON p.seccion_id = h.seccion_id
 AND p.anio = h.anio
WHERE p.anio IN (2021, 2022, 2023, 2024, 2025)
  AND h.seccion_id IS NULL
ORDER BY p.anio, p.seccion_id;

SELECT 'geometry_without_population' AS check_name, h.anio::text AS key, h.seccion_id AS value
FROM core.seccion_historica h
LEFT JOIN marts.v_poblacion_seccion_anio p
  ON h.seccion_id = p.seccion_id
 AND h.anio = p.anio
WHERE h.anio IN (2021, 2022, 2023, 2024, 2025)
  AND p.seccion_id IS NULL
ORDER BY h.anio, h.seccion_id;

SELECT 'core_duplicates' AS check_name,
       (seccion_id || ':' || anio || ':' || genero || ':' || edad_cohorte) AS key,
       COUNT(*)::text AS value
FROM core.poblacion_edad
GROUP BY seccion_id, anio, genero, edad_cohorte
HAVING COUNT(*) > 1;

SELECT 'invalid_geometries' AS check_name, anio::text AS key, COUNT(*)::text AS value
FROM core.seccion_historica
WHERE anio IN (2020, 2021, 2022, 2023, 2024, 2025, 2026)
  AND NOT ST_IsValid(geom)
GROUP BY anio
ORDER BY anio;

SELECT 'population_layer_sections_by_year' AS check_name, anio::text AS key, COUNT(*)::text AS value
FROM marts.v_population_layer
WHERE anio IN (2021, 2022, 2023, 2024, 2025)
GROUP BY anio
ORDER BY anio;
