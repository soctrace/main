CREATE TABLE IF NOT EXISTS core.renta_seccion (
    seccion_id              text NOT NULL,
    anio                    integer NOT NULL,
    renta_media_persona     numeric(12, 2),
    renta_media_hogar       numeric(12, 2),
    fuente                  text,
    updated_at              timestamp default now(),

    PRIMARY KEY (seccion_id, anio)
);

CREATE INDEX IF NOT EXISTS idx_renta_seccion_anio
    ON core.renta_seccion (anio);

CREATE INDEX IF NOT EXISTS idx_renta_seccion_seccion_anio
    ON core.renta_seccion (seccion_id, anio);
