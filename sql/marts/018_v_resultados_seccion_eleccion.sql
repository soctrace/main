CREATE SCHEMA IF NOT EXISTS marts;

DROP VIEW IF EXISTS marts.v_resultados_seccion_eleccion CASCADE;

CREATE VIEW marts.v_resultados_seccion_eleccion AS
SELECT
    r.election_id,
    e.tipo_eleccion_code,
    COALESCE(e.tipo_eleccion_nombre, et.descripcion) AS tipo_eleccion_nombre,
    r.anio,
    r.mes,
    e.election_date,
    r.seccion_id,
    r.cod_candidatura,
    r.siglas,
    r.denominacion,
    COALESCE(a.normalized_party_family, 'OTHER') AS normalized_party_family,
    COALESCE(a.ideological_bloc, 'OTHER') AS ideological_bloc,
    COALESCE(a.is_local_party, false) AS is_local_party,
    r.votos_partido,
    r.votos_validos,
    r.votos_emitidos,
    r.censo,
    r.votos_blanco,
    r.votos_nulos,
    r.pct_voto
FROM core.resultados_seccion r
JOIN core.election e
  ON e.election_id = r.election_id
LEFT JOIN core.election_type et
  ON et.tipo_eleccion_code = e.tipo_eleccion_code
LEFT JOIN core.candidatura_alias a
  ON a.election_id = r.election_id
 AND a.cod_candidatura = r.cod_candidatura;
