CREATE TABLE IF NOT EXISTS staging.renta_seccion_multi_anio (
    seccion_id TEXT,
    anio INTEGER,
    indicador_norm TEXT,
    valor NUMERIC(12, 2),
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_renta_seccion_multi_anio_seccion_anio
    ON staging.renta_seccion_multi_anio (seccion_id, anio);

CREATE INDEX IF NOT EXISTS idx_renta_seccion_multi_anio_indicador
    ON staging.renta_seccion_multi_anio (indicador_norm);
