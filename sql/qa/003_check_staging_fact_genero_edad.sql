SELECT COUNT(*) AS n_filas
FROM staging.fact_genero_edad;

SELECT sexo, genero, COUNT(*) AS n
FROM staging.fact_genero_edad
GROUP BY sexo, genero
ORDER BY sexo, genero;

SELECT DISTINCT edad_cohorte
FROM staging.fact_genero_edad
ORDER BY edad_cohorte;

SELECT *
FROM staging.fact_genero_edad
LIMIT 10;