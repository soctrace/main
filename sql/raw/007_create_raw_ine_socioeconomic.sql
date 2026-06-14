CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.ine_nivel_estudios_2021_2024 (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    nivel_formacion_alcanzado TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.ine_ocupacion_2021_2024 (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    relacion_actividad TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.ine_actividad_2021_2023 (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    ocupacion TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.ine_rama_actividad_2021_2023 (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    actividad_economica TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.ine_sit_profesional_2021_2023 (
    provincias TEXT,
    municipios TEXT,
    secciones TEXT,
    sexo TEXT,
    situacion_profesional TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.ine_gini_p80p20_2015_2023 (
    municipios TEXT,
    distritos TEXT,
    secciones TEXT,
    indicador TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.ine_fuente_ingresos_2019_2023 (
    municipios TEXT,
    distritos TEXT,
    secciones TEXT,
    distribucion_fuente_ingresos TEXT,
    periodo TEXT,
    total TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP DEFAULT NOW()
);
