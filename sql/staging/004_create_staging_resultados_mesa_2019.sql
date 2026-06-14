CREATE TABLE IF NOT EXISTS staging.resultados_mesa_2019 (
    election_id BIGINT NOT NULL,
    anio INT NOT NULL,

    cod_provincia SMALLINT NOT NULL,
    cod_municipio SMALLINT NOT NULL,
    cod_distrito SMALLINT NOT NULL,
    cod_seccion CHAR(3) NOT NULL,
    cod_mesa CHAR(1) NOT NULL,
    seccion_id TEXT NOT NULL,

    cod_candidatura CHAR(6) NOT NULL,
    siglas_originales TEXT,
    votos INT NOT NULL,

    censo INT,
    votos_emitidos INT,
    votos_validos INT,
    votos_blanco INT,
    votos_nulos INT,

    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (election_id, cod_provincia, cod_municipio, cod_distrito, cod_seccion, cod_mesa, cod_candidatura)
);

CREATE INDEX IF NOT EXISTS idx_staging_resultados_mesa_2019_section
    ON staging.resultados_mesa_2019 (seccion_id);
