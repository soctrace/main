CREATE TABLE IF NOT EXISTS core.seccion_historica (
    seccion_sk BIGSERIAL PRIMARY KEY,
    seccion_id TEXT NOT NULL,
    anio INT NOT NULL,

    cod_provincia CHAR(2) NOT NULL,
    cod_municipio CHAR(3) NOT NULL,
    cod_distrito CHAR(2) NOT NULL,
    cod_seccion CHAR(3) NOT NULL,

    geom geometry(MultiPolygon, 4326) NOT NULL,

    area_m2 NUMERIC,
    area_km2 NUMERIC,

    source_file TEXT,
    source_layer TEXT,
    loaded_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (seccion_id, anio)
);

CREATE INDEX IF NOT EXISTS idx_seccion_historica_anio
    ON core.seccion_historica (anio);

CREATE INDEX IF NOT EXISTS idx_seccion_historica_seccion_anio
    ON core.seccion_historica (seccion_id, anio);

CREATE INDEX IF NOT EXISTS idx_seccion_historica_geom
    ON core.seccion_historica
    USING GIST (geom);

COMMENT ON TABLE core.seccion_historica IS
    'Historical census/electoral sections by year. Does not replace core.seccion, which remains the current operative geography.';
