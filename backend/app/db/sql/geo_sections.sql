WITH selected_election AS (
    SELECT eb.election_id
    FROM marts.mv_electoral_behavior eb
    WHERE eb.anio = :year
      AND (CAST(:election_id AS bigint) IS NULL OR eb.election_id = CAST(:election_id AS bigint))
    GROUP BY eb.election_id, eb.tipo_eleccion_code, eb.mes
    ORDER BY
        CASE
            WHEN CAST(:election_id AS bigint) IS NOT NULL THEN 0
            WHEN eb.tipo_eleccion_code = 'MUNICIPALES' THEN 1
            ELSE 2
        END,
        eb.mes,
        eb.election_id
    LIMIT 1
),
geometry_year AS (
    SELECT COALESCE(
        (
            SELECT vm.anio
            FROM marts.v_mapa_seccion_anio vm
            WHERE vm.anio = :year
              AND LEFT(vm.seccion_id, 5) = :municipality_id
              AND vm.geom IS NOT NULL
            LIMIT 1
        ),
        (
            SELECT MIN(vm.anio)
            FROM marts.v_mapa_seccion_anio vm
            WHERE CAST(:election_id AS bigint) IS NOT NULL
              AND LEFT(vm.seccion_id, 5) = :municipality_id
              AND vm.geom IS NOT NULL
        )
    ) AS anio
),
electoral_behavior AS (
    SELECT
        eb.*,
        (
            SELECT (party_item->>'pct')::numeric * 100
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'normalized_party_family' = 'PP'
            ORDER BY (party_item->>'pct')::numeric DESC
            LIMIT 1
        ) AS pct_pp,
        (
            SELECT (party_item->>'pct')::numeric * 100
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'normalized_party_family' = 'PSOE'
            ORDER BY (party_item->>'pct')::numeric DESC
            LIMIT 1
        ) AS pct_psoe,
        (
            SELECT (party_item->>'pct')::numeric * 100
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'normalized_party_family' = 'VOX'
            ORDER BY (party_item->>'pct')::numeric DESC
            LIMIT 1
        ) AS pct_vox,
        (
            SELECT (party_item->>'pct')::numeric * 100
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'normalized_party_family' = 'CS'
            ORDER BY (party_item->>'pct')::numeric DESC
            LIMIT 1
        ) AS pct_cs,
        (
            SELECT (party_item->>'pct')::numeric * 100
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'normalized_party_family' = 'PACMA'
            ORDER BY (party_item->>'pct')::numeric DESC
            LIMIT 1
        ) AS pct_pacma,
        (
            SELECT SUM((party_item->>'pct')::numeric * 100)
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'normalized_party_family' = 'LOCAL'
        ) AS pct_local,
        (
            SELECT SUM((party_item->>'pct')::numeric * 100)
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'party' ILIKE '%ADELANTE%'
        ) AS pct_adelante_andalucia,
        (
            SELECT SUM((party_item->>'pct')::numeric * 100)
            FROM jsonb_array_elements(COALESCE(eb.party_results_json, '[]'::jsonb)) AS party_item
            WHERE party_item->>'party' ILIKE '%CON ANDALUC%'
        ) AS pct_con_andalucia
    FROM marts.mv_electoral_behavior eb
    JOIN selected_election se
      ON se.election_id = eb.election_id
),
base_sections AS (
    SELECT
        vm.seccion_id,
        vm.anio,
        vm.seccion_numero_visible,
        vm.nombre_barrio,
        vm.zona_macro,
        vm.label_cliente,
        vm.area_m2,
        vm.area_km2,
        vm.geom
    FROM marts.v_mapa_seccion_anio vm
    JOIN geometry_year gy
      ON gy.anio = vm.anio
),
filtered_sections AS (
    SELECT
        bs.seccion_id,
        bs.seccion_numero_visible,
        bs.nombre_barrio,
        bs.zona_macro,
        bs.label_cliente,
        bs.geom,
        COALESCE(mfp.anio, bs.anio) AS anio,
        COALESCE(mfp.area_km2, pop.area_km2, bs.area_km2) AS area_km2,
        COALESCE(pop.densidad, mfp.densidad) AS densidad,
        COALESCE(pop.pob_total, mfp.pob_total) AS pob_total,
        pop.pob_h,
        pop.pob_m,
        pop.pct_h,
        pop.pct_m,
        pop.pob_0_19,
        pop.pob_0_14,
        pop.pob_15_29,
        pop.pob_30_44,
        pop.pob_45_64,
        pop.dependency_ratio,
        mfp.pob_65p,
        COALESCE(pop.pob_65p, mfp.pob_65p) AS population_pob_65p,
        COALESCE(pop.pct_65p, mfp.pct_65p) AS pct_65p,
        pop.population_quintile,
        pop.density_quintile,
        COALESCE(eb.participacion, mfp.participacion) AS participacion,
        COALESCE(eb.winning_party, mfp.sigla_ganadora) AS sigla_ganadora,
        COALESCE(eb.pct_pp, mfp.pct_pp) AS pct_pp,
        COALESCE(eb.pct_psoe, mfp.pct_psoe) AS pct_psoe,
        COALESCE(eb.pct_vox, mfp.pct_vox) AS pct_vox,
        COALESCE(il.renta_media_persona, mfp.renta_media_persona) AS renta_media_persona,
        COALESCE(il.renta_media_hogar, mfp.renta_media_hogar) AS renta_media_hogar,
        COALESCE(il.income_quintile, mfp.income_quintile) AS income_quintile,
        COALESCE(il.income_level, mfp.income_level) AS income_level,
        COALESCE(il.income_rank_municipal, mfp.income_rank_municipal) AS income_rank_municipal,
        COALESCE(il.income_index, mfp.income_index) AS income_index,
        isp.income_salary,
        isp.income_pension,
        isp.income_unemployment,
        isp.income_social_benefits,
        isp.income_other,
        isp.pension_dependency_index,
        isp.employment_dependency_index,
        isp.welfare_dependency_index,
        isp.entrepreneurial_activity_signal,
        isp.passive_income_signal,
        eb.winning_party AS eb_winning_party,
        eb.winning_party_pct,
        eb.runner_up_party,
        eb.runner_up_pct,
        eb.victory_margin_pct,
        eb.local_vote_pct,
        eb.national_vote_pct,
        eb.left_bloc_pct,
        eb.right_bloc_pct,
        eb.fragmentation_index,
        eb.competitive_parties_count,
        eb.vote_concentration_index,
        eb.localism_index,
        eb.localism_category,
        eb.party_results_json,
        eb.pct_cs,
        eb.pct_pacma,
        eb.pct_local AS pct_por_mi_pueblo,
        NULL::numeric AS pct_soydemijas,
        NULL::numeric AS pct_a_mijas,
        eb.pct_adelante_andalucia,
        eb.pct_con_andalucia,
        age.average_age,
        age.age_group,
        age.age_group_label,
        age.age_color_key,
        age.over_65_pct,
        age.under_30_pct,
        age.density_level,
        COALESCE(lbe.anio, ti.anio) AS real_estate_year,
        lbe.num_parcelas,
        lbe.superficie_total_parcelas_m2,
        lbe.superficie_media_parcela_m2,
        lbe.densidad_parcelaria,
        lbe.num_building_parts,
        lbe.huella_construida_m2,
        lbe.huella_media_building_part_m2,
        ti.precio_m2_observado AS valor_catastral_estimado_m2,
        ti.market_reference_m2 AS precio_mercado_estimado_m2,
        NULL::numeric AS ratio_mercado_catastro,
        ti.territorial_signal_label AS clasificacion_inmobiliaria,
        lbe.indice_construido,
        lbe.urban_intensity_index,
        lbe.urban_intensity_label,
        lbe.urban_intensity_completeness_pct,
        ti.precio_m2_observado,
        ti.precio_m2_municipal_baseline,
        ti.valor_catastral_distrito_baseline,
        ti.market_reference_m2,
        ti.price_reference_is_observed,
        ti.market_reference_confidence_weight,
        ti.market_reference_type,
        ti.calibration_source,
        ti.market_pressure_index,
        COALESCE(hi.quality_life_score, ti.territorial_signal_score) AS quality_life_score,
        ti.opportunity_signal_score,
        COALESCE(hi.opportunity_zone_score, ti.opportunity_signal_score) AS opportunity_zone_score,
        ti.residential_saturation_index,
        COALESCE(hi.residential_balance_score, 100 - ti.residential_saturation_index) AS residential_balance_score,
        ti.urban_prestige_signal,
        ti.foreign_demand_exposure,
        COALESCE(hi.international_appeal_score, ti.foreign_demand_exposure) AS international_appeal_score,
        ti.territorial_signal_score,
        COALESCE(hi.housing_signal_score, ti.territorial_signal_score) AS housing_signal_score,
        hi.safety_potential_score,
        hi.noise_exposure_potential,
        hi.housing_stress_index,
        hf.daily_life_access_score,
        hf.quietness_potential,
        hf.residential_stability_proxy,
        hf.socioeconomic_resilience_proxy,
        hf.mobility_friction_proxy,
        hf.extreme_market_pressure,
        ti.market_pressure_label,
        ti.opportunity_label,
        ti.residential_profile_label,
        ti.prestige_label,
        ti.territorial_signal_label,
        hi.strategic_profile_label,
        ti.confidence_level,
        sis.pct_higher_studies,
        sis.pct_no_studies,
        sis.pct_secondary_studies,
        sis.pct_employed,
        sis.pct_unemployed,
        sis.pct_pensioner,
        sis.pct_self_employed,
        sis.pct_employee,
        sis.pct_services,
        sis.pct_construction,
        sis.pct_industry,
        sis.pct_agriculture,
        sis.pct_directors_managers,
        sis.pct_technicians_professionals,
        sis.pct_directors_managers_professionals,
        sis.pct_qualified_occupations,
        sis.gini_index,
        sis.p80_p20_ratio,
        sis.income_unemployment_benefits,
        sis.income_business_activity,
        sis.income_real_estate,
        sis.education_high_norm,
        sis.low_education_norm,
        sis.qualified_occupation_norm,
        sis.employment_norm,
        sis.unemployment_norm,
        sis.income_norm,
        sis.low_income_norm,
        sis.social_benefits_norm,
        sis.unemployment_benefits_norm,
        sis.ageing_pressure_norm,
        sis.gini_norm,
        sis.lower_gini_norm,
        sis.p80_p20_norm,
        sis.income_diversity_norm,
        sis.sector_diversity_norm,
        sis.professional_status_diversity_norm,
        sis.business_activity_norm,
        sis.self_employment_norm,
        sis.advanced_services_industry_norm,
        sis.income_polarization_norm,
        sis.balanced_age_structure_norm,
        sis.human_capital_index,
        sis.vulnerability_index,
        sis.resilience_index,
        sis.productive_complexity_index,
        sis.inequality_pressure_index,
        sis.human_capital_completeness_pct,
        sis.vulnerability_completeness_pct,
        sis.resilience_completeness_pct,
        sis.productive_complexity_completeness_pct,
        sis.inequality_pressure_completeness_pct,
        sis.human_capital_label,
        sis.vulnerability_label,
        sis.resilience_label,
        sis.productive_complexity_label,
        sis.inequality_pressure_label,
        ef.projected_leading_party,
        ef.projected_vote_share,
        ef.structural_projected_leading_party,
        ef.structural_projected_vote_share,
        ef.turnout_forecast,
        ef.volatility,
        ef.abstention_risk,
        ef.localist_potential,
        ef.swing_sections,
        ef.forecast_confidence,
        ef.structural_forecast_confidence,
        ef.confidence_level AS forecast_confidence_level,
        ef.is_strategic_section,
        ef.is_swing_section,
        ef.is_abstention_risk_area,
        ef.interpretation AS forecast_interpretation,
        ef.drivers AS forecast_drivers,
        ef.model_version AS forecast_model_version,
        ef.oraculum_calibrated,
        ef.contextual_adjustment_score,
        ef.contextual_vote_adjustment_pct,
        ef.contextual_uncertainty,
        ef.contextual_confidence,
        ef.has_contextual_adjustments,
        ef.contextual_drivers
    FROM base_sections bs
    LEFT JOIN marts.v_population_layer pop
      ON pop.seccion_id = bs.seccion_id
     AND pop.anio = bs.anio
    LEFT JOIN marts.mijas_features_panel mfp
      ON mfp.seccion_id = bs.seccion_id
     AND mfp.anio = :year
    LEFT JOIN marts.v_income_level il
      ON il.seccion_id = bs.seccion_id
     AND il.anio = :year
    LEFT JOIN marts.v_income_sources_profile isp
      ON isp.seccion_id = bs.seccion_id
     AND isp.anio = :year
    LEFT JOIN marts.v_mapa_age_structure age
      ON age.seccion_id = bs.seccion_id
     AND age.anio = :year
    LEFT JOIN electoral_behavior eb
      ON eb.seccion_id = bs.seccion_id
     AND eb.anio = :year
    LEFT JOIN marts.territorial_intelligence_section_2023 ti
      ON ti.seccion_id = bs.seccion_id
     AND ti.anio = :year
    LEFT JOIN marts.housing_intelligence_ui_2023 hi
      ON hi.seccion_id = bs.seccion_id
     AND hi.anio = :year
    LEFT JOIN marts.housing_intelligence_features_2023 hf
      ON hf.seccion_id = bs.seccion_id
     AND hf.anio = :year
    LEFT JOIN marts.v_land_built_environment lbe
      ON lbe.seccion_id = bs.seccion_id
     AND lbe.anio = :year
    LEFT JOIN marts.socioeconomic_intelligence_signals sis
      ON sis.seccion_id = bs.seccion_id
     AND sis.anio = :year
    LEFT JOIN marts.electoral_forecasting_ui_2027 ef
      ON ef.seccion_id = bs.seccion_id
    WHERE LEFT(bs.seccion_id, 5) = :municipality_id
      AND bs.geom IS NOT NULL
      AND ST_IsValid(bs.geom)
)
SELECT
    seccion_id,
    seccion_numero_visible,
    nombre_barrio,
    zona_macro,
    label_cliente,
    SUBSTRING(seccion_id FROM 6 FOR 2) AS district_code,
    ST_AsGeoJSON(ST_Transform(ST_Force2D(geom), 4326))::json AS geometry,
    area_km2,
    densidad,
    pob_total,
    pob_h,
    pob_m,
    pct_h,
    pct_m,
    pob_0_19,
    pob_0_14,
    pob_15_29,
    pob_30_44,
    pob_45_64,
    dependency_ratio,
    population_pob_65p AS pob_65p,
    pct_65p,
    population_quintile,
    density_quintile,
    participacion,
    COALESCE(eb_winning_party, sigla_ganadora) AS sigla_ganadora,
    pct_pp,
    pct_psoe,
    pct_vox,
    renta_media_persona,
    renta_media_hogar,
    income_quintile,
    income_level,
    income_rank_municipal,
    income_index,
    income_salary,
    income_pension,
    income_unemployment,
    income_social_benefits,
    income_other,
    pension_dependency_index,
    employment_dependency_index,
    welfare_dependency_index,
    entrepreneurial_activity_signal,
    passive_income_signal,
    winning_party_pct,
    runner_up_party,
    runner_up_pct,
    victory_margin_pct,
    local_vote_pct,
    national_vote_pct,
    left_bloc_pct,
    right_bloc_pct,
    fragmentation_index,
    competitive_parties_count,
    vote_concentration_index,
    localism_index,
    localism_category,
    party_results_json,
    pct_cs,
    pct_pacma,
    pct_por_mi_pueblo,
    pct_soydemijas,
    pct_a_mijas,
    pct_adelante_andalucia,
    pct_con_andalucia,
    average_age,
    age_group,
    age_group_label,
    age_color_key,
    over_65_pct,
    under_30_pct,
    density_level,
    real_estate_year,
    num_parcelas,
    superficie_total_parcelas_m2,
    superficie_media_parcela_m2,
    densidad_parcelaria,
    num_building_parts,
    huella_construida_m2,
    huella_media_building_part_m2,
    valor_catastral_estimado_m2,
    precio_mercado_estimado_m2,
    ratio_mercado_catastro,
    clasificacion_inmobiliaria,
    indice_construido,
    urban_intensity_index,
    urban_intensity_label,
    urban_intensity_completeness_pct,
    precio_m2_observado,
    precio_m2_municipal_baseline,
    valor_catastral_distrito_baseline,
    market_reference_m2,
    price_reference_is_observed,
    market_reference_confidence_weight,
    market_reference_type,
    calibration_source,
    market_pressure_index,
    quality_life_score,
    opportunity_signal_score,
    opportunity_zone_score,
    residential_saturation_index,
    residential_balance_score,
    urban_prestige_signal,
    foreign_demand_exposure,
    international_appeal_score,
    territorial_signal_score,
    housing_signal_score,
    safety_potential_score,
    noise_exposure_potential,
    housing_stress_index,
    daily_life_access_score,
    quietness_potential,
    residential_stability_proxy,
    socioeconomic_resilience_proxy,
    mobility_friction_proxy,
    extreme_market_pressure,
    market_pressure_label,
    opportunity_label,
    residential_profile_label,
    prestige_label,
    territorial_signal_label,
    strategic_profile_label,
    confidence_level,
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
    income_unemployment_benefits,
    income_business_activity,
    income_real_estate,
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
    human_capital_label,
    vulnerability_label,
    resilience_label,
    productive_complexity_label,
    inequality_pressure_label,
    projected_leading_party,
    projected_vote_share,
    structural_projected_leading_party,
    structural_projected_vote_share,
    turnout_forecast,
    volatility,
    abstention_risk,
    localist_potential,
    swing_sections,
    forecast_confidence,
    structural_forecast_confidence,
    forecast_confidence_level,
    is_strategic_section,
    is_swing_section,
    is_abstention_risk_area,
    forecast_interpretation,
    forecast_drivers,
    forecast_model_version,
    oraculum_calibrated,
    contextual_adjustment_score,
    contextual_vote_adjustment_pct,
    contextual_uncertainty,
    contextual_confidence,
    has_contextual_adjustments,
    contextual_drivers
FROM filtered_sections
ORDER BY seccion_id;
