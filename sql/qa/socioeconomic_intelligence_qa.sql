-- 1. Cobertura por dominio/año
SELECT
    domain,
    anio,
    COUNT(*) AS rows,
    COUNT(DISTINCT seccion_id) AS secciones,
    COUNT(DISTINCT category_code) AS categorias
FROM core.socioeconomic_indicator_section
GROUP BY domain, anio
ORDER BY domain, anio;

-- 2. Categorías detectadas
SELECT DISTINCT
    domain,
    indicator_code,
    category_code,
    category_label,
    value_type,
    unit
FROM core.socioeconomic_indicator_section
ORDER BY domain, indicator_code, category_code;

-- 3. Duplicados
SELECT
    seccion_id,
    anio,
    domain,
    indicator_code,
    category_code,
    COUNT(*)
FROM core.socioeconomic_indicator_section
GROUP BY seccion_id, anio, domain, indicator_code, category_code
HAVING COUNT(*) > 1;

-- 4. Nulos críticos
SELECT *
FROM core.socioeconomic_indicator_section
WHERE value IS NULL;

-- 5. Geometría faltante
SELECT s.anio, s.seccion_id, s.domain
FROM core.socioeconomic_indicator_section s
LEFT JOIN marts.v_mapa_seccion_anio g
  ON s.seccion_id = g.seccion_id
 AND s.anio = g.anio
WHERE g.seccion_id IS NULL
ORDER BY s.domain, s.anio, s.seccion_id;

-- 6. Rangos por indicador
SELECT
    domain,
    indicator_code,
    category_code,
    anio,
    MIN(value),
    MAX(value),
    AVG(value)
FROM core.socioeconomic_indicator_section
GROUP BY domain, indicator_code, category_code, anio
ORDER BY domain, indicator_code, category_code, anio;

-- 7. Perfil socioeconómico
SELECT
    anio,
    COUNT(*) AS rows,
    COUNT(DISTINCT seccion_id) AS secciones
FROM marts.v_socioeconomic_profile
GROUP BY anio
ORDER BY anio;

-- 8. Base intelligence
SELECT
    anio,
    COUNT(*) AS rows,
    COUNT(DISTINCT seccion_id) AS secciones
FROM marts.v_socioeconomic_intelligence_base
GROUP BY anio
ORDER BY anio;

-- 9. Premium socioeconomic signals: cobertura por año
SELECT
    anio,
    COUNT(*) AS rows,
    COUNT(DISTINCT seccion_id) AS secciones
FROM marts.socioeconomic_intelligence_signals
GROUP BY anio
ORDER BY anio;

-- 10. Nulos por score
SELECT
    anio,
    COUNT(*) FILTER (WHERE human_capital_index IS NULL) AS null_human_capital,
    COUNT(*) FILTER (WHERE vulnerability_index IS NULL) AS null_vulnerability,
    COUNT(*) FILTER (WHERE resilience_index IS NULL) AS null_resilience,
    COUNT(*) FILTER (WHERE productive_complexity_index IS NULL) AS null_productive_complexity,
    COUNT(*) FILTER (WHERE inequality_pressure_index IS NULL) AS null_inequality_pressure
FROM marts.socioeconomic_intelligence_signals
GROUP BY anio
ORDER BY anio;

-- 11. Rangos 0-100 por año
SELECT
    anio,
    MIN(human_capital_index) AS min_human_capital,
    MAX(human_capital_index) AS max_human_capital,
    MIN(vulnerability_index) AS min_vulnerability,
    MAX(vulnerability_index) AS max_vulnerability,
    MIN(resilience_index) AS min_resilience,
    MAX(resilience_index) AS max_resilience,
    MIN(productive_complexity_index) AS min_productive_complexity,
    MAX(productive_complexity_index) AS max_productive_complexity,
    MIN(inequality_pressure_index) AS min_inequality_pressure,
    MAX(inequality_pressure_index) AS max_inequality_pressure
FROM marts.socioeconomic_intelligence_signals
GROUP BY anio
ORDER BY anio;

-- 12. Geometría faltante
SELECT anio, seccion_id
FROM marts.socioeconomic_intelligence_signals
WHERE geom IS NULL
ORDER BY anio, seccion_id;
