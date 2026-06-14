CREATE TABLE IF NOT EXISTS core.fuentes_ingresos_seccion (
    seccion_id TEXT NOT NULL,
    anio INTEGER NOT NULL,
    indicador_norm TEXT NOT NULL,
    indicador_original TEXT,
    valor NUMERIC(14, 2),
    unidad TEXT,
    fuente TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (seccion_id, anio, indicador_norm)
);

CREATE INDEX IF NOT EXISTS idx_fuentes_ingresos_anio
    ON core.fuentes_ingresos_seccion (anio);

CREATE INDEX IF NOT EXISTS idx_fuentes_ingresos_seccion
    ON core.fuentes_ingresos_seccion (seccion_id);

CREATE INDEX IF NOT EXISTS idx_fuentes_ingresos_indicador
    ON core.fuentes_ingresos_seccion (indicador_norm);
