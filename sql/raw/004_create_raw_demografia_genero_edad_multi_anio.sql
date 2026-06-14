CREATE TABLE IF NOT EXISTS raw.demografia_genero_edad_multi_anio (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    edad TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);
