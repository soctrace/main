CREATE SCHEMA IF NOT EXISTS marts;

DROP VIEW IF EXISTS marts.ml_electoral_section_panel CASCADE;

CREATE VIEW marts.ml_electoral_section_panel AS
SELECT
    election_id,
    tipo_eleccion_code,
    anio,
    mes,
    seccion_id,
    winning_party,
    winning_party_family,
    winning_party_pct,
    victory_margin_pct,
    participacion,
    fragmentation_index,
    vote_concentration_index,
    competitive_parties_count,
    left_bloc_pct,
    right_bloc_pct,
    local_vote_pct,
    national_vote_pct,
    censo,
    votos_validos
FROM marts.mv_electoral_behavior;
