DROP MATERIALIZED VIEW IF EXISTS marts.territorial_intelligence_section_2023 CASCADE;

CREATE MATERIALIZED VIEW marts.territorial_intelligence_section_2023 AS
/*
Territorial Intelligence is an aggregated strategic layer.
It is not a real-estate appraisal, not an exact sale-price estimate and not a
replacement for valuation work. It combines section-level market references,
cadastral structure, building footprint intensity and sociodemographic signals
to compare territorial pressure, opportunity, saturation, prestige and demand
exposure across census/electoral sections.

Primary calibration source:
staging.manual_precio_m2_seccion_2023 is treated as the preferred observed
section-level market reference source. The municipal baseline is used only as a
fallback where no observed section reference exists. Observed market references
calibrate market pressure, prestige and opportunity signals; values are
winsorized through 5th/95th percentile bounds before 0-100 normalization to
reduce outlier-driven false precision.

Density and building footprint intensity are intentionally secondary inputs.
They inform saturation and context, but observed market references anchor market
pressure, prestige and the global territorial signal. Final component scores use
a light 80/20 adjacent-section smoothing step to improve geographic plausibility
without erasing genuine section-level differences.
*/
WITH base AS (
    SELECT
        vm.seccion_id,
        2023::integer AS anio,
        vm.seccion_numero_visible,
        vm.nombre_barrio,
        vm.zona_macro,
        vm.label_cliente,
        vm.geom,
        mfp.area_m2,
        mfp.area_km2,
        mfp.pob_total,
        mfp.densidad,
        mfp.renta_media_persona,
        mfp.renta_media_hogar,
        NULL::numeric AS pct_extran,
        age.average_age AS edad_media,
        mfp.participacion,
        parcel.num_parcelas,
        parcel.superficie_total_parcelas_m2,
        parcel.superficie_media_parcela_m2,
        built.num_building_parts,
        built.huella_construida_m2,
        built.huella_media_building_part_m2,
        ROUND(
            CASE
                WHEN mfp.area_m2 > 0 THEN built.huella_construida_m2::numeric / mfp.area_m2::numeric
                ELSE NULL
            END,
            6
        ) AS indice_construido,
        manual.precio_m2_observado,
        manual.fuente AS precio_m2_fuente,
        manual.notas AS precio_m2_notas,
        manual.confidence_level AS manual_confidence_level,
        muni.precio_mercado_m2 AS precio_m2_municipal_baseline,
        ROUND(
            (
                NULLIF(cat.vm_viv_colectiva, 0) * 0.55
                + NULLIF(cat.vm_viv_unifamiliar, 0) * 0.45
            )::numeric,
            2
        ) AS valor_catastral_distrito_baseline,
        COALESCE(manual.precio_m2_observado, muni.precio_mercado_m2) AS market_reference_m2,
        (manual.precio_m2_observado IS NOT NULL) AS price_reference_is_observed,
        CASE
            WHEN manual.precio_m2_observado IS NOT NULL THEN 1.00::numeric
            WHEN muni.precio_mercado_m2 IS NOT NULL THEN 0.55::numeric
            ELSE 0.00::numeric
        END AS market_reference_confidence_weight
    FROM marts.v_mapa_seccion_2023 vm
    LEFT JOIN marts.mijas_features_panel mfp
      ON mfp.seccion_id = vm.seccion_id
     AND mfp.anio = 2023
    LEFT JOIN marts.v_mapa_age_structure_2023 age
      ON age.seccion_id = vm.seccion_id
     AND age.anio = 2023
    LEFT JOIN marts.real_estate_section_profile_base parcel
      ON parcel.seccion_id = vm.seccion_id
    LEFT JOIN marts.real_estate_built_section_2023 built
      ON built.seccion_id = vm.seccion_id
    LEFT JOIN staging.manual_precio_m2_seccion_2023 manual
      ON manual.seccion_id = vm.seccion_id
    LEFT JOIN staging.vivienda_valor_tasado_mijas_2023 muni
      ON muni.anio = 2023
    LEFT JOIN staging.catastro_valor_distrito_mijas_2023 cat
      ON cat.aref = 2023
     AND cat.distrito = LEFT(vm.seccion_id, 7)::bigint
    WHERE LEFT(vm.seccion_id, 5) = '29070'
      AND vm.geom IS NOT NULL
),
raw_metrics AS (
    SELECT
        *,
        CASE
            WHEN area_m2 > 0 THEN huella_construida_m2::numeric / area_m2::numeric
            ELSE NULL
        END AS footprint_density_raw,
        CASE
            WHEN superficie_media_parcela_m2 > 0 THEN 1::numeric / superficie_media_parcela_m2::numeric
            ELSE NULL
        END AS small_parcel_raw,
        CASE
            WHEN pct_extran IS NULL THEN NULL
            WHEN pct_extran <= 1 THEN pct_extran * 100
            ELSE pct_extran
        END AS pct_extran_points
    FROM base
),
stats AS (
    SELECT
        percentile_cont(0.05) WITHIN GROUP (ORDER BY market_reference_m2) AS price_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY market_reference_m2) AS price_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY renta_media_persona) AS income_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY renta_media_persona) AS income_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY densidad) AS density_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY densidad) AS density_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY footprint_density_raw) AS footprint_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY footprint_density_raw) AS footprint_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY num_building_parts) AS parts_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY num_building_parts) AS parts_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY small_parcel_raw) AS small_parcel_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY small_parcel_raw) AS small_parcel_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY superficie_media_parcela_m2) AS parcel_size_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY superficie_media_parcela_m2) AS parcel_size_p95,
        percentile_cont(0.05) WITHIN GROUP (ORDER BY pct_extran_points) AS foreign_p05,
        percentile_cont(0.95) WITHIN GROUP (ORDER BY pct_extran_points) AS foreign_p95
    FROM raw_metrics
),
normalized AS (
    SELECT
        r.*,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.market_reference_m2, s.price_p05), s.price_p95) - s.price_p05) / NULLIF(s.price_p95 - s.price_p05, 0)))::numeric, 2) AS price_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.renta_media_persona, s.income_p05), s.income_p95) - s.income_p05) / NULLIF(s.income_p95 - s.income_p05, 0)))::numeric, 2) AS income_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.densidad, s.density_p05), s.density_p95) - s.density_p05) / NULLIF(s.density_p95 - s.density_p05, 0)))::numeric, 2) AS density_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.footprint_density_raw, s.footprint_p05), s.footprint_p95) - s.footprint_p05) / NULLIF(s.footprint_p95 - s.footprint_p05, 0)))::numeric, 2) AS footprint_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.num_building_parts, s.parts_p05), s.parts_p95) - s.parts_p05) / NULLIF(s.parts_p95 - s.parts_p05, 0)))::numeric, 2) AS building_parts_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.small_parcel_raw, s.small_parcel_p05), s.small_parcel_p95) - s.small_parcel_p05) / NULLIF(s.small_parcel_p95 - s.small_parcel_p05, 0)))::numeric, 2) AS small_parcel_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.superficie_media_parcela_m2, s.parcel_size_p05), s.parcel_size_p95) - s.parcel_size_p05) / NULLIF(s.parcel_size_p95 - s.parcel_size_p05, 0)))::numeric, 2) AS parcel_size_norm,
        ROUND(LEAST(100, GREATEST(0, 100 * (LEAST(GREATEST(r.pct_extran_points, s.foreign_p05), s.foreign_p95) - s.foreign_p05) / NULLIF(s.foreign_p95 - s.foreign_p05, 0)))::numeric, 2) AS foreign_norm
    FROM raw_metrics r
    CROSS JOIN stats s
),
raw_scores AS (
    SELECT
        *,
        ROUND((
            0.55 * COALESCE(price_norm, 50)
            + 0.18 * COALESCE(income_norm, 50)
            + 0.10 * COALESCE(density_norm, 50)
            + 0.07 * COALESCE(footprint_norm, 50)
            + 0.10 * COALESCE(foreign_norm, 50)
        )::numeric, 2) AS market_pressure_raw,
        ROUND((
            0.28 * COALESCE(footprint_norm, 50)
            + 0.22 * COALESCE(density_norm, 50)
            + 0.20 * COALESCE(building_parts_norm, 50)
            + 0.30 * COALESCE(small_parcel_norm, 50)
        )::numeric, 2) AS residential_saturation_raw,
        ROUND((
            CASE
                WHEN price_norm IS NULL THEN 50
                ELSE LEAST(100, GREATEST(0, 100 - ABS(price_norm - 45) * 100 / 55))
            END * 0.35
            + COALESCE(income_norm, 50) * 0.25
            + (100 - (
                0.28 * COALESCE(footprint_norm, 50)
                + 0.22 * COALESCE(density_norm, 50)
                + 0.20 * COALESCE(building_parts_norm, 50)
                + 0.30 * COALESCE(small_parcel_norm, 50)
            )) * 0.15
            + COALESCE(foreign_norm, 50) * 0.15
            + (
                0.55 * COALESCE(price_norm, 50)
                + 0.18 * COALESCE(income_norm, 50)
                + 0.10 * COALESCE(density_norm, 50)
                + 0.07 * COALESCE(footprint_norm, 50)
                + 0.10 * COALESCE(foreign_norm, 50)
            ) * 0.10
        )::numeric, 2) AS opportunity_signal_raw,
        ROUND((
            0.45 * COALESCE(price_norm, 50)
            + 0.30 * COALESCE(income_norm, 50)
            + 0.10 * COALESCE(parcel_size_norm, 50)
            + 0.05 * (100 - COALESCE(footprint_norm, 50))
            + 0.10 * COALESCE(foreign_norm, 50)
        )::numeric, 2) AS urban_prestige_raw,
        ROUND((
            CASE
                WHEN pct_extran_points IS NULL THEN
                    0.45 * COALESCE(price_norm, 50)
                    + 0.35 * COALESCE(income_norm, 50)
                    + 0.20 * (
                        0.45 * COALESCE(price_norm, 50)
                        + 0.30 * COALESCE(income_norm, 50)
                        + 0.10 * COALESCE(parcel_size_norm, 50)
                        + 0.05 * (100 - COALESCE(footprint_norm, 50))
                        + 0.10 * COALESCE(foreign_norm, 50)
                    )
                ELSE
                    0.45 * COALESCE(foreign_norm, 50)
                    + 0.20 * COALESCE(price_norm, 50)
                    + 0.20 * COALESCE(income_norm, 50)
                    + 0.15 * (
                        0.45 * COALESCE(price_norm, 50)
                        + 0.30 * COALESCE(income_norm, 50)
                        + 0.10 * COALESCE(parcel_size_norm, 50)
                        + 0.05 * (100 - COALESCE(footprint_norm, 50))
                        + 0.10 * COALESCE(foreign_norm, 50)
                    )
            END
        )::numeric, 2) AS foreign_demand_raw
    FROM normalized
),
neighbor_scores AS (
    SELECT
        a.seccion_id,
        AVG(b.market_pressure_raw) AS neighbor_market_pressure,
        AVG(b.opportunity_signal_raw) AS neighbor_opportunity_signal,
        AVG(b.residential_saturation_raw) AS neighbor_residential_saturation,
        AVG(b.urban_prestige_raw) AS neighbor_urban_prestige,
        AVG(b.foreign_demand_raw) AS neighbor_foreign_demand
    FROM raw_scores a
    JOIN raw_scores b
      ON a.seccion_id <> b.seccion_id
     AND ST_Touches(a.geom, b.geom)
    GROUP BY a.seccion_id
),
scores AS (
    SELECT
        r.*,
        ROUND((0.80 * r.market_pressure_raw + 0.20 * COALESCE(n.neighbor_market_pressure, r.market_pressure_raw))::numeric, 2) AS market_pressure_index,
        ROUND((0.80 * r.opportunity_signal_raw + 0.20 * COALESCE(n.neighbor_opportunity_signal, r.opportunity_signal_raw))::numeric, 2) AS opportunity_signal_score,
        ROUND((0.80 * r.residential_saturation_raw + 0.20 * COALESCE(n.neighbor_residential_saturation, r.residential_saturation_raw))::numeric, 2) AS residential_saturation_index,
        ROUND((0.80 * r.urban_prestige_raw + 0.20 * COALESCE(n.neighbor_urban_prestige, r.urban_prestige_raw))::numeric, 2) AS urban_prestige_signal,
        ROUND((0.80 * r.foreign_demand_raw + 0.20 * COALESCE(n.neighbor_foreign_demand, r.foreign_demand_raw))::numeric, 2) AS foreign_demand_exposure
    FROM raw_scores r
    LEFT JOIN neighbor_scores n
      ON n.seccion_id = r.seccion_id
),
final_scores AS (
    SELECT
        *,
        ROUND((
            0.30 * market_pressure_index
            + 0.25 * opportunity_signal_score
            + 0.25 * urban_prestige_signal
            + 0.08 * (100 - residential_saturation_index)
            + 0.12 * foreign_demand_exposure
        )::numeric, 2) AS territorial_signal_score
    FROM scores
)
SELECT
    seccion_id,
    anio,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    geom,
    pob_total,
    densidad,
    renta_media_persona,
    renta_media_hogar,
    pct_extran,
    edad_media,
    participacion,
    num_parcelas,
    superficie_total_parcelas_m2,
    superficie_media_parcela_m2,
    num_building_parts,
    huella_construida_m2,
    huella_media_building_part_m2,
    indice_construido,
    precio_m2_observado,
    precio_m2_fuente,
    precio_m2_notas,
    precio_m2_municipal_baseline,
    valor_catastral_distrito_baseline,
    market_reference_m2,
    price_reference_is_observed,
    market_reference_confidence_weight,
    price_norm,
    income_norm,
    density_norm,
    footprint_norm,
    market_pressure_index,
    opportunity_signal_score,
    residential_saturation_index,
    urban_prestige_signal,
    foreign_demand_exposure,
    territorial_signal_score,
    CASE
        WHEN market_pressure_index < 25 THEN 'Low'
        WHEN market_pressure_index < 45 THEN 'Stable'
        WHEN market_pressure_index < 65 THEN 'Dynamic'
        WHEN market_pressure_index < 82 THEN 'High Pressure'
        ELSE 'Critical'
    END AS market_pressure_label,
    CASE
        WHEN opportunity_signal_score < 35 THEN 'Low'
        WHEN opportunity_signal_score < 58 THEN 'Medium'
        WHEN opportunity_signal_score < 78 THEN 'High'
        ELSE 'Strategic'
    END AS opportunity_label,
    CASE
        WHEN residential_saturation_index < 30 THEN 'Low Density'
        WHEN residential_saturation_index < 55 THEN 'Balanced'
        WHEN residential_saturation_index < 78 THEN 'Compact'
        ELSE 'Saturated'
    END AS residential_profile_label,
    CASE
        WHEN urban_prestige_signal < 35 THEN 'Emerging'
        WHEN urban_prestige_signal < 60 THEN 'Consolidated'
        WHEN urban_prestige_signal < 80 THEN 'Premium'
        ELSE 'Prime'
    END AS prestige_label,
    CASE
        WHEN territorial_signal_score < 35 THEN 'Watch'
        WHEN territorial_signal_score < 52 THEN 'Stable'
        WHEN territorial_signal_score < 68 THEN 'Opportunity'
        WHEN residential_saturation_index >= 78 AND market_pressure_index >= 70 THEN 'High Pressure'
        WHEN territorial_signal_score < 82 THEN 'Strategic'
        ELSE 'High Pressure'
    END AS territorial_signal_label,
    CASE
        WHEN precio_m2_observado IS NOT NULL
         AND renta_media_persona IS NOT NULL
         AND huella_construida_m2 IS NOT NULL THEN 'High'
        WHEN renta_media_persona IS NOT NULL
         AND huella_construida_m2 IS NOT NULL THEN 'Medium'
        ELSE 'Low'
    END AS confidence_level,
    CASE
        WHEN precio_m2_observado IS NOT NULL THEN 'observed market reference'
        WHEN precio_m2_municipal_baseline IS NOT NULL THEN 'municipal market reference baseline'
        ELSE 'no market reference'
    END AS market_reference_type,
    CASE
        WHEN precio_m2_observado IS NOT NULL THEN 'manual section-level observed market reference'
        WHEN precio_m2_municipal_baseline IS NOT NULL THEN 'municipal baseline fallback'
        ELSE 'uncalibrated'
    END AS calibration_source
FROM final_scores;

CREATE UNIQUE INDEX IF NOT EXISTS ux_territorial_intelligence_section_2023
    ON marts.territorial_intelligence_section_2023 (seccion_id, anio);

CREATE INDEX IF NOT EXISTS ix_territorial_intelligence_section_2023_geom
    ON marts.territorial_intelligence_section_2023
    USING GIST (geom);

CREATE INDEX IF NOT EXISTS ix_territorial_intelligence_section_2023_signal
    ON marts.territorial_intelligence_section_2023 (territorial_signal_score DESC);

COMMENT ON MATERIALIZED VIEW marts.territorial_intelligence_section_2023 IS
    'Aggregated section-level territorial intelligence for strategic comparison in Mijas 2023. This mart is not a property valuation or appraisal layer.';
