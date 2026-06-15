-- soctrace MVP Supabase deployment: base core tables that some ETL loaders
-- used to create implicitly. Keep this file idempotent for PROD rebuilds.

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.election_type (
    tipo_eleccion_code TEXT PRIMARY KEY,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS core.election (
    election_id BIGSERIAL PRIMARY KEY,
    tipo_eleccion_code TEXT NOT NULL REFERENCES core.election_type(tipo_eleccion_code),
    tipo_eleccion_nombre TEXT,
    anio INT NOT NULL,
    mes INT,
    num_vuelta INT DEFAULT 1,
    election_date DATE,
    source_folder TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_core_election_type_year_month_round
    ON core.election (tipo_eleccion_code, anio, mes, COALESCE(num_vuelta, 1));

CREATE TABLE IF NOT EXISTS core.candidatura (
    election_id BIGINT NOT NULL REFERENCES core.election(election_id) ON DELETE CASCADE,
    cod_candidatura TEXT NOT NULL,
    siglas TEXT,
    denominacion TEXT,
    cod_cab_prov TEXT,
    cod_cab_auto TEXT,
    cod_cab_nac TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (election_id, cod_candidatura)
);

CREATE TABLE IF NOT EXISTS core.mesa (
    cod_provincia SMALLINT NOT NULL,
    cod_municipio SMALLINT NOT NULL,
    cod_distrito SMALLINT NOT NULL,
    cod_seccion CHAR(3) NOT NULL,
    cod_mesa CHAR(1) NOT NULL,
    PRIMARY KEY (cod_provincia, cod_municipio, cod_distrito, cod_seccion, cod_mesa)
);

CREATE TABLE IF NOT EXISTS core.datos_mesa (
    election_id BIGINT NOT NULL REFERENCES core.election(election_id) ON DELETE CASCADE,
    cod_provincia SMALLINT NOT NULL,
    cod_municipio SMALLINT NOT NULL,
    cod_distrito SMALLINT NOT NULL,
    cod_seccion CHAR(3) NOT NULL,
    cod_mesa CHAR(1) NOT NULL,
    seccion_id TEXT,
    censo_ine BIGINT,
    censo_escrutinio BIGINT,
    censo_cere BIGINT,
    votantes_cere BIGINT,
    votantes_avance1 BIGINT,
    votantes_avance2 BIGINT,
    votos_blanco BIGINT,
    votos_nulos BIGINT,
    votos_candidaturas BIGINT,
    votos_ref_si BIGINT,
    votos_ref_no BIGINT,
    datos_oficiales TEXT,
    censo BIGINT,
    votos_emitidos BIGINT,
    votos_validos BIGINT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (election_id, cod_provincia, cod_municipio, cod_distrito, cod_seccion, cod_mesa)
);

CREATE TABLE IF NOT EXISTS core.resultados_mesa (
    election_id BIGINT NOT NULL REFERENCES core.election(election_id) ON DELETE CASCADE,
    cod_provincia SMALLINT NOT NULL,
    cod_municipio SMALLINT NOT NULL,
    cod_distrito SMALLINT NOT NULL,
    cod_seccion CHAR(3) NOT NULL,
    cod_mesa CHAR(1) NOT NULL,
    seccion_id TEXT,
    cod_candidatura TEXT NOT NULL,
    votos BIGINT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (election_id, cod_provincia, cod_municipio, cod_distrito, cod_seccion, cod_mesa, cod_candidatura)
);

CREATE TABLE IF NOT EXISTS core.seccion (
    cod_provincia SMALLINT NOT NULL,
    cod_municipio SMALLINT NOT NULL,
    cod_distrito SMALLINT NOT NULL,
    cod_seccion CHAR(3) NOT NULL,
    geom geometry(MultiPolygon, 4326),
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (cod_provincia, cod_municipio, cod_distrito, cod_seccion)
);

CREATE INDEX IF NOT EXISTS idx_core_seccion_geom
    ON core.seccion USING GIST (geom);

INSERT INTO core.election_type (tipo_eleccion_code, descripcion)
VALUES
    ('CONGRESO', 'Elecciones al Congreso de los Diputados'),
    ('MUNICIPALES', 'Elecciones Municipales'),
    ('PARLAMENTO_EUROPEO', 'Elecciones al Parlamento Europeo'),
    ('ANDALUZAS', 'Elecciones Andaluzas'),
    ('04', 'Elecciones Municipales')
ON CONFLICT (tipo_eleccion_code) DO UPDATE
SET descripcion = EXCLUDED.descripcion;
