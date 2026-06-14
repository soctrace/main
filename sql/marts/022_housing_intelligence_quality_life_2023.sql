DROP MATERIALIZED VIEW IF EXISTS marts.housing_intelligence_ui_2023 CASCADE;
DROP MATERIALIZED VIEW IF EXISTS marts.housing_intelligence_features_2023 CASCADE;

CREATE MATERIALIZED VIEW marts.housing_intelligence_features_2023 AS
/*
Housing Intelligence reframes the previous housing layer as strategic
residential intelligence. It is not a property appraisal layer and it must not
be interpreted as crime, noise measurement or sale-price prediction.

The features mart is intentionally wide: it keeps visible metrics, hidden
synthetic proxies, methodological metadata and confidence signals for future
LLM agents, forecasting and Oraculum workflows. OSM road/POI integration can
replace the proxy road/service components when staging OSM tables are loaded.
*/
WITH base AS (
    SELECT
        ti.seccion_id,
        ti.anio,
        ti.seccion_numero_visible,
        ti.nombre_barrio,
        ti.zona_macro,
        ti.label_cliente,
        ti.geom,
        ti.pob_total,
        ti.densidad,
        ti.renta_media_persona,
        ti.renta_media_hogar,
        ti.precio_m2_observado,
        ti.market_reference_m2,
        ti.market_reference_confidence_weight,
        ti.market_pressure_index,
        ti.opportunity_signal_score AS opportunity_zone_score,
        ti.residential_saturation_index,
        ROUND((100 - COALESCE(ti.residential_saturation_index, 50))::numeric, 2) AS residential_balance_score,
        ti.urban_prestige_signal,
        ti.foreign_demand_exposure,
        ti.foreign_demand_exposure AS international_appeal_score,
        ti.territorial_signal_score AS housing_signal_score,
        ti.price_norm,
        ti.income_norm AS market_income_norm,
        ti.density_norm,
        ti.footprint_norm,
        ti.confidence_level AS housing_reference_confidence,
        ti.calibration_source,
        lbe.num_parcelas,
        lbe.superficie_total_parcelas_m2,
        lbe.superficie_media_parcela_m2,
        lbe.densidad_parcelaria,
        lbe.num_building_parts,
        lbe.huella_construida_m2,
        lbe.huella_media_building_part_m2,
        lbe.indice_construido,
        lbe.urban_intensity_index,
        lbe.built_intensity_norm,
        lbe.parcel_density_norm,
        sis.income_norm,
        sis.employment_norm,
        sis.unemployment_norm,
        sis.low_income_norm,
        sis.gini_norm,
        sis.lower_gini_norm,
        sis.p80_p20_norm,
        sis.education_high_norm,
        sis.qualified_occupation_norm,
        sis.income_diversity_norm,
        sis.balanced_age_structure_norm,
        sis.human_capital_index,
        sis.vulnerability_index,
        sis.resilience_index,
        sis.inequality_pressure_index,
        sis.productive_complexity_index
    FROM marts.territorial_intelligence_section_2023 ti
    LEFT JOIN marts.v_land_built_environment lbe
      ON lbe.seccion_id = ti.seccion_id
     AND lbe.anio = ti.anio
    LEFT JOIN marts.socioeconomic_intelligence_signals sis
      ON sis.seccion_id = ti.seccion_id
     AND sis.anio = ti.anio
    WHERE ti.anio = 2023
),
proxy_primary AS (
    SELECT
        *,
        ROUND((
            0.35 * COALESCE(resilience_index, 50)
            + 0.18 * (100 - COALESCE(vulnerability_index, 50))
            + 0.14 * COALESCE(lower_gini_norm, 50)
            + 0.12 * COALESCE(urban_prestige_signal, 50)
            + 0.09 * COALESCE(balanced_age_structure_norm, 50)
            + 0.07 * (100 - COALESCE(residential_saturation_index, 50))
            + 0.05 * (100 - COALESCE(footprint_norm, 50))
        )::numeric, 2) AS safety_potential_score,
        ROUND((
            0.32 * COALESCE(density_norm, 50)
            + 0.24 * COALESCE(footprint_norm, 50)
            + 0.18 * COALESCE(residential_saturation_index, 50)
            + 0.12 * COALESCE(built_intensity_norm, 50)
            + 0.08 * COALESCE(parcel_density_norm, 50)
            + 0.06 * (100 - COALESCE(balanced_age_structure_norm, 50))
        )::numeric, 2) AS road_intensity_proxy,
        ROUND((
            0.30 * COALESCE(density_norm, 50)
            + 0.22 * COALESCE(footprint_norm, 50)
            + 0.18 * COALESCE(residential_saturation_index, 50)
            + 0.15 * COALESCE(built_intensity_norm, 50)
            + 0.10 * COALESCE(parcel_density_norm, 50)
            + 0.05 * (100 - COALESCE(balanced_age_structure_norm, 50))
        )::numeric, 2) AS noise_exposure_potential,
        ROUND((
            0.55 * (100 - COALESCE(footprint_norm, 50))
            + 0.25 * (100 - COALESCE(density_norm, 50))
            + 0.20 * (100 - COALESCE(residential_saturation_index, 50))
        )::numeric, 2) AS quietness_potential,
        ROUND((
            0.40 * COALESCE(resilience_index, 50)
            + 0.18 * COALESCE(income_diversity_norm, 50)
            + 0.17 * COALESCE(balanced_age_structure_norm, 50)
            + 0.15 * COALESCE(employment_norm, 50)
            + 0.10 * (100 - COALESCE(residential_saturation_index, 50))
        )::numeric, 2) AS residential_stability_proxy,
        ROUND(COALESCE(resilience_index, 50)::numeric, 2) AS socioeconomic_resilience_proxy,
        ROUND(GREATEST(0, COALESCE(market_pressure_index, 50) - 72) * 3.5714::numeric, 2) AS extreme_market_pressure,
        ROUND((100 - COALESCE(footprint_norm, 50))::numeric, 2) AS green_space_proxy,
        ROUND(COALESCE(footprint_norm, 50)::numeric, 2) AS built_environment_pressure,
        ROUND((100 - COALESCE(market_pressure_index, 50))::numeric, 2) AS affordability_gap_index
    FROM base
),
proxy_secondary AS (
    SELECT
        *,
        ROUND((
            0.40 * COALESCE(density_norm, 50)
            + 0.25 * COALESCE(road_intensity_proxy, 50)
            + 0.20 * COALESCE(residential_saturation_index, 50)
            + 0.15 * COALESCE(footprint_norm, 50)
        )::numeric, 2) AS mobility_friction_proxy,
        ROUND((
            0.34 * COALESCE(market_pressure_index, 50)
            + 0.24 * COALESCE(residential_saturation_index, 50)
            + 0.18 * GREATEST(0, COALESCE(market_pressure_index, 50) - 72) * 3.5714
            + 0.14 * COALESCE(vulnerability_index, 50)
            + 0.10 * COALESCE(inequality_pressure_index, 50)
        )::numeric, 2) AS housing_stress_index
    FROM proxy_primary
),
proxy_daily AS (
    SELECT
        *,
        ROUND((
            0.28 * COALESCE(density_norm, 50)
            + 0.24 * COALESCE(human_capital_index, 50)
            + 0.18 * COALESCE(productive_complexity_index, 50)
            + 0.16 * COALESCE(balanced_age_structure_norm, 50)
            + 0.14 * (100 - COALESCE(mobility_friction_proxy, 50))
        )::numeric, 2) AS daily_life_access_score
    FROM proxy_secondary
),
proxy_scores AS (
    SELECT
        *,
        ROUND((
            0.34 * COALESCE(residential_saturation_index, 50)
            + 0.26 * COALESCE(housing_stress_index, 50)
            + 0.20 * COALESCE(noise_exposure_potential, 50)
            + 0.12 * COALESCE(mobility_friction_proxy, 50)
            + 0.08 * COALESCE(extreme_market_pressure, 0)
        )::numeric, 2) AS livability_tension_score,
        ROUND((100 - COALESCE(noise_exposure_potential, 50))::numeric, 2) AS urban_calm_index,
        ROUND((
            0.36 * COALESCE(daily_life_access_score, 50)
            + 0.24 * COALESCE(quietness_potential, 50)
            + 0.22 * COALESCE(safety_potential_score, 50)
            + 0.18 * COALESCE(balanced_age_structure_norm, 50)
        )::numeric, 2) AS family_suitability_score,
        ROUND((
            0.34 * COALESCE(daily_life_access_score, 50)
            + 0.26 * COALESCE(quietness_potential, 50)
            + 0.22 * COALESCE(safety_potential_score, 50)
            + 0.18 * (100 - COALESCE(mobility_friction_proxy, 50))
        )::numeric, 2) AS senior_comfort_score,
        ROUND((
            0.38 * COALESCE(housing_stress_index, 50)
            + 0.28 * COALESCE(extreme_market_pressure, 0)
            + 0.18 * COALESCE(inequality_pressure_index, 50)
            + 0.16 * (100 - COALESCE(residential_stability_proxy, 50))
        )::numeric, 2) AS displacement_risk_signal
    FROM proxy_daily
),
quality AS (
    SELECT
        *,
        ROUND(LEAST(100, GREATEST(0,
            0.14 * COALESCE(urban_prestige_signal, 50)
            + 0.12 * COALESCE(housing_signal_score, 50)
            + 0.11 * COALESCE(opportunity_zone_score, 50)
            + 0.10 * COALESCE(quietness_potential, 50)
            + 0.10 * COALESCE(safety_potential_score, 50)
            + 0.09 * COALESCE(daily_life_access_score, 50)
            + 0.08 * COALESCE(residential_stability_proxy, 50)
            + 0.08 * COALESCE(socioeconomic_resilience_proxy, 50)
            + 0.07 * (100 - COALESCE(residential_saturation_index, 50))
            + 0.06 * (100 - COALESCE(housing_stress_index, 50))
            + 0.05 * (100 - COALESCE(noise_exposure_potential, 50))
            + 0.05 * (100 - COALESCE(extreme_market_pressure, 0))
            + 0.05 * (100 - COALESCE(mobility_friction_proxy, 50))
        ))::numeric, 2) AS quality_life_score
    FROM proxy_scores
)
SELECT
    *,
    CASE
        WHEN quality_life_score >= 82 AND housing_stress_index < 55 THEN 'Premium'
        WHEN quality_life_score >= 68 AND housing_stress_index < 68 THEN 'High'
        WHEN quality_life_score >= 52 THEN 'Balanced'
        WHEN housing_stress_index >= 70 OR residential_saturation_index >= 78 THEN 'Pressured'
        ELSE 'Low'
    END AS strategic_profile_label,
    CASE
        WHEN housing_reference_confidence = 'High'
         AND resilience_index IS NOT NULL
         AND urban_intensity_index IS NOT NULL THEN 0.86::numeric
        WHEN resilience_index IS NOT NULL
         AND urban_intensity_index IS NOT NULL THEN 0.72::numeric
        ELSE 0.58::numeric
    END AS methodological_confidence_score,
    jsonb_build_object(
        'model', 'housing_intelligence_quality_life_2023',
        'interpretation', 'synthetic residential livability signal, not property appraisal',
        'safety_note', 'perceived safety potential only; not crime prediction',
        'noise_note', 'noise exposure potential proxy; not measured acoustic decibels',
        'osm_status', 'road and POI proxies are computed from internal density/built-environment signals until OSM staging tables are loaded',
        'score_scale', '0-100 normalized municipal comparison',
        'positive_factors', ARRAY[
            'urban_prestige_signal',
            'housing_signal_score',
            'opportunity_zone_score',
            'quietness_potential',
            'safety_potential_score',
            'daily_life_access_score',
            'residential_stability_proxy',
            'socioeconomic_resilience_proxy'
        ],
        'negative_factors', ARRAY[
            'residential_saturation_index',
            'housing_stress_index',
            'noise_exposure_potential',
            'extreme_market_pressure',
            'mobility_friction_proxy'
        ]
    ) AS methodological_metadata
FROM quality;

CREATE UNIQUE INDEX IF NOT EXISTS ux_housing_intelligence_features_2023
    ON marts.housing_intelligence_features_2023 (seccion_id, anio);

CREATE INDEX IF NOT EXISTS ix_housing_intelligence_features_2023_geom
    ON marts.housing_intelligence_features_2023 USING GIST (geom);

CREATE INDEX IF NOT EXISTS ix_housing_intelligence_features_2023_quality
    ON marts.housing_intelligence_features_2023 (quality_life_score DESC);

CREATE MATERIALIZED VIEW marts.housing_intelligence_ui_2023 AS
SELECT
    seccion_id,
    anio,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    quality_life_score,
    market_pressure_index,
    urban_prestige_signal,
    opportunity_zone_score,
    residential_saturation_index,
    residential_balance_score,
    housing_signal_score,
    foreign_demand_exposure,
    international_appeal_score,
    housing_stress_index,
    safety_potential_score,
    noise_exposure_potential,
    strategic_profile_label,
    geom
FROM marts.housing_intelligence_features_2023;

CREATE UNIQUE INDEX IF NOT EXISTS ux_housing_intelligence_ui_2023
    ON marts.housing_intelligence_ui_2023 (seccion_id, anio);

CREATE INDEX IF NOT EXISTS ix_housing_intelligence_ui_2023_geom
    ON marts.housing_intelligence_ui_2023 USING GIST (geom);

COMMENT ON MATERIALIZED VIEW marts.housing_intelligence_features_2023 IS
    'Deep Housing Intelligence features mart for LLM agents, forecasting, explainability and advanced analytics. Synthetic residential intelligence, not property appraisal.';

COMMENT ON MATERIALIZED VIEW marts.housing_intelligence_ui_2023 IS
    'Narrow frontend mart for Housing Intelligence UI: quality life, radar variables, safety/noise potential and geometry.';
