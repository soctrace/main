SELECT
    anio,
    COUNT(*) AS secciones
FROM core.seccion_historica
WHERE anio BETWEEN 2014 AND 2018
GROUP BY anio
ORDER BY anio;

SELECT
    anio,
    COUNT(*) FILTER (WHERE ST_SRID(geom) <> 4326) AS srid_not_4326,
    COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid_geom,
    COUNT(*) FILTER (WHERE ST_IsEmpty(geom)) AS empty_geom,
    MIN(area_km2) AS min_area_km2,
    MAX(area_km2) AS max_area_km2
FROM core.seccion_historica
WHERE anio BETWEEN 2014 AND 2018
GROUP BY anio
ORDER BY anio;

SELECT
    seccion_id,
    anio,
    COUNT(*) AS duplicates
FROM core.seccion_historica
WHERE anio BETWEEN 2014 AND 2018
GROUP BY seccion_id, anio
HAVING COUNT(*) > 1
ORDER BY anio, seccion_id;

SELECT
    election_id,
    tipo_eleccion_code,
    anio,
    mes,
    election_date
FROM core.election
ORDER BY anio, mes, tipo_eleccion_code;

SELECT *
FROM core.election
WHERE tipo_eleccion_code = 'ANDALUZAS'
  AND anio = 2018;

SELECT
    e.tipo_eleccion_code,
    e.anio,
    e.mes,
    COUNT(DISTINCT r.seccion_id) AS secciones
FROM core.resultados_seccion r
JOIN core.election e USING (election_id)
GROUP BY e.tipo_eleccion_code, e.anio, e.mes
ORDER BY e.anio, e.mes, e.tipo_eleccion_code;

SELECT
    e.tipo_eleccion_code,
    e.anio,
    e.mes,
    COUNT(DISTINCT r.cod_candidatura) AS candidaturas
FROM core.resultados_seccion r
JOIN core.election e USING (election_id)
GROUP BY e.tipo_eleccion_code, e.anio, e.mes
ORDER BY e.anio, e.mes, e.tipo_eleccion_code;

SELECT
    election_id,
    seccion_id,
    cod_candidatura,
    COUNT(*)
FROM core.resultados_seccion
GROUP BY election_id, seccion_id, cod_candidatura
HAVING COUNT(*) > 1;

SELECT
    election_id,
    seccion_id,
    SUM(pct_voto) AS suma_pct
FROM core.resultados_seccion
GROUP BY election_id, seccion_id
HAVING SUM(pct_voto) < 0.98
    OR SUM(pct_voto) > 1.02;

SELECT
    eb.election_id,
    eb.anio,
    eb.seccion_id
FROM marts.mv_electoral_behavior eb
WHERE eb.geom IS NULL
ORDER BY eb.anio, eb.election_id, eb.seccion_id;

SELECT
    c.election_id,
    c.cod_candidatura,
    c.siglas,
    c.denominacion
FROM core.candidatura c
LEFT JOIN core.candidatura_alias a
  ON c.election_id = a.election_id
 AND c.cod_candidatura::text = a.cod_candidatura
WHERE a.cod_candidatura IS NULL
ORDER BY c.election_id, c.siglas;

SELECT
    e.tipo_eleccion_code,
    e.anio,
    e.mes,
    a.siglas_originales,
    a.denominacion_original
FROM core.candidatura_alias a
JOIN core.election e USING (election_id)
WHERE a.normalized_party_family = 'OTHER'
ORDER BY e.anio, e.mes, a.siglas_originales;
