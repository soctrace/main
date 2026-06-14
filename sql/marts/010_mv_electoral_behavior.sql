CREATE SCHEMA IF NOT EXISTS marts;

DROP MATERIALIZED VIEW IF EXISTS marts.mv_electoral_behavior CASCADE;

CREATE MATERIALIZED VIEW marts.mv_electoral_behavior AS
WITH base AS (
    SELECT
        r.election_id,
        e.tipo_eleccion_code,
        COALESCE(e.tipo_eleccion_nombre, et.descripcion) AS tipo_eleccion_nombre,
        e.anio,
        e.mes,
        e.election_date,
        r.seccion_id,
        r.cod_candidatura,
        r.siglas,
        COALESCE(a.normalized_party_family, 'OTHER') AS normalized_party_family,
        COALESCE(a.ideological_bloc, 'OTHER') AS ideological_bloc,
        COALESCE(a.is_local_party, false) AS is_local_party,
        COALESCE(r.votos_partido, 0)::bigint AS votos_partido,
        COALESCE(r.votos_validos, 0)::bigint AS votos_validos,
        COALESCE(r.votos_emitidos, 0)::bigint AS votos_emitidos,
        COALESCE(r.censo, 0)::bigint AS censo,
        COALESCE(r.pct_voto, 0)::numeric AS pct_voto
    FROM core.resultados_seccion r
    JOIN core.election e
      ON e.election_id = r.election_id
    LEFT JOIN core.election_type et
      ON et.tipo_eleccion_code = e.tipo_eleccion_code
    LEFT JOIN core.candidatura_alias a
      ON a.election_id = r.election_id
     AND a.cod_candidatura = r.cod_candidatura
),
ranked AS (
    SELECT
        b.*,
        ROW_NUMBER() OVER (
            PARTITION BY b.election_id, b.seccion_id
            ORDER BY b.pct_voto DESC, b.votos_partido DESC, b.siglas
        ) AS party_rank
    FROM base b
),
section_metrics AS (
    SELECT
        election_id,
        MAX(tipo_eleccion_code) AS tipo_eleccion_code,
        MAX(tipo_eleccion_nombre) AS tipo_eleccion_nombre,
        MAX(anio) AS anio,
        MAX(mes) AS mes,
        MAX(election_date) AS election_date,
        seccion_id,
        MAX(siglas) FILTER (WHERE party_rank = 1) AS winning_party,
        MAX(normalized_party_family) FILTER (WHERE party_rank = 1) AS winning_party_family,
        MAX(pct_voto) FILTER (WHERE party_rank = 1) AS winning_party_pct_ratio,
        MAX(siglas) FILTER (WHERE party_rank = 2) AS runner_up_party,
        MAX(pct_voto) FILTER (WHERE party_rank = 2) AS runner_up_pct_ratio,
        MAX(votos_validos) AS votos_validos,
        MAX(votos_emitidos) AS votos_emitidos,
        MAX(censo) AS censo,
        COUNT(*) FILTER (WHERE pct_voto >= 0.05) AS competitive_parties_count,
        ROUND(SUM(POWER(pct_voto, 2)), 6) AS vote_concentration_index,
        ROUND(1 - SUM(POWER(pct_voto, 2)), 6) AS fragmentation_index,
        COALESCE(SUM(pct_voto) FILTER (WHERE is_local_party), 0) AS local_vote_pct_ratio,
        COALESCE(SUM(pct_voto) FILTER (
            WHERE NOT is_local_party
              AND ideological_bloc IN ('LEFT', 'RIGHT', 'CENTER', 'GREEN', 'OTHER')
        ), 0) AS national_vote_pct_ratio,
        COALESCE(SUM(pct_voto) FILTER (WHERE ideological_bloc = 'LEFT'), 0) AS left_bloc_pct_ratio,
        COALESCE(SUM(pct_voto) FILTER (WHERE ideological_bloc = 'RIGHT'), 0) AS right_bloc_pct_ratio,
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'party', siglas,
                'votes', votos_partido,
                'pct', ROUND(pct_voto, 6),
                'normalized_party_family', normalized_party_family,
                'ideological_bloc', ideological_bloc
            )
            ORDER BY pct_voto DESC, votos_partido DESC, siglas
        ) AS party_results_json
    FROM ranked
    GROUP BY election_id, seccion_id
)
SELECT
    sm.election_id,
    sm.tipo_eleccion_code,
    sm.tipo_eleccion_nombre,
    sm.anio,
    sm.mes,
    sm.election_date,
    sm.seccion_id,
    g.geom,
    CASE
        WHEN g.geom IS NOT NULL
        THEN ST_AsGeoJSON(ST_Transform(ST_Force2D(g.geom), 4326))::jsonb
        ELSE NULL
    END AS geojson,
    sm.winning_party,
    sm.winning_party_family,
    ROUND(sm.winning_party_pct_ratio * 100, 6) AS winning_party_pct,
    sm.runner_up_party,
    ROUND(sm.runner_up_pct_ratio * 100, 6) AS runner_up_pct,
    ROUND(GREATEST(COALESCE(sm.winning_party_pct_ratio, 0) - COALESCE(sm.runner_up_pct_ratio, 0), 0) * 100, 6) AS victory_margin_pct,
    sm.votos_validos,
    sm.votos_emitidos,
    sm.censo,
    ROUND(sm.votos_emitidos::numeric / NULLIF(sm.censo, 0), 6) AS participacion,
    ROUND(sm.local_vote_pct_ratio * 100, 6) AS local_vote_pct,
    ROUND(sm.national_vote_pct_ratio * 100, 6) AS national_vote_pct,
    ROUND(sm.left_bloc_pct_ratio * 100, 6) AS left_bloc_pct,
    ROUND(sm.right_bloc_pct_ratio * 100, 6) AS right_bloc_pct,
    sm.fragmentation_index,
    sm.competitive_parties_count,
    sm.vote_concentration_index,
    ROUND(sm.local_vote_pct_ratio * 100, 6) AS localism_index,
    CASE
        WHEN sm.local_vote_pct_ratio * 100 < 10 THEN 'Low'
        WHEN sm.local_vote_pct_ratio * 100 < 20 THEN 'Moderate'
        WHEN sm.local_vote_pct_ratio * 100 < 30 THEN 'High'
        ELSE 'Very High'
    END AS localism_category,
    sm.party_results_json
FROM section_metrics sm
LEFT JOIN marts.v_mapa_seccion_anio g
  ON g.seccion_id = sm.seccion_id
 AND g.anio = sm.anio;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_electoral_behavior_election_seccion
    ON marts.mv_electoral_behavior (election_id, seccion_id);

CREATE INDEX IF NOT EXISTS idx_mv_electoral_behavior_tipo_anio_mes
    ON marts.mv_electoral_behavior (tipo_eleccion_code, anio, mes);

CREATE INDEX IF NOT EXISTS idx_mv_electoral_behavior_winner
    ON marts.mv_electoral_behavior (winning_party);

CREATE INDEX IF NOT EXISTS idx_mv_electoral_behavior_geom
    ON marts.mv_electoral_behavior
    USING GIST (geom);
