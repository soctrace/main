from typing import Any

from pydantic import BaseModel, Field


class PartyVotePercentage(BaseModel):
    party: str
    percentage: float


class PartyResult(BaseModel):
    party: str
    pct: float
    votes: int


class SectionFeatureProperties(BaseModel):
    section_id: str
    municipality_id: str
    municipality: str
    district: str
    section_number: str | None = None
    label_cliente: str | None = None
    section_name: str | None = None
    display_name: str | None = None
    neighborhood: str | None = None
    nombre_barrio: str | None = None
    zone: str | None = None
    label: str | None = None
    area_km2: float | None = None
    population_total: int | None = None
    population_density: float | None = None
    population_male: int | None = None
    population_female: int | None = None
    pct_male: float | None = None
    pct_female: float | None = None
    population_0_19: int | None = None
    population_0_14: int | None = None
    population_15_29: int | None = None
    population_30_44: int | None = None
    population_45_64: int | None = None
    population_65_plus: int | None = None
    dependency_ratio: float | None = None
    population_quintile: int | None = None
    density_quintile: int | None = None
    pct_65_plus: float | None = None
    average_age: float | None = None
    age_group: int | None = None
    age_group_label: str | None = None
    age_color_key: str | None = None
    over_65_pct: float | None = None
    under_30_pct: float | None = None
    density_level: str | None = None
    pct_foreign_born: float | None = None
    turnout: float | None = None
    renta_media_persona: float | None = None
    renta_media_hogar: float | None = None
    income_quintile: int | None = None
    income_level: str | None = None
    income_rank_municipal: int | None = None
    income_index: float | None = None
    income_salary: float | None = None
    income_pension: float | None = None
    income_unemployment: float | None = None
    income_social_benefits: float | None = None
    income_other: float | None = None
    pension_dependency_index: float | None = None
    employment_dependency_index: float | None = None
    welfare_dependency_index: float | None = None
    entrepreneurial_activity_signal: float | None = None
    passive_income_signal: float | None = None
    winning_party: str | None = None
    winning_party_pct: float | None = None
    runner_up_party: str | None = None
    runner_up_pct: float | None = None
    victory_margin_pct: float | None = None
    local_vote_pct: float | None = None
    national_vote_pct: float | None = None
    left_bloc_pct: float | None = None
    right_bloc_pct: float | None = None
    fragmentation_index: float | None = None
    competitive_parties_count: int | None = None
    vote_concentration_index: float | None = None
    localism_index: float | None = None
    localism_category: str | None = None
    pct_pp: float | None = None
    pct_psoe: float | None = None
    pct_vox: float | None = None
    pct_cs: float | None = None
    pct_pacma: float | None = None
    pct_por_mi_pueblo: float | None = None
    pct_soydemijas: float | None = None
    pct_a_mijas: float | None = None
    pct_adelante_andalucia: float | None = None
    pct_con_andalucia: float | None = None
    party_results_json: list[PartyResult] = Field(default_factory=list)
    party_vote_percentages: list[PartyVotePercentage] = Field(default_factory=list)
    real_estate_year: int | None = None
    num_parcelas: int | None = None
    superficie_total_parcelas_m2: float | None = None
    superficie_media_parcela_m2: float | None = None
    densidad_parcelaria: float | None = None
    num_building_parts: int | None = None
    huella_construida_m2: float | None = None
    huella_media_building_part_m2: float | None = None
    valor_catastral_estimado_m2: float | None = None
    precio_mercado_estimado_m2: float | None = None
    ratio_mercado_catastro: float | None = None
    clasificacion_inmobiliaria: str | None = None
    indice_construido: float | None = None
    urban_intensity_index: float | None = None
    urban_intensity_label: str | None = None
    urban_intensity_completeness_pct: float | None = None
    precio_m2_observado: float | None = None
    precio_m2_municipal_baseline: float | None = None
    valor_catastral_distrito_baseline: float | None = None
    market_reference_m2: float | None = None
    price_reference_is_observed: bool | None = None
    market_reference_confidence_weight: float | None = None
    market_reference_type: str | None = None
    calibration_source: str | None = None
    market_pressure_index: float | None = None
    quality_life_score: float | None = None
    opportunity_signal_score: float | None = None
    opportunity_zone_score: float | None = None
    residential_saturation_index: float | None = None
    residential_balance_score: float | None = None
    urban_prestige_signal: float | None = None
    foreign_demand_exposure: float | None = None
    international_appeal_score: float | None = None
    territorial_signal_score: float | None = None
    housing_signal_score: float | None = None
    safety_potential_score: float | None = None
    noise_exposure_potential: float | None = None
    housing_stress_index: float | None = None
    daily_life_access_score: float | None = None
    quietness_potential: float | None = None
    residential_stability_proxy: float | None = None
    socioeconomic_resilience_proxy: float | None = None
    mobility_friction_proxy: float | None = None
    extreme_market_pressure: float | None = None
    market_pressure_label: str | None = None
    opportunity_label: str | None = None
    residential_profile_label: str | None = None
    prestige_label: str | None = None
    territorial_signal_label: str | None = None
    strategic_profile_label: str | None = None
    confidence_level: str | None = None
    pct_higher_studies: float | None = None
    pct_no_studies: float | None = None
    pct_secondary_studies: float | None = None
    pct_employed: float | None = None
    pct_unemployed: float | None = None
    pct_pensioner: float | None = None
    pct_self_employed: float | None = None
    pct_employee: float | None = None
    pct_services: float | None = None
    pct_construction: float | None = None
    pct_industry: float | None = None
    pct_agriculture: float | None = None
    pct_directors_managers: float | None = None
    pct_technicians_professionals: float | None = None
    pct_directors_managers_professionals: float | None = None
    pct_qualified_occupations: float | None = None
    gini_index: float | None = None
    p80_p20_ratio: float | None = None
    income_unemployment_benefits: float | None = None
    income_business_activity: float | None = None
    income_real_estate: float | None = None
    education_high_norm: float | None = None
    low_education_norm: float | None = None
    qualified_occupation_norm: float | None = None
    employment_norm: float | None = None
    unemployment_norm: float | None = None
    income_norm: float | None = None
    low_income_norm: float | None = None
    social_benefits_norm: float | None = None
    unemployment_benefits_norm: float | None = None
    ageing_pressure_norm: float | None = None
    gini_norm: float | None = None
    lower_gini_norm: float | None = None
    p80_p20_norm: float | None = None
    income_diversity_norm: float | None = None
    sector_diversity_norm: float | None = None
    professional_status_diversity_norm: float | None = None
    business_activity_norm: float | None = None
    self_employment_norm: float | None = None
    advanced_services_industry_norm: float | None = None
    income_polarization_norm: float | None = None
    balanced_age_structure_norm: float | None = None
    human_capital_index: float | None = None
    vulnerability_index: float | None = None
    resilience_index: float | None = None
    productive_complexity_index: float | None = None
    inequality_pressure_index: float | None = None
    human_capital_completeness_pct: float | None = None
    vulnerability_completeness_pct: float | None = None
    resilience_completeness_pct: float | None = None
    productive_complexity_completeness_pct: float | None = None
    inequality_pressure_completeness_pct: float | None = None
    human_capital_label: str | None = None
    vulnerability_label: str | None = None
    resilience_label: str | None = None
    productive_complexity_label: str | None = None
    inequality_pressure_label: str | None = None
    projected_leading_party: str | None = None
    projected_vote_share: float | None = None
    structural_projected_leading_party: str | None = None
    structural_projected_vote_share: float | None = None
    turnout_forecast: float | None = None
    volatility: float | None = None
    abstention_risk: float | None = None
    localist_potential: float | None = None
    swing_sections: float | None = None
    forecast_confidence: float | None = None
    structural_forecast_confidence: float | None = None
    forecast_confidence_level: str | None = None
    is_strategic_section: bool | None = None
    is_swing_section: bool | None = None
    is_abstention_risk_area: bool | None = None
    forecast_interpretation: str | None = None
    forecast_drivers: list[dict[str, Any]] = Field(default_factory=list)
    forecast_model_version: str | None = None
    oraculum_calibrated: bool | None = None
    contextual_adjustment_score: float | None = None
    contextual_vote_adjustment_pct: float | None = None
    contextual_uncertainty: float | None = None
    contextual_confidence: str | None = None
    has_contextual_adjustments: bool | None = None
    contextual_drivers: list[dict[str, Any]] = Field(default_factory=list)


class GeoFeature(BaseModel):
    type: str = "Feature"
    geometry: dict[str, Any]
    properties: SectionFeatureProperties


class GeoFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    bbox: list[float] | None = None
    features: list[GeoFeature]
