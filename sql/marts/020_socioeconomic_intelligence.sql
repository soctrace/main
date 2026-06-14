CREATE SCHEMA IF NOT EXISTS marts;

DROP VIEW IF EXISTS marts.ml_socioeconomic_section_panel;
DROP VIEW IF EXISTS marts.socioeconomic_intelligence_signals;
DROP VIEW IF EXISTS marts.v_socioeconomic_intelligence_base;
DROP VIEW IF EXISTS marts.v_socioeconomic_profile;
DROP VIEW IF EXISTS marts.v_socioeconomic_indicators;

CREATE OR REPLACE VIEW marts.v_socioeconomic_indicators AS
WITH ranked AS (
    SELECT
        s.*,
        NTILE(5) OVER (
            PARTITION BY s.anio, s.domain, s.indicator_code, s.category_code
            ORDER BY s.value
        ) AS quintile,
        MIN(s.value) OVER (
            PARTITION BY s.anio, s.domain, s.indicator_code, s.category_code
        ) AS min_value,
        MAX(s.value) OVER (
            PARTITION BY s.anio, s.domain, s.indicator_code, s.category_code
        ) AS max_value
    FROM core.socioeconomic_indicator_section s
    WHERE s.value IS NOT NULL
)
SELECT
    r.seccion_id,
    r.anio,
    g.seccion_numero_visible,
    g.nombre_barrio,
    g.zona_macro,
    g.label_cliente,
    g.area_m2,
    g.area_km2,
    g.geom,
    g.geom_json,
    r.domain,
    r.indicator_code,
    r.category_code,
    r.indicator_label,
    r.category_label,
    r.value,
    r.value_type,
    r.unit,
    r.source_file,
    r.fuente,
    r.quintile,
    ROUND(
        100 * (r.value - r.min_value) / NULLIF(r.max_value - r.min_value, 0),
        2
    ) AS normalized_index
FROM ranked r
LEFT JOIN marts.v_mapa_seccion_anio g
  ON g.seccion_id = r.seccion_id
 AND g.anio = r.anio;

CREATE OR REPLACE VIEW marts.v_socioeconomic_profile AS
WITH totals AS (
    SELECT
        seccion_id,
        anio,
        domain,
        indicator_code,
        MAX(value) FILTER (WHERE category_code = 'total') AS total_value
    FROM core.socioeconomic_indicator_section
    WHERE value_type = 'count'
    GROUP BY seccion_id, anio, domain, indicator_code
),
normalized AS (
    SELECT
        s.seccion_id,
        s.anio,
        s.domain,
        s.indicator_code,
        s.category_code,
        CASE
            WHEN s.value_type = 'count'
             AND s.category_code <> 'total'
             AND t.total_value > 0
            THEN ROUND(s.value / t.total_value * 100, 4)
            ELSE s.value
        END AS profile_value
    FROM core.socioeconomic_indicator_section s
    LEFT JOIN totals t
      ON t.seccion_id = s.seccion_id
     AND t.anio = s.anio
     AND t.domain = s.domain
     AND t.indicator_code = s.indicator_code
    WHERE s.value IS NOT NULL
),
pivoted AS (
    SELECT
        seccion_id,
        anio,
        MAX(profile_value) FILTER (WHERE domain = 'education_level' AND category_code = 'primary_or_below') AS pct_primary_or_below,
        MAX(profile_value) FILTER (WHERE domain = 'education_level' AND category_code = 'lower_secondary') AS pct_lower_secondary,
        MAX(profile_value) FILTER (WHERE domain = 'education_level' AND category_code = 'upper_secondary') AS pct_upper_secondary,
        MAX(profile_value) FILTER (WHERE domain = 'education_level' AND category_code = 'higher') AS pct_higher_studies,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_status' AND category_code = 'employed') AS pct_employed,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_status' AND category_code = 'unemployed') AS pct_unemployed,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_status' AND category_code = 'student') AS pct_student,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_status' AND category_code = 'pensioner') AS pct_pensioner,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_status' AND category_code = 'other_inactive') AS pct_other_inactive,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_activity' AND category_code = 'directors_managers_professionals') AS pct_directors_managers_professionals,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_activity' AND category_code = 'skilled_workers') AS pct_skilled_workers,
        MAX(profile_value) FILTER (WHERE domain = 'occupation_activity' AND category_code = 'elementary_occupations') AS pct_elementary_occupations,
        MAX(profile_value) FILTER (WHERE domain = 'activity_branch' AND category_code = 'agriculture') AS pct_agriculture,
        MAX(profile_value) FILTER (WHERE domain = 'activity_branch' AND category_code = 'industry') AS pct_industry,
        MAX(profile_value) FILTER (WHERE domain = 'activity_branch' AND category_code = 'construction') AS pct_construction,
        MAX(profile_value) FILTER (WHERE domain = 'activity_branch' AND category_code = 'services') AS pct_services,
        MAX(profile_value) FILTER (WHERE domain = 'professional_status' AND category_code = 'self_employed') AS pct_self_employed,
        MAX(profile_value) FILTER (WHERE domain = 'professional_status' AND category_code = 'employee_or_other') AS pct_employee_or_other,
        MAX(profile_value) FILTER (WHERE domain = 'income_inequality' AND category_code = 'gini_index') AS gini_index,
        MAX(profile_value) FILTER (WHERE domain = 'income_inequality' AND category_code = 'p80_p20_ratio') AS p80_p20_ratio,
        MAX(profile_value) FILTER (WHERE domain = 'income_source' AND category_code = 'salary') AS income_salary,
        MAX(profile_value) FILTER (WHERE domain = 'income_source' AND category_code = 'pension') AS income_pension,
        MAX(profile_value) FILTER (WHERE domain = 'income_source' AND category_code = 'unemployment_benefits') AS income_unemployment_benefits,
        MAX(profile_value) FILTER (WHERE domain = 'income_source' AND category_code = 'social_benefits') AS income_social_benefits,
        MAX(profile_value) FILTER (WHERE domain = 'income_source' AND category_code = 'other_income') AS income_other
    FROM normalized
    WHERE category_code <> 'total'
    GROUP BY seccion_id, anio
)
SELECT
    p.seccion_id,
    p.anio,
    g.seccion_numero_visible,
    g.nombre_barrio,
    g.zona_macro,
    g.label_cliente,
    g.area_m2,
    g.area_km2,
    g.geom,
    g.geom_json,
    p.pct_primary_or_below,
    p.pct_lower_secondary,
    p.pct_upper_secondary,
    COALESCE(p.pct_lower_secondary, 0) + COALESCE(p.pct_upper_secondary, 0) AS pct_secondary_studies,
    p.pct_higher_studies,
    p.pct_primary_or_below AS pct_no_studies,
    p.pct_employed,
    p.pct_unemployed,
    p.pct_student,
    p.pct_pensioner,
    p.pct_other_inactive,
    p.pct_directors_managers_professionals,
    NULL::numeric AS pct_directors_managers,
    p.pct_directors_managers_professionals AS pct_technicians_professionals,
    p.pct_skilled_workers,
    p.pct_elementary_occupations,
    p.pct_agriculture,
    p.pct_industry,
    p.pct_construction,
    p.pct_services,
    p.pct_self_employed,
    p.pct_employee_or_other,
    p.pct_employee_or_other AS pct_employee,
    p.gini_index,
    p.p80_p20_ratio,
    p.income_salary,
    p.income_pension,
    p.income_unemployment_benefits,
    p.income_social_benefits,
    p.income_other,
    NULL::numeric AS income_business_activity,
    NULL::numeric AS income_real_estate
FROM pivoted p
LEFT JOIN marts.v_mapa_seccion_anio g
  ON g.seccion_id = p.seccion_id
 AND g.anio = p.anio;

CREATE OR REPLACE VIEW marts.v_socioeconomic_intelligence_base AS
SELECT
    p.seccion_id,
    p.anio,
    p.seccion_numero_visible,
    p.nombre_barrio,
    p.zona_macro,
    p.label_cliente,
    p.area_m2,
    p.area_km2,
    p.geom,
    p.geom_json,
    il.renta_media_persona,
    il.renta_media_hogar,
    il.income_index,
    pop.pob_total,
    ROUND(pop.pob_total / NULLIF(p.area_km2, 0), 2) AS densidad,
    edad.edad_media AS average_age,
    ROUND(pop.pct_65p * 100, 4) AS over_65_pct,
    ROUND((pop.pct_0_14 + pop.pct_15_29) * 100, 4) AS under_30_pct,
    p.pct_primary_or_below,
    p.pct_lower_secondary,
    p.pct_upper_secondary,
    p.pct_secondary_studies,
    p.pct_higher_studies,
    p.pct_no_studies,
    p.pct_employed,
    p.pct_unemployed,
    p.pct_pensioner,
    p.pct_directors_managers,
    p.pct_technicians_professionals,
    p.pct_directors_managers_professionals,
    p.pct_employee,
    p.gini_index,
    p.p80_p20_ratio,
    p.income_salary,
    p.income_pension,
    p.income_unemployment_benefits,
    p.income_social_benefits,
    p.income_business_activity,
    p.income_real_estate,
    p.income_other,
    p.pct_self_employed,
    p.pct_employee_or_other,
    p.pct_services,
    p.pct_construction,
    p.pct_industry,
    p.pct_agriculture
FROM marts.v_socioeconomic_profile p
LEFT JOIN marts.v_income_level il
  ON il.seccion_id = p.seccion_id
 AND il.anio = p.anio
LEFT JOIN marts.v_poblacion_seccion_anio pop
  ON pop.seccion_id = p.seccion_id
 AND pop.anio = p.anio
LEFT JOIN marts.mv_seccion_edad_media edad
  ON edad.seccion_id = p.seccion_id
 AND edad.anio = p.anio;

CREATE OR REPLACE VIEW marts.socioeconomic_intelligence_signals AS
WITH base AS (
    SELECT
        b.*,
        COALESCE(b.pct_directors_managers_professionals, b.pct_technicians_professionals) AS pct_qualified_occupations,
        CASE
            WHEN COALESCE(b.income_salary, 0)
               + COALESCE(b.income_pension, 0)
               + COALESCE(b.income_social_benefits, 0)
               + COALESCE(b.income_unemployment_benefits, 0)
               + COALESCE(b.income_business_activity, 0)
               + COALESCE(b.income_real_estate, 0)
               + COALESCE(b.income_other, 0) <= 0 THEN NULL::numeric
            ELSE ROUND(
                (
                    SELECT -SUM(p * LN(p)) / LN(7)
                    FROM (
                        SELECT value / NULLIF(total, 0) AS p
                        FROM (
                            SELECT
                                ARRAY[
                                    COALESCE(b.income_salary, 0),
                                    COALESCE(b.income_pension, 0),
                                    COALESCE(b.income_social_benefits, 0),
                                    COALESCE(b.income_unemployment_benefits, 0),
                                    COALESCE(b.income_business_activity, 0),
                                    COALESCE(b.income_real_estate, 0),
                                    COALESCE(b.income_other, 0)
                                ] AS values,
                                COALESCE(b.income_salary, 0)
                              + COALESCE(b.income_pension, 0)
                              + COALESCE(b.income_social_benefits, 0)
                              + COALESCE(b.income_unemployment_benefits, 0)
                              + COALESCE(b.income_business_activity, 0)
                              + COALESCE(b.income_real_estate, 0)
                              + COALESCE(b.income_other, 0) AS total
                        ) source,
                        LATERAL UNNEST(source.values) AS value
                        WHERE value > 0
                    ) shares
                )::numeric * 100,
                4
            )
        END AS income_diversity_raw,
        CASE
            WHEN COALESCE(b.pct_agriculture, 0) + COALESCE(b.pct_industry, 0) + COALESCE(b.pct_construction, 0) + COALESCE(b.pct_services, 0) <= 0 THEN NULL::numeric
            ELSE ROUND(
                (
                    SELECT -SUM(p * LN(p)) / LN(4)
                    FROM (
                        SELECT value / NULLIF(total, 0) AS p
                        FROM (
                            SELECT
                                ARRAY[
                                    COALESCE(b.pct_agriculture, 0),
                                    COALESCE(b.pct_industry, 0),
                                    COALESCE(b.pct_construction, 0),
                                    COALESCE(b.pct_services, 0)
                                ] AS values,
                                COALESCE(b.pct_agriculture, 0)
                              + COALESCE(b.pct_industry, 0)
                              + COALESCE(b.pct_construction, 0)
                              + COALESCE(b.pct_services, 0) AS total
                        ) source,
                        LATERAL UNNEST(source.values) AS value
                        WHERE value > 0
                    ) shares
                )::numeric * 100,
                4
            )
        END AS sector_diversity_raw,
        CASE
            WHEN COALESCE(b.pct_self_employed, 0) + COALESCE(b.pct_employee, 0) <= 0 THEN NULL::numeric
            ELSE ROUND(
                (
                    SELECT -SUM(p * LN(p)) / LN(2)
                    FROM (
                        SELECT value / NULLIF(total, 0) AS p
                        FROM (
                            SELECT
                                ARRAY[COALESCE(b.pct_self_employed, 0), COALESCE(b.pct_employee, 0)] AS values,
                                COALESCE(b.pct_self_employed, 0) + COALESCE(b.pct_employee, 0) AS total
                        ) source,
                        LATERAL UNNEST(source.values) AS value
                        WHERE value > 0
                    ) shares
                )::numeric * 100,
                4
            )
        END AS professional_status_diversity_raw,
        CASE
            WHEN b.over_65_pct IS NULL OR b.under_30_pct IS NULL THEN NULL::numeric
            ELSE GREATEST(0, 100 - ABS(b.over_65_pct - b.under_30_pct))
        END AS balanced_age_structure_raw
    FROM marts.v_socioeconomic_intelligence_base b
),
normalized AS (
    SELECT
        base.*,
        ROUND(100 * (pct_higher_studies - MIN(pct_higher_studies) OVER (PARTITION BY anio)) / NULLIF(MAX(pct_higher_studies) OVER (PARTITION BY anio) - MIN(pct_higher_studies) OVER (PARTITION BY anio), 0), 4) AS education_high_norm,
        ROUND(100 * (pct_no_studies - MIN(pct_no_studies) OVER (PARTITION BY anio)) / NULLIF(MAX(pct_no_studies) OVER (PARTITION BY anio) - MIN(pct_no_studies) OVER (PARTITION BY anio), 0), 4) AS low_education_norm,
        ROUND(100 * (pct_qualified_occupations - MIN(pct_qualified_occupations) OVER (PARTITION BY anio)) / NULLIF(MAX(pct_qualified_occupations) OVER (PARTITION BY anio) - MIN(pct_qualified_occupations) OVER (PARTITION BY anio), 0), 4) AS qualified_occupation_norm,
        ROUND(100 * (pct_employed - MIN(pct_employed) OVER (PARTITION BY anio)) / NULLIF(MAX(pct_employed) OVER (PARTITION BY anio) - MIN(pct_employed) OVER (PARTITION BY anio), 0), 4) AS employment_norm,
        ROUND(100 * (pct_unemployed - MIN(pct_unemployed) OVER (PARTITION BY anio)) / NULLIF(MAX(pct_unemployed) OVER (PARTITION BY anio) - MIN(pct_unemployed) OVER (PARTITION BY anio), 0), 4) AS unemployment_norm,
        ROUND(100 * (renta_media_persona - MIN(renta_media_persona) OVER (PARTITION BY anio)) / NULLIF(MAX(renta_media_persona) OVER (PARTITION BY anio) - MIN(renta_media_persona) OVER (PARTITION BY anio), 0), 4) AS income_norm,
        ROUND(100 - 100 * (renta_media_persona - MIN(renta_media_persona) OVER (PARTITION BY anio)) / NULLIF(MAX(renta_media_persona) OVER (PARTITION BY anio) - MIN(renta_media_persona) OVER (PARTITION BY anio), 0), 4) AS low_income_norm,
        ROUND(100 * (income_social_benefits - MIN(income_social_benefits) OVER (PARTITION BY anio)) / NULLIF(MAX(income_social_benefits) OVER (PARTITION BY anio) - MIN(income_social_benefits) OVER (PARTITION BY anio), 0), 4) AS social_benefits_norm,
        ROUND(100 * (income_unemployment_benefits - MIN(income_unemployment_benefits) OVER (PARTITION BY anio)) / NULLIF(MAX(income_unemployment_benefits) OVER (PARTITION BY anio) - MIN(income_unemployment_benefits) OVER (PARTITION BY anio), 0), 4) AS unemployment_benefits_norm,
        ROUND(100 * (over_65_pct - MIN(over_65_pct) OVER (PARTITION BY anio)) / NULLIF(MAX(over_65_pct) OVER (PARTITION BY anio) - MIN(over_65_pct) OVER (PARTITION BY anio), 0), 4) AS ageing_pressure_norm,
        ROUND(100 * (gini_index - MIN(gini_index) OVER (PARTITION BY anio)) / NULLIF(MAX(gini_index) OVER (PARTITION BY anio) - MIN(gini_index) OVER (PARTITION BY anio), 0), 4) AS gini_norm,
        ROUND(100 - 100 * (gini_index - MIN(gini_index) OVER (PARTITION BY anio)) / NULLIF(MAX(gini_index) OVER (PARTITION BY anio) - MIN(gini_index) OVER (PARTITION BY anio), 0), 4) AS lower_gini_norm,
        ROUND(100 * (p80_p20_ratio - MIN(p80_p20_ratio) OVER (PARTITION BY anio)) / NULLIF(MAX(p80_p20_ratio) OVER (PARTITION BY anio) - MIN(p80_p20_ratio) OVER (PARTITION BY anio), 0), 4) AS p80_p20_norm,
        ROUND(100 * (income_diversity_raw - MIN(income_diversity_raw) OVER (PARTITION BY anio)) / NULLIF(MAX(income_diversity_raw) OVER (PARTITION BY anio) - MIN(income_diversity_raw) OVER (PARTITION BY anio), 0), 4) AS income_diversity_norm,
        ROUND(100 * (sector_diversity_raw - MIN(sector_diversity_raw) OVER (PARTITION BY anio)) / NULLIF(MAX(sector_diversity_raw) OVER (PARTITION BY anio) - MIN(sector_diversity_raw) OVER (PARTITION BY anio), 0), 4) AS sector_diversity_norm,
        ROUND(100 * (professional_status_diversity_raw - MIN(professional_status_diversity_raw) OVER (PARTITION BY anio)) / NULLIF(MAX(professional_status_diversity_raw) OVER (PARTITION BY anio) - MIN(professional_status_diversity_raw) OVER (PARTITION BY anio), 0), 4) AS professional_status_diversity_norm,
        ROUND(100 * (COALESCE(income_business_activity, income_other) - MIN(COALESCE(income_business_activity, income_other)) OVER (PARTITION BY anio)) / NULLIF(MAX(COALESCE(income_business_activity, income_other)) OVER (PARTITION BY anio) - MIN(COALESCE(income_business_activity, income_other)) OVER (PARTITION BY anio), 0), 4) AS business_activity_norm,
        ROUND(100 * (pct_self_employed - MIN(pct_self_employed) OVER (PARTITION BY anio)) / NULLIF(MAX(pct_self_employed) OVER (PARTITION BY anio) - MIN(pct_self_employed) OVER (PARTITION BY anio), 0), 4) AS self_employment_norm,
        ROUND(100 * ((COALESCE(pct_services, 0) + COALESCE(pct_industry, 0)) - MIN(COALESCE(pct_services, 0) + COALESCE(pct_industry, 0)) OVER (PARTITION BY anio)) / NULLIF(MAX(COALESCE(pct_services, 0) + COALESCE(pct_industry, 0)) OVER (PARTITION BY anio) - MIN(COALESCE(pct_services, 0) + COALESCE(pct_industry, 0)) OVER (PARTITION BY anio), 0), 4) AS advanced_services_industry_norm,
        ROUND(ABS(COALESCE(income_index, 50) - 50) * 2, 4) AS income_polarization_norm,
        ROUND(100 * (balanced_age_structure_raw - MIN(balanced_age_structure_raw) OVER (PARTITION BY anio)) / NULLIF(MAX(balanced_age_structure_raw) OVER (PARTITION BY anio) - MIN(balanced_age_structure_raw) OVER (PARTITION BY anio), 0), 4) AS balanced_age_structure_norm
    FROM base
),
scores AS (
    SELECT
        n.*,
        ROUND(
            (
                COALESCE(education_high_norm * 0.35, 0)
              + COALESCE(qualified_occupation_norm * 0.25, 0)
              + COALESCE(employment_norm * 0.20, 0)
              + COALESCE(income_norm * 0.20, 0)
            ) / NULLIF(
                CASE WHEN education_high_norm IS NOT NULL THEN 0.35 ELSE 0 END
              + CASE WHEN qualified_occupation_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN employment_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN income_norm IS NOT NULL THEN 0.20 ELSE 0 END,
                0
            ),
            2
        ) AS human_capital_index,
        ROUND(100 * (
                CASE WHEN education_high_norm IS NOT NULL THEN 0.35 ELSE 0 END
              + CASE WHEN qualified_occupation_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN employment_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN income_norm IS NOT NULL THEN 0.20 ELSE 0 END
        ), 2) AS human_capital_completeness_pct,
        ROUND(
            (
                COALESCE(unemployment_norm * 0.25, 0)
              + COALESCE(low_income_norm * 0.25, 0)
              + COALESCE(low_education_norm * 0.20, 0)
              + COALESCE(GREATEST(COALESCE(social_benefits_norm, 0), COALESCE(unemployment_benefits_norm, 0)) * 0.15, 0)
              + COALESCE(ageing_pressure_norm * 0.10, 0)
              + COALESCE(gini_norm * 0.05, 0)
            ) / NULLIF(
                CASE WHEN unemployment_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN low_income_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN low_education_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN social_benefits_norm IS NOT NULL OR unemployment_benefits_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN ageing_pressure_norm IS NOT NULL THEN 0.10 ELSE 0 END
              + CASE WHEN gini_norm IS NOT NULL THEN 0.05 ELSE 0 END,
                0
            ),
            2
        ) AS vulnerability_index,
        ROUND(100 * (
                CASE WHEN unemployment_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN low_income_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN low_education_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN social_benefits_norm IS NOT NULL OR unemployment_benefits_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN ageing_pressure_norm IS NOT NULL THEN 0.10 ELSE 0 END
              + CASE WHEN gini_norm IS NOT NULL THEN 0.05 ELSE 0 END
        ), 2) AS vulnerability_completeness_pct,
        ROUND(
            (
                COALESCE(employment_norm * 0.25, 0)
              + COALESCE(income_norm * 0.20, 0)
              + COALESCE(income_diversity_norm * 0.20, 0)
              + COALESCE(lower_gini_norm * 0.15, 0)
              + COALESCE(education_high_norm * 0.10, 0)
              + COALESCE(self_employment_norm * 0.10, 0)
            ) / NULLIF(
                CASE WHEN employment_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN income_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN income_diversity_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN lower_gini_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN education_high_norm IS NOT NULL THEN 0.10 ELSE 0 END
              + CASE WHEN self_employment_norm IS NOT NULL THEN 0.10 ELSE 0 END,
                0
            ),
            2
        ) AS resilience_index,
        ROUND(100 * (
                CASE WHEN employment_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN income_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN income_diversity_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN lower_gini_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN education_high_norm IS NOT NULL THEN 0.10 ELSE 0 END
              + CASE WHEN self_employment_norm IS NOT NULL THEN 0.10 ELSE 0 END
        ), 2) AS resilience_completeness_pct,
        ROUND(
            (
                COALESCE(qualified_occupation_norm * 0.30, 0)
              + COALESCE(sector_diversity_norm * 0.25, 0)
              + COALESCE(business_activity_norm * 0.20, 0)
              + COALESCE(self_employment_norm * 0.15, 0)
              + COALESCE(advanced_services_industry_norm * 0.10, 0)
            ) / NULLIF(
                CASE WHEN qualified_occupation_norm IS NOT NULL THEN 0.30 ELSE 0 END
              + CASE WHEN sector_diversity_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN business_activity_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN self_employment_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN advanced_services_industry_norm IS NOT NULL THEN 0.10 ELSE 0 END,
                0
            ),
            2
        ) AS productive_complexity_index,
        ROUND(100 * (
                CASE WHEN qualified_occupation_norm IS NOT NULL THEN 0.30 ELSE 0 END
              + CASE WHEN sector_diversity_norm IS NOT NULL THEN 0.25 ELSE 0 END
              + CASE WHEN business_activity_norm IS NOT NULL THEN 0.20 ELSE 0 END
              + CASE WHEN self_employment_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN advanced_services_industry_norm IS NOT NULL THEN 0.10 ELSE 0 END
        ), 2) AS productive_complexity_completeness_pct,
        ROUND(
            (
                COALESCE(gini_norm * 0.40, 0)
              + COALESCE(p80_p20_norm * 0.35, 0)
              + COALESCE(low_income_norm * 0.15, 0)
              + COALESCE(income_polarization_norm * 0.10, 0)
            ) / NULLIF(
                CASE WHEN gini_norm IS NOT NULL THEN 0.40 ELSE 0 END
              + CASE WHEN p80_p20_norm IS NOT NULL THEN 0.35 ELSE 0 END
              + CASE WHEN low_income_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN income_polarization_norm IS NOT NULL THEN 0.10 ELSE 0 END,
                0
            ),
            2
        ) AS inequality_pressure_index,
        ROUND(100 * (
                CASE WHEN gini_norm IS NOT NULL THEN 0.40 ELSE 0 END
              + CASE WHEN p80_p20_norm IS NOT NULL THEN 0.35 ELSE 0 END
              + CASE WHEN low_income_norm IS NOT NULL THEN 0.15 ELSE 0 END
              + CASE WHEN income_polarization_norm IS NOT NULL THEN 0.10 ELSE 0 END
        ), 2) AS inequality_pressure_completeness_pct
    FROM normalized n
)
SELECT
    seccion_id,
    anio,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    area_m2,
    area_km2,
    geom,
    geom_json,
    renta_media_persona,
    renta_media_hogar,
    income_index,
    pob_total,
    densidad,
    average_age,
    over_65_pct,
    under_30_pct,
    pct_higher_studies,
    pct_no_studies,
    pct_secondary_studies,
    pct_employed,
    pct_unemployed,
    pct_pensioner,
    pct_self_employed,
    pct_employee,
    pct_services,
    pct_construction,
    pct_industry,
    pct_agriculture,
    pct_directors_managers,
    pct_technicians_professionals,
    pct_directors_managers_professionals,
    pct_qualified_occupations,
    gini_index,
    p80_p20_ratio,
    income_salary,
    income_pension,
    income_social_benefits,
    income_unemployment_benefits,
    income_business_activity,
    income_real_estate,
    income_other,
    education_high_norm,
    low_education_norm,
    qualified_occupation_norm,
    employment_norm,
    unemployment_norm,
    income_norm,
    low_income_norm,
    social_benefits_norm,
    unemployment_benefits_norm,
    ageing_pressure_norm,
    gini_norm,
    lower_gini_norm,
    p80_p20_norm,
    income_diversity_norm,
    sector_diversity_norm,
    professional_status_diversity_norm,
    business_activity_norm,
    self_employment_norm,
    advanced_services_industry_norm,
    income_polarization_norm,
    balanced_age_structure_norm,
    human_capital_index,
    vulnerability_index,
    resilience_index,
    productive_complexity_index,
    inequality_pressure_index,
    human_capital_completeness_pct,
    vulnerability_completeness_pct,
    resilience_completeness_pct,
    productive_complexity_completeness_pct,
    inequality_pressure_completeness_pct,
    CASE
      WHEN human_capital_index IS NULL THEN 'N/A'
      WHEN human_capital_index < 20 THEN 'Very Low'
      WHEN human_capital_index < 40 THEN 'Low'
      WHEN human_capital_index < 60 THEN 'Medium'
      WHEN human_capital_index < 80 THEN 'High'
      ELSE 'Very High'
    END AS human_capital_label,
    CASE
      WHEN vulnerability_index IS NULL THEN 'N/A'
      WHEN vulnerability_index < 20 THEN 'Very Low'
      WHEN vulnerability_index < 40 THEN 'Low'
      WHEN vulnerability_index < 60 THEN 'Medium'
      WHEN vulnerability_index < 80 THEN 'High'
      ELSE 'Very High'
    END AS vulnerability_label,
    CASE
      WHEN resilience_index IS NULL THEN 'N/A'
      WHEN resilience_index < 20 THEN 'Very Low'
      WHEN resilience_index < 40 THEN 'Low'
      WHEN resilience_index < 60 THEN 'Medium'
      WHEN resilience_index < 80 THEN 'High'
      ELSE 'Very High'
    END AS resilience_label,
    CASE
      WHEN productive_complexity_index IS NULL THEN 'N/A'
      WHEN productive_complexity_index < 20 THEN 'Very Low'
      WHEN productive_complexity_index < 40 THEN 'Low'
      WHEN productive_complexity_index < 60 THEN 'Medium'
      WHEN productive_complexity_index < 80 THEN 'High'
      ELSE 'Very High'
    END AS productive_complexity_label,
    CASE
      WHEN inequality_pressure_index IS NULL THEN 'N/A'
      WHEN inequality_pressure_index < 20 THEN 'Very Low'
      WHEN inequality_pressure_index < 40 THEN 'Low'
      WHEN inequality_pressure_index < 60 THEN 'Medium'
      WHEN inequality_pressure_index < 80 THEN 'High'
      ELSE 'Very High'
    END AS inequality_pressure_label
FROM scores;

CREATE OR REPLACE VIEW marts.ml_socioeconomic_section_panel AS
SELECT *
FROM marts.socioeconomic_intelligence_signals;
