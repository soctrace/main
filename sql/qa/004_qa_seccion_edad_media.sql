-- Cohortes no mapeables por la lógica de edad representativa.
-- Debe devolver 0 filas.
WITH cohortes AS (
    SELECT DISTINCT
        edad_cohorte,
        lower(trim(edad_cohorte)) AS edad_cohorte_norm
    FROM core.poblacion_edad
)
SELECT edad_cohorte
FROM cohortes
WHERE edad_cohorte_norm !~ '^[0-9]+\s*-\s*[0-9]+$'
  AND edad_cohorte_norm !~ '^[0-9]+\s*(\+|y\s*m[aá]s)$'
ORDER BY edad_cohorte;

-- Sanity check del mart.
SELECT
    COUNT(*) AS n_seccion_anio,
    MIN(anio) AS min_anio,
    MAX(anio) AS max_anio,
    MIN(edad_media) AS min_edad_media,
    MAX(edad_media) AS max_edad_media,
    SUM(total_poblacion) AS total_poblacion
FROM marts.mv_seccion_edad_media;

-- Muestra para inspección rápida.
SELECT
    seccion_id,
    anio,
    ROUND(edad_media, 2) AS edad_media_frontend,
    total_poblacion,
    fecha_refresh
FROM marts.mv_seccion_edad_media
ORDER BY anio DESC, seccion_id
LIMIT 20;
