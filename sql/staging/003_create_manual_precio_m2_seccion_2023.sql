CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.manual_precio_m2_seccion_2023 (
    seccion_id text PRIMARY KEY,
    precio_m2_observado numeric(12, 2),
    fuente text,
    notas text,
    confidence_level text,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_manual_precio_m2_seccion_2023_seccion
        CHECK (seccion_id ~ '^[0-9]{10}$'),
    CONSTRAINT ck_manual_precio_m2_seccion_2023_confidence
        CHECK (
            confidence_level IS NULL
            OR confidence_level IN ('High', 'Medium', 'Low')
        ),
    CONSTRAINT ck_manual_precio_m2_seccion_2023_precio
        CHECK (precio_m2_observado IS NULL OR precio_m2_observado >= 0)
);

COMMENT ON TABLE staging.manual_precio_m2_seccion_2023 IS
    'Manual section-level observed market references for Mijas 2023. These values are aggregated references, not individual property appraisals.';

COMMENT ON COLUMN staging.manual_precio_m2_seccion_2023.precio_m2_observado IS
    'Observed market reference in EUR/m2 at section level. Not an exact estimated sale price and not an appraisal.';
