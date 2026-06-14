CREATE TABLE IF NOT EXISTS raw.renta_ine_2019_2023 (
    municipios TEXT,
    distritos TEXT,
    secciones TEXT,
    indicador TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);
