CREATE OR REPLACE VIEW marts.v_income_sources AS
WITH ranked AS (
    SELECT
        f.seccion_id,
        f.anio,
        f.indicador_norm,
        f.indicador_original,
        f.valor,
        f.unidad,
        SUM(f.valor) OVER (
            PARTITION BY f.anio, f.indicador_norm
        ) AS municipal_indicator_total,
        NTILE(5) OVER (
            PARTITION BY f.anio, f.indicador_norm
            ORDER BY f.valor
        ) AS quintile,
        MIN(f.valor) OVER (
            PARTITION BY f.anio, f.indicador_norm
        ) AS min_valor,
        MAX(f.valor) OVER (
            PARTITION BY f.anio, f.indicador_norm
        ) AS max_valor
    FROM core.fuentes_ingresos_seccion f
    WHERE f.valor IS NOT NULL
),
scored AS (
    SELECT
        *,
        ROUND(
            CASE
                WHEN municipal_indicator_total > 0 THEN valor / municipal_indicator_total * 100
                ELSE NULL
            END,
            6
        ) AS valor_pct_municipal,
        ROUND(
            100 * (valor - min_valor) / NULLIF(max_valor - min_valor, 0),
            2
        ) AS income_source_index
    FROM ranked
)
SELECT
    s.seccion_id,
    s.anio,
    g.seccion_numero_visible,
    g.nombre_barrio,
    g.zona_macro,
    g.label_cliente,
    g.area_m2,
    g.area_km2,
    g.geom,
    g.geom_json,
    s.indicador_norm,
    s.indicador_original,
    s.valor,
    s.unidad,
    s.valor_pct_municipal,
    s.quintile,
    CASE s.quintile
        WHEN 1 THEN 'Very Low'
        WHEN 2 THEN 'Low'
        WHEN 3 THEN 'Medium'
        WHEN 4 THEN 'High'
        WHEN 5 THEN 'Very High'
    END AS income_source_level,
    s.income_source_index
FROM scored s
JOIN marts.v_mapa_seccion_anio g
  ON g.seccion_id = s.seccion_id
 AND g.anio = s.anio;

CREATE OR REPLACE VIEW marts.v_income_sources_profile AS
WITH pivoted AS (
    SELECT
        f.seccion_id,
        f.anio,
        MAX(f.valor) FILTER (WHERE f.indicador_norm = 'income_salary') AS income_salary,
        MAX(f.valor) FILTER (WHERE f.indicador_norm = 'income_pension') AS income_pension,
        MAX(f.valor) FILTER (WHERE f.indicador_norm = 'income_unemployment') AS income_unemployment,
        MAX(f.valor) FILTER (WHERE f.indicador_norm = 'income_social_benefits') AS income_social_benefits,
        MAX(f.valor) FILTER (WHERE f.indicador_norm = 'income_other') AS income_other
    FROM core.fuentes_ingresos_seccion f
    WHERE f.valor IS NOT NULL
    GROUP BY f.seccion_id, f.anio
),
signals AS (
    SELECT
        *,
        income_pension AS pension_signal_raw,
        income_salary AS employment_signal_raw,
        COALESCE(income_unemployment, 0) + COALESCE(income_social_benefits, 0) AS welfare_signal_raw,
        income_other AS other_income_signal_raw,
        COALESCE(income_pension, 0) + COALESCE(income_other, 0) AS passive_income_signal_raw
    FROM pivoted
),
ranked AS (
    SELECT
        *,
        MIN(pension_signal_raw) OVER (PARTITION BY anio) AS min_pension_signal,
        MAX(pension_signal_raw) OVER (PARTITION BY anio) AS max_pension_signal,
        MIN(employment_signal_raw) OVER (PARTITION BY anio) AS min_employment_signal,
        MAX(employment_signal_raw) OVER (PARTITION BY anio) AS max_employment_signal,
        MIN(welfare_signal_raw) OVER (PARTITION BY anio) AS min_welfare_signal,
        MAX(welfare_signal_raw) OVER (PARTITION BY anio) AS max_welfare_signal,
        MIN(other_income_signal_raw) OVER (PARTITION BY anio) AS min_other_income_signal,
        MAX(other_income_signal_raw) OVER (PARTITION BY anio) AS max_other_income_signal,
        MIN(passive_income_signal_raw) OVER (PARTITION BY anio) AS min_passive_income_signal,
        MAX(passive_income_signal_raw) OVER (PARTITION BY anio) AS max_passive_income_signal
    FROM signals
)
SELECT
    r.seccion_id,
    r.anio,
    g.seccion_numero_visible,
    g.nombre_barrio,
    g.zona_macro,
    g.label_cliente,
    g.geom,
    g.geom_json,
    r.income_salary,
    r.income_pension,
    r.income_unemployment,
    r.income_social_benefits,
    r.income_other,
    ROUND(
        100 * (r.pension_signal_raw - r.min_pension_signal)
        / NULLIF(r.max_pension_signal - r.min_pension_signal, 0),
        2
    ) AS pension_dependency_index,
    ROUND(
        100 * (r.employment_signal_raw - r.min_employment_signal)
        / NULLIF(r.max_employment_signal - r.min_employment_signal, 0),
        2
    ) AS employment_dependency_index,
    ROUND(
        100 * (r.welfare_signal_raw - r.min_welfare_signal)
        / NULLIF(r.max_welfare_signal - r.min_welfare_signal, 0),
        2
    ) AS welfare_dependency_index,
    ROUND(
        100 * (r.other_income_signal_raw - r.min_other_income_signal)
        / NULLIF(r.max_other_income_signal - r.min_other_income_signal, 0),
        2
    ) AS entrepreneurial_activity_signal,
    ROUND(
        100 * (r.passive_income_signal_raw - r.min_passive_income_signal)
        / NULLIF(r.max_passive_income_signal - r.min_passive_income_signal, 0),
        2
    ) AS passive_income_signal
FROM ranked r
JOIN marts.v_mapa_seccion_anio g
  ON g.seccion_id = r.seccion_id
 AND g.anio = r.anio;
