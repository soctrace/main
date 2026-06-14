CREATE TABLE IF NOT EXISTS core.poblacion_edad (
    seccion_id      text NOT NULL,
    anio            integer NOT NULL,
    genero          text NOT NULL,
    edad_cohorte    text NOT NULL,
    poblacion       integer NOT NULL,

    PRIMARY KEY (seccion_id, anio, genero, edad_cohorte)
);