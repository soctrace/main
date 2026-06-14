DROP VIEW IF EXISTS marts.v_resultados_seccion_anio CASCADE;

CREATE VIEW marts.v_resultados_seccion_anio AS
WITH ranked AS (
    SELECT
        r.*,
        ROW_NUMBER() OVER (
            PARTITION BY r.election_id, r.seccion_id
            ORDER BY r.pct_voto DESC, r.votos_partido DESC, r.siglas
        ) AS rn
    FROM core.resultados_seccion r
    JOIN core.election e
      ON e.election_id = r.election_id
     AND e.tipo_eleccion_code = 'MUNICIPALES'
),
totales AS (
    SELECT DISTINCT
        r.election_id,
        r.seccion_id,
        r.anio,
        r.censo,
        r.votos_emitidos,
        r.votos_validos,
        r.votos_blanco,
        r.votos_nulos
    FROM core.resultados_seccion r
    JOIN core.election e
      ON e.election_id = r.election_id
     AND e.tipo_eleccion_code = 'MUNICIPALES'
),
votos_partido AS (
    SELECT
        r.election_id,
        r.seccion_id,
        SUM(r.votos_partido) FILTER (WHERE UPPER(COALESCE(a.normalized_party_family, r.siglas)) = 'PP') AS votos_pp,
        SUM(r.votos_partido) FILTER (WHERE UPPER(COALESCE(a.normalized_party_family, r.siglas)) = 'PSOE') AS votos_psoe,
        SUM(r.votos_partido) FILTER (WHERE UPPER(COALESCE(a.normalized_party_family, r.siglas)) = 'VOX') AS votos_vox
    FROM core.resultados_seccion r
    JOIN core.election e
      ON e.election_id = r.election_id
     AND e.tipo_eleccion_code = 'MUNICIPALES'
    LEFT JOIN core.candidatura_alias a
      ON a.election_id = r.election_id
     AND a.cod_candidatura = r.cod_candidatura
    GROUP BY r.election_id, r.seccion_id
)
SELECT
    t.seccion_id,
    t.anio,
    t.election_id,
    t.censo,
    t.votos_emitidos,
    t.votos_validos,
    t.votos_blanco,
    t.votos_nulos,
    ROUND(t.votos_emitidos::numeric / NULLIF(t.censo, 0), 6) AS participacion,
    ROUND(t.votos_blanco::numeric / NULLIF(t.votos_emitidos, 0), 6) AS blanco_pct,
    ROUND(t.votos_nulos::numeric / NULLIF(t.votos_emitidos, 0), 6) AS nulos_pct,
    g.cod_candidatura AS cod_candidatura_ganadora,
    g.siglas AS sigla_ganadora,
    g.votos_partido AS votos_ganador,
    COALESCE(vp.votos_pp, 0) AS votos_pp,
    COALESCE(vp.votos_psoe, 0) AS votos_psoe,
    COALESCE(vp.votos_vox, 0) AS votos_vox,
    ROUND(COALESCE(vp.votos_pp, 0)::numeric / NULLIF(t.votos_validos, 0), 6) AS pct_pp,
    ROUND(COALESCE(vp.votos_psoe, 0)::numeric / NULLIF(t.votos_validos, 0), 6) AS pct_psoe,
    ROUND(COALESCE(vp.votos_vox, 0)::numeric / NULLIF(t.votos_validos, 0), 6) AS pct_vox
FROM totales t
LEFT JOIN ranked g
  ON g.election_id = t.election_id
 AND g.seccion_id = t.seccion_id
 AND g.rn = 1
LEFT JOIN votos_partido vp
  ON vp.election_id = t.election_id
 AND vp.seccion_id = t.seccion_id;
