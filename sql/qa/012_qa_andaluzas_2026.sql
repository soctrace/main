-- QA for Mijas Andalusian regional election 2026 load.

\set ON_ERROR_STOP on

WITH target AS (
    SELECT election_id
    FROM core.election
    WHERE tipo_eleccion_code = 'ANDALUZAS'
      AND anio = 2026
      AND mes = 5
)
SELECT *
FROM core.election
WHERE election_id = (SELECT election_id FROM target);

WITH target AS (
    SELECT election_id
    FROM core.election
    WHERE tipo_eleccion_code = 'ANDALUZAS'
      AND anio = 2026
      AND mes = 5
)
SELECT COUNT(DISTINCT seccion_id) AS secciones_cargadas
FROM core.resultados_seccion
WHERE election_id = (SELECT election_id FROM target);

WITH target AS (
    SELECT election_id
    FROM core.election
    WHERE tipo_eleccion_code = 'ANDALUZAS'
      AND anio = 2026
      AND mes = 5
)
SELECT COUNT(DISTINCT cod_candidatura) AS candidaturas
FROM core.resultados_seccion
WHERE election_id = (SELECT election_id FROM target);

WITH target AS (
    SELECT election_id
    FROM core.election
    WHERE tipo_eleccion_code = 'ANDALUZAS'
      AND anio = 2026
      AND mes = 5
)
SELECT seccion_id, SUM(pct_voto) AS pct_sum
FROM core.resultados_seccion
WHERE election_id = (SELECT election_id FROM target)
GROUP BY seccion_id
HAVING SUM(pct_voto) < 0.98 OR SUM(pct_voto) > 1.02
ORDER BY seccion_id;

SELECT campo, total_secciones, total_municipio, diferencia, ok
FROM staging.andaluzas_2026_validation_mijas
ORDER BY ok, campo;

WITH target AS (
    SELECT election_id
    FROM core.election
    WHERE tipo_eleccion_code = 'ANDALUZAS'
      AND anio = 2026
      AND mes = 5
)
SELECT eb.seccion_id
FROM marts.mv_electoral_behavior eb
WHERE eb.election_id = (SELECT election_id FROM target)
  AND eb.geom IS NULL
ORDER BY eb.seccion_id;

WITH target AS (
    SELECT election_id
    FROM core.election
    WHERE tipo_eleccion_code = 'ANDALUZAS'
      AND anio = 2026
      AND mes = 5
)
SELECT
    election_id,
    COUNT(*) AS section_rows,
    COUNT(*) FILTER (WHERE party_results_json IS NOT NULL) AS rows_with_party_json,
    COUNT(*) FILTER (WHERE winning_party IS NOT NULL) AS rows_with_winner,
    COUNT(*) FILTER (WHERE geom IS NOT NULL) AS rows_with_geom
FROM marts.mv_electoral_behavior
WHERE election_id = (SELECT election_id FROM target)
GROUP BY election_id;
