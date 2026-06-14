CREATE TABLE IF NOT EXISTS core.elecciones_mun_2019 (
    seccion_id TEXT NOT NULL,
    anio INT NOT NULL,
    election_id BIGINT NOT NULL,
    cod_candidatura CHAR(6) NOT NULL,
    partido TEXT,
    votos_partido INT NOT NULL,
    votos_validos INT,
    votos_emitidos INT,
    votos_blanco INT,
    votos_nulos INT,
    censo INT,
    pct_voto NUMERIC,

    PRIMARY KEY (seccion_id, election_id, cod_candidatura)
);

CREATE INDEX IF NOT EXISTS idx_elecciones_mun_2019_seccion
    ON core.elecciones_mun_2019 (seccion_id);

CREATE INDEX IF NOT EXISTS idx_elecciones_mun_2019_party
    ON core.elecciones_mun_2019 (partido);
