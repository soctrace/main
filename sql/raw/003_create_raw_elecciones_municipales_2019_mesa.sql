CREATE TABLE IF NOT EXISTS raw.elecciones_municipales_2019_mesa (
    raw_sk BIGSERIAL PRIMARY KEY,
    record_type TEXT NOT NULL,
    raw_line TEXT NOT NULL,

    tipo_eleccion TEXT,
    anio INT,
    mes INT,
    num_vuelta INT,
    cod_comunidad TEXT,
    cod_provincia TEXT,
    cod_municipio TEXT,
    cod_distrito TEXT,
    cod_seccion_raw TEXT,
    cod_seccion TEXT,
    cod_mesa TEXT,
    seccion_id TEXT,

    cod_candidatura TEXT,
    siglas_originales TEXT,
    denominacion_original TEXT,
    cod_cab_prov TEXT,
    cod_cab_auto TEXT,
    cod_cab_nac TEXT,

    censo_ine INT,
    censo_escrutinio INT,
    censo_cere INT,
    votantes_cere INT,
    votantes_avance1 INT,
    votantes_avance2 INT,
    votos_blanco INT,
    votos_nulos INT,
    votos_candidaturas INT,
    votos_ref_si INT,
    votos_ref_no INT,
    votos INT,
    datos_oficiales TEXT,

    source_file TEXT NOT NULL,
    source_encoding TEXT DEFAULT 'cp1252',
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_elecciones_mun_2019_mesa_record
    ON raw.elecciones_municipales_2019_mesa (record_type);

CREATE INDEX IF NOT EXISTS idx_raw_elecciones_mun_2019_mesa_section
    ON raw.elecciones_municipales_2019_mesa (seccion_id);
