CREATE TABLE IF NOT EXISTS raw.fuentes_ingresos_2019_2023 (
    municipios TEXT,
    distritos TEXT,
    secciones TEXT,
    distribucion_fuente_ingresos TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);
