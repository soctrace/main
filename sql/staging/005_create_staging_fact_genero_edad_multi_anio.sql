CREATE TABLE IF NOT EXISTS staging.fact_genero_edad_multi_anio (
    seccion_id TEXT,
    anio INTEGER,
    genero TEXT,
    edad_cohorte TEXT,
    poblacion INTEGER,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_genero_edad_multi_anio_seccion_anio
    ON staging.fact_genero_edad_multi_anio (seccion_id, anio);
