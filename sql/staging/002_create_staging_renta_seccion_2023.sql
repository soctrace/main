CREATE TABLE IF NOT EXISTS staging.renta_seccion_2023 (
    seccion_id  text,
    anio        integer,
    indicador   text,
    valor       numeric(12, 2),
    fuente      text,
    loaded_at   timestamp default now()
);
