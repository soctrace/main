CREATE TABLE IF NOT EXISTS raw.demografia_genero_edad_2023 (
    seccion_id      text,
    sexo            text,
    genero          text,
    edad_cohorte    text,
    periodo         text,
    poblacion       text,
    source_file     text,
    loaded_at       timestamp default now()
);