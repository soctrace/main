CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.socioeconomic_indicator_catalog (
    domain TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    category_code TEXT NOT NULL,
    indicator_label TEXT,
    category_label TEXT,
    value_type TEXT,
    unit TEXT,
    sort_order INT,
    is_synthetic BOOLEAN DEFAULT FALSE,
    description TEXT,
    PRIMARY KEY (domain, indicator_code, category_code)
);

CREATE TABLE IF NOT EXISTS core.socioeconomic_indicator_section (
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
    fuente TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (
        seccion_id,
        anio,
        domain,
        indicator_code,
        category_code
    )
);

CREATE INDEX IF NOT EXISTS idx_socioeconomic_section_anio
ON core.socioeconomic_indicator_section (seccion_id, anio);

CREATE INDEX IF NOT EXISTS idx_socioeconomic_domain_anio
ON core.socioeconomic_indicator_section (domain, anio);

CREATE INDEX IF NOT EXISTS idx_socioeconomic_indicator
ON core.socioeconomic_indicator_section (domain, indicator_code, category_code);
