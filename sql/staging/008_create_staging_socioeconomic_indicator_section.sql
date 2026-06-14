CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.socioeconomic_indicator_section (
    seccion_id TEXT NOT NULL,
    anio INT NOT NULL,
    domain TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    category_code TEXT NOT NULL,
    indicator_label TEXT,
    category_label TEXT,
    value NUMERIC(14,4),
    value_type TEXT,
    unit TEXT,
    source_file TEXT,
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_socioeconomic_section_anio
ON staging.socioeconomic_indicator_section (seccion_id, anio);

CREATE INDEX IF NOT EXISTS idx_staging_socioeconomic_domain_anio
ON staging.socioeconomic_indicator_section (domain, anio);
