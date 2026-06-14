CREATE TABLE IF NOT EXISTS marts.dim_seccion_display (
    seccion_id text PRIMARY KEY,
    seccion_numero_visible text,
    nombre_barrio text,
    zona_macro text,
    label_cliente text,
    updated_at timestamp NOT NULL DEFAULT now()
);

ALTER TABLE marts.dim_seccion_display
    ADD COLUMN IF NOT EXISTS seccion_numero_visible text,
    ADD COLUMN IF NOT EXISTS nombre_barrio text,
    ADD COLUMN IF NOT EXISTS zona_macro text,
    ADD COLUMN IF NOT EXISTS label_cliente text,
    ADD COLUMN IF NOT EXISTS updated_at timestamp NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS ix_dim_seccion_display_label_cliente
    ON marts.dim_seccion_display (label_cliente);
