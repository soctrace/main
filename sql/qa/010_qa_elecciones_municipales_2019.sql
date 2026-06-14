SELECT COUNT(DISTINCT seccion_id) AS n_secciones_2019_resultados
FROM core.elecciones_mun_2019;

SELECT COUNT(*) AS n_candidaturas_2019
FROM core.candidatura
WHERE election_id = 4;

SELECT
    seccion_id,
    MAX(votos_validos) AS votos_validos,
    SUM(votos_partido) AS suma_votos_partido,
    MAX(votos_validos) - SUM(votos_partido) AS diff
FROM core.elecciones_mun_2019
GROUP BY seccion_id
ORDER BY seccion_id;

SELECT
    seccion_id,
    ROUND(SUM(pct_voto), 3) AS pct_sum
FROM core.elecciones_mun_2019
GROUP BY seccion_id
ORDER BY seccion_id;

SELECT h.seccion_id
FROM core.seccion_historica h
LEFT JOIN core.elecciones_mun_2019 e
  ON e.seccion_id = h.seccion_id
WHERE h.anio = 2019
GROUP BY h.seccion_id
HAVING COUNT(e.*) = 0
ORDER BY h.seccion_id;

SELECT e.seccion_id
FROM core.elecciones_mun_2019 e
LEFT JOIN core.seccion_historica h
  ON h.seccion_id = e.seccion_id
 AND h.anio = 2019
WHERE h.seccion_id IS NULL
GROUP BY e.seccion_id
ORDER BY e.seccion_id;

SELECT seccion_id, election_id, cod_candidatura, COUNT(*) AS n
FROM core.elecciones_mun_2019
GROUP BY seccion_id, election_id, cod_candidatura
HAVING COUNT(*) > 1;

SELECT anio, COUNT(*) AS n_sections
FROM marts.mv_electoral_behavior
WHERE anio IN (2019, 2023)
GROUP BY anio
ORDER BY anio;

SELECT DISTINCT anio, ST_SRID(geom) AS srid
FROM marts.mv_electoral_behavior
WHERE anio IN (2019, 2023)
ORDER BY anio, srid;
