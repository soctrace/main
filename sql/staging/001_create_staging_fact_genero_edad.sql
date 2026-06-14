CREATE TABLE IF NOT EXISTS staging.fact_genero_edad (
    seccion_id      text,
    sexo            text,
    genero          text,
    edad_cohorte    text,
    anio            integer,
    poblacion       integer,
    source_file     text,
    loaded_at       timestamp default now()
);