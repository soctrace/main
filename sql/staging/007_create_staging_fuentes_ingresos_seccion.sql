CREATE TABLE IF NOT EXISTS staging.fuentes_ingresos_seccion (
    seccion_id TEXT,
    anio INTEGER,
    indicador_original TEXT,
    indicador_norm TEXT,
    valor NUMERIC(14, 2),
    unidad TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stg_fuentes_ingresos_seccion_anio
    ON staging.fuentes_ingresos_seccion (seccion_id, anio);

CREATE INDEX IF NOT EXISTS idx_stg_fuentes_ingresos_indicador
    ON staging.fuentes_ingresos_seccion (indicador_norm);
