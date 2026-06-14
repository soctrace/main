CREATE TABLE IF NOT EXISTS core.candidatura_alias (
    candidatura_alias_sk BIGSERIAL PRIMARY KEY,

    election_id INT NOT NULL,
    cod_candidatura TEXT NOT NULL,

    siglas_originales TEXT,
    denominacion_original TEXT,

    normalized_party_family TEXT,
    ideological_bloc TEXT,
    is_local_party BOOLEAN,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (election_id, cod_candidatura)
);

CREATE INDEX IF NOT EXISTS idx_candidatura_alias_family
    ON core.candidatura_alias (normalized_party_family);

CREATE INDEX IF NOT EXISTS idx_candidatura_alias_bloc
    ON core.candidatura_alias (ideological_bloc);

COMMENT ON TABLE core.candidatura_alias IS
    'Election-specific party normalization preserving original candidacy labels for analytical comparability.';
