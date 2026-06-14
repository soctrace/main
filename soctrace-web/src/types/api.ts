export type LayerKey =
  | "population"
  | "ageStructure"
  | "foreignBorn"
  | "incomeLevel"
  | "electoralBehavior"
  | "landBuiltEnvironment"
  | "housingIntelligence"
  | "socioeconomicIntelligence"
  | "electoralForecasting";

export type LayerCategory =
  | "territorialData"
  | "housingIntelligence"
  | "socioeconomicIntelligence"
  | "electoralForecasting"
  | "oraculum"
  | "narrativeIntelligence";

export type TerritorialDataLayer =
  | "population"
  | "ageStructure"
  | "incomeLevel"
  | "electoralResults"
  | "landBuiltEnvironment";

export type ActiveSubLayer = TerritorialDataLayer | string | null;

export type ElectionType = "municipales" | "andaluzas" | "congreso" | "europeas";
export type ElectionContestId =
  | "municipales_2023"
  | "municipales_2019"
  | "municipales_2015"
  | "andaluzas_2026"
  | "andaluzas_2022"
  | "andaluzas_2018"
  | "congreso_2023"
  | "congreso_2019_11"
  | "congreso_2019_04"
  | "europeas_2024"
  | "europeas_2019"
  | "europeas_2014";

export type ElectionContest = {
  id: ElectionContestId;
  type: ElectionType;
  label: string;
  year: string;
  electionId: number | null;
  available: boolean;
  disabledReason?: "comingSoon" | "geometriesUnavailable";
};

export type ElectionGroup = {
  type: ElectionType;
  label: string;
  contests: ElectionContest[];
};

export const electionGroups: ElectionGroup[] = [
  {
    type: "municipales",
    label: "Municipales",
    contests: [
      {
        id: "municipales_2015",
        type: "municipales",
        label: "2015",
        year: "2015",
        electionId: 11,
        available: true,
      },
      { id: "municipales_2019", type: "municipales", label: "2019", year: "2019", electionId: 4, available: true },
      { id: "municipales_2023", type: "municipales", label: "2023", year: "2023", electionId: 1, available: true },
    ],
  },
  {
    type: "andaluzas",
    label: "Andaluzas",
    contests: [
      { id: "andaluzas_2018", type: "andaluzas", label: "2018", year: "2018", electionId: 37, available: true },
      { id: "andaluzas_2022", type: "andaluzas", label: "2022", year: "2022", electionId: 17, available: true },
      {
        id: "andaluzas_2026",
        type: "andaluzas",
        label: "2026",
        year: "2026",
        electionId: 40,
        available: true,
      },
    ],
  },
  {
    type: "congreso",
    label: "Congreso",
    contests: [
      { id: "congreso_2019_04", type: "congreso", label: "2019A", year: "2019", electionId: 8, available: true },
      { id: "congreso_2019_11", type: "congreso", label: "2019N", year: "2019", electionId: 9, available: true },
      { id: "congreso_2023", type: "congreso", label: "2023", year: "2023", electionId: 10, available: true },
    ],
  },
  {
    type: "europeas",
    label: "Europeas",
    contests: [
      {
        id: "europeas_2014",
        type: "europeas",
        label: "2014",
        year: "2014",
        electionId: 14,
        available: true,
      },
      { id: "europeas_2019", type: "europeas", label: "2019", year: "2019", electionId: 15, available: true },
      { id: "europeas_2024", type: "europeas", label: "2024", year: "2024", electionId: 16, available: true },
    ],
  },
] as const;

export const electionContests: ElectionContest[] = electionGroups.flatMap((group) => group.contests);
export const defaultElectionContestId: ElectionContestId = "municipales_2023";
export type ElectionYear = ElectionContest["year"];
export const populationYears = ["2021", "2022", "2023", "2024", "2025"] as const;
export type PopulationYear = (typeof populationYears)[number];
export const ageStructureYears = ["2021", "2022", "2023", "2025"] as const;
export type AgeStructureYear = (typeof ageStructureYears)[number];
export const incomeYears = ["2019", "2020", "2021", "2022", "2023"] as const;
export type IncomeYear = (typeof incomeYears)[number];
export const SOCIAL_DEVELOPMENT_UI_YEAR = "2023";
export const socialDevelopmentAvailableYearsForUI = [SOCIAL_DEVELOPMENT_UI_YEAR] as const;
export const socialDevelopmentInternalYears = ["2021", "2022", "2023", "2024"] as const;
export type SocioeconomicYear = (typeof socialDevelopmentInternalYears)[number];

export type AgeCohortPoint = {
  cohort: string;
  population: number;
};

export type AgeCohortYearPoint = {
  year: AgeStructureYear;
  cohort: string;
  population: number;
};

export type SectionAgeStructure = {
  sectionId: string;
  sectionName: string;
  year: AgeStructureYear;
  cohorts: AgeCohortPoint[];
};

export type MunicipalityAgeStructureSummary = {
  year: number;
  totalPopulation: number;
  populationMale?: number | null;
  populationFemale?: number | null;
  cohorts: AgeCohortPoint[];
  averageAge: number | null;
  over65Pct: number | null;
  under30Pct: number | null;
  foreignBornPct?: number | null;
};

export type IncomeSourceKey =
  | "income_salary"
  | "income_pension"
  | "income_unemployment"
  | "income_social_benefits"
  | "income_other";

export type IncomeSourcePoint = {
  year: IncomeYear;
  source: IncomeSourceKey;
  value: number;
};

export type MunicipalityIncomeSummary = {
  year: number;
  individualIncome: number | null;
  householdIncome: number | null;
  sources: Record<IncomeSourceKey, number | null>;
};

export type RealEstateMetricKey = "cadastralValue" | "marketPrice" | "marketCadastreRatio";
export type LandBuiltEnvironmentMetricKey =
  | "populationDensity"
  | "parcelDensity"
  | "builtFootprint"
  | "avgPlotSize"
  | "buildingIntensity"
  | "urbanIntensity";
export type TerritorialMetricKey =
  | "qualityLife"
  | "perceivedSafetyPotential"
  | "noiseExposurePotential"
  | "airQualityPotential"
  | "marketPressure"
  | "urbanPrestige"
  | "opportunitySignal"
  | "residentialSaturation"
  | "territorialSignal"
  | "foreignDemand";
export type SocioeconomicMetricKey =
  | "humanCapital"
  | "vulnerability"
  | "resilience"
  | "productiveComplexity"
  | "inequalityPressure";

export type CampaignForecastMetricKey =
  | "volatility"
  | "abstentionRisk"
  | "localistPotential"
  | "swingSections"
  | "forecastConfidence";

export type ElectoralScenarioId =
  | "structural"
  | "candidate_reset"
  | "localist_fragmentation"
  | "oraculum_ready";

export type ElectoralScenarioPartyShare = {
  party: string;
  projected_vote_share: number;
};

export type ElectoralScenario = {
  municipality_id: string;
  forecast_year: number;
  scenario_id: ElectoralScenarioId;
  scenario_name: string;
  scenario_label: string;
  scenario_description: string;
  scenario_assumption: string;
  turnout_forecast: number | null;
  volatility: number | null;
  forecast_confidence: number;
  contextual_uncertainty: number;
  swing_territory_count: number;
  strategic_section_count: number;
  projected_vote_shares: ElectoralScenarioPartyShare[];
  projected_leading_party: string | null;
  projected_leading_vote_share: number | null;
  oraculum_calibrated: boolean;
  model_version: string;
  interpretation: string;
  cs_supply_uncertainty: number;
  pmp_supply_uncertainty: number;
  localist_supply_uncertainty: number;
  candidate_supply_uncertainty: number;
  is_conditional: boolean;
  has_contextual_adjustments: boolean;
  oraculum_priority_sections: {
    section_id: string;
    swing_sections: number;
    abstention_risk: number;
    forecast_confidence: number;
  }[];
};

export type ElectoralScenarioListResponse = {
  municipality_id: string;
  year: number;
  scenarios: ElectoralScenario[];
};

export type ProductivePotentialVariableKey =
  | "educationLevel"
  | "occupation"
  | "economicActivity"
  | "incomeSource"
  | "professionalStatus";

export type SectionFeatureProperties = {
  section_id: string;
  municipality_id: string;
  municipality: string;
  district: string;
  section_number?: string | null;
  label_cliente?: string | null;
  section_name?: string | null;
  display_name?: string | null;
  neighborhood?: string | null;
  nombre_barrio?: string | null;
  zone?: string | null;
  label?: string | null;
  area_km2?: number | null;
  population_total?: number | null;
  population_density?: number | null;
  population_male?: number | null;
  population_female?: number | null;
  pct_male?: number | null;
  pct_female?: number | null;
  population_0_19?: number | null;
  population_0_14?: number | null;
  population_15_29?: number | null;
  population_30_44?: number | null;
  population_45_64?: number | null;
  population_65_plus?: number | null;
  dependency_ratio?: number | null;
  population_quintile?: number | null;
  density_quintile?: number | null;
  pct_65_plus?: number | null;
  average_age?: number | null;
  age_group?: number | null;
  age_group_label?: string | null;
  age_color_key?: string | null;
  over_65_pct?: number | null;
  under_30_pct?: number | null;
  density_level?: string | null;
  pct_foreign_born?: number | null;
  turnout?: number | null;
  renta_media_persona?: number | null;
  renta_media_hogar?: number | null;
  income_quintile?: number | null;
  income_level?: string | null;
  income_rank_municipal?: number | null;
  income_index?: number | null;
  income_salary?: number | null;
  income_pension?: number | null;
  income_unemployment?: number | null;
  income_social_benefits?: number | null;
  income_other?: number | null;
  pension_dependency_index?: number | null;
  employment_dependency_index?: number | null;
  welfare_dependency_index?: number | null;
  entrepreneurial_activity_signal?: number | null;
  passive_income_signal?: number | null;
  winning_party?: string | null;
  winning_party_pct?: number | null;
  runner_up_party?: string | null;
  runner_up_pct?: number | null;
  victory_margin_pct?: number | string | null;
  local_vote_pct?: number | null;
  national_vote_pct?: number | null;
  left_bloc_pct?: number | null;
  right_bloc_pct?: number | null;
  fragmentation_index?: number | null;
  competitive_parties_count?: number | null;
  vote_concentration_index?: number | null;
  localism_index?: number | null;
  localism_category?: string | null;
  pct_pp?: number | null;
  pct_psoe?: number | null;
  pct_vox?: number | null;
  pct_cs?: number | null;
  pct_pacma?: number | null;
  pct_por_mi_pueblo?: number | null;
  pct_soydemijas?: number | null;
  pct_a_mijas?: number | null;
  pct_adelante_andalucia?: number | null;
  pct_con_andalucia?: number | null;
  volatility?: number | null;
  abstention_risk?: number | null;
  localist_potential?: number | null;
  swing_sections?: number | null;
  forecast_confidence?: number | null;
  projected_leading_party?: string | null;
  projected_vote_share?: number | null;
  structural_projected_leading_party?: string | null;
  structural_projected_vote_share?: number | null;
  turnout_forecast?: number | null;
  territorial_forecast_signal?: number | null;
  electoral_competitiveness?: number | null;
  turnout_sensitivity?: number | null;
  forecast_confidence_level?: "high" | "medium" | "low" | null;
  structural_forecast_confidence?: number | null;
  contextual_adjustment_score?: number | null;
  contextual_vote_adjustment_pct?: number | null;
  contextual_uncertainty?: number | null;
  contextual_confidence?: string | null;
  has_contextual_adjustments?: boolean | null;
  contextual_drivers?: { prior: string; value?: number | null; category: string }[];
  is_strategic_section?: boolean | null;
  is_swing_section?: boolean | null;
  is_abstention_risk_area?: boolean | null;
  forecast_interpretation?: string | null;
  forecast_drivers?: { variable: string; value?: number | null; category: string }[];
  forecast_model_version?: string | null;
  oraculum_calibrated?: boolean | null;
  forecast_swing_territory_count?: number | null;
  party_results_json?: {
    party: string;
    pct?: number | string | null;
    percentage?: number | string | null;
    vote_share?: number | string | null;
    votes?: number | string | null;
  }[];
  party_vote_percentages?: {
    party: string;
    percentage: number | string;
  }[];
  real_estate_year?: number | null;
  num_parcelas?: number | null;
  superficie_total_parcelas_m2?: number | null;
  superficie_media_parcela_m2?: number | null;
  densidad_parcelaria?: number | null;
  num_building_parts?: number | null;
  huella_construida_m2?: number | null;
  huella_media_building_part_m2?: number | null;
  valor_catastral_estimado_m2?: number | null;
  precio_mercado_estimado_m2?: number | null;
  ratio_mercado_catastro?: number | null;
  clasificacion_inmobiliaria?: string | null;
  indice_construido?: number | null;
  urban_intensity_index?: number | null;
  urban_intensity_label?: string | null;
  urban_intensity_completeness_pct?: number | null;
  real_estate_bucket?: number | null;
  land_built_environment_bucket?: number | null;
  territorial_bucket?: number | null;
  precio_m2_observado?: number | null;
  precio_m2_municipal_baseline?: number | null;
  valor_catastral_distrito_baseline?: number | null;
  market_reference_m2?: number | null;
  price_reference_is_observed?: boolean | null;
  market_reference_confidence_weight?: number | null;
  market_reference_type?: string | null;
  calibration_source?: string | null;
  market_pressure_index?: number | null;
  quality_life_score?: number | null;
  opportunity_signal_score?: number | null;
  opportunity_zone_score?: number | null;
  residential_saturation_index?: number | null;
  residential_balance_score?: number | null;
  urban_prestige_signal?: number | null;
  foreign_demand_exposure?: number | null;
  international_appeal_score?: number | null;
  territorial_signal_score?: number | null;
  housing_signal_score?: number | null;
  safety_potential_score?: number | null;
  noise_exposure_potential?: number | null;
  housing_stress_index?: number | null;
  daily_life_access_score?: number | null;
  quietness_potential?: number | null;
  residential_stability_proxy?: number | null;
  socioeconomic_resilience_proxy?: number | null;
  mobility_friction_proxy?: number | null;
  extreme_market_pressure?: number | null;
  market_pressure_label?: string | null;
  opportunity_label?: string | null;
  residential_profile_label?: string | null;
  prestige_label?: string | null;
  territorial_signal_label?: string | null;
  strategic_profile_label?: string | null;
  confidence_level?: string | null;
  pct_higher_studies?: number | null;
  pct_no_studies?: number | null;
  pct_primary_or_below?: number | null;
  pct_lower_secondary?: number | null;
  pct_upper_secondary?: number | null;
  pct_secondary_studies?: number | null;
  pct_employed?: number | null;
  pct_unemployed?: number | null;
  pct_student?: number | null;
  pct_pensioner?: number | null;
  pct_other_inactive?: number | null;
  pct_self_employed?: number | null;
  pct_employee?: number | null;
  pct_employee_or_other?: number | null;
  pct_services?: number | null;
  pct_construction?: number | null;
  pct_industry?: number | null;
  pct_agriculture?: number | null;
  pct_directors_managers?: number | null;
  pct_technicians_professionals?: number | null;
  pct_directors_managers_professionals?: number | null;
  pct_qualified_occupations?: number | null;
  pct_skilled_workers?: number | null;
  pct_elementary_occupations?: number | null;
  gini_index?: number | null;
  p80_p20_ratio?: number | null;
  income_unemployment_benefits?: number | null;
  income_business_activity?: number | null;
  income_real_estate?: number | null;
  education_high_norm?: number | null;
  low_education_norm?: number | null;
  qualified_occupation_norm?: number | null;
  employment_norm?: number | null;
  unemployment_norm?: number | null;
  income_norm?: number | null;
  low_income_norm?: number | null;
  social_benefits_norm?: number | null;
  unemployment_benefits_norm?: number | null;
  ageing_pressure_norm?: number | null;
  gini_norm?: number | null;
  lower_gini_norm?: number | null;
  p80_p20_norm?: number | null;
  income_diversity_norm?: number | null;
  sector_diversity_norm?: number | null;
  professional_status_diversity_norm?: number | null;
  business_activity_norm?: number | null;
  self_employment_norm?: number | null;
  advanced_services_industry_norm?: number | null;
  income_polarization_norm?: number | null;
  balanced_age_structure_norm?: number | null;
  human_capital_index?: number | null;
  vulnerability_index?: number | null;
  resilience_index?: number | null;
  productive_complexity_index?: number | null;
  inequality_pressure_index?: number | null;
  human_capital_completeness_pct?: number | null;
  vulnerability_completeness_pct?: number | null;
  resilience_completeness_pct?: number | null;
  productive_complexity_completeness_pct?: number | null;
  inequality_pressure_completeness_pct?: number | null;
  human_capital_label?: string | null;
  vulnerability_label?: string | null;
  resilience_label?: string | null;
  productive_complexity_label?: string | null;
  inequality_pressure_label?: string | null;
};

export type SectionFeature = GeoJSON.Feature<
  GeoJSON.Geometry,
  SectionFeatureProperties
>;

export type SectionFeatureCollection = GeoJSON.FeatureCollection<
  GeoJSON.Geometry,
  SectionFeatureProperties
> & {
  bbox?: [number, number, number, number];
};

export type SectionDetail = {
  display: {
    section_id: string;
    label: string;
    label_cliente?: string | null;
    section_name?: string | null;
    display_name?: string | null;
    municipality_id: string;
    municipality: string;
    district: string;
    section_number?: string | null;
    neighborhood?: string | null;
    nombre_barrio?: string | null;
    zone?: string | null;
    year?: number | null;
  };
  geography: {
    area_km2?: number | null;
    population_density?: number | null;
  };
  demography: {
    population_total?: number | null;
    population_male?: number | null;
    population_female?: number | null;
    population_0_14?: number | null;
    population_15_29?: number | null;
    population_30_44?: number | null;
    population_45_64?: number | null;
    population_65_plus?: number | null;
    pct_0_14?: number | null;
    pct_15_29?: number | null;
    pct_30_44?: number | null;
    pct_45_64?: number | null;
    pct_65_plus?: number | null;
    pct_foreign_born?: number | null;
    dependency_ratio?: number | null;
  };
  electoral: {
    election_id?: number | null;
    census?: number | null;
    turnout?: number | null;
    votes_cast?: number | null;
    valid_votes?: number | null;
    blank_votes?: number | null;
    null_votes?: number | null;
    blank_pct?: number | null;
    null_pct?: number | null;
    winning_party?: string | null;
    pct_pp?: number | null;
    pct_psoe?: number | null;
    pct_vox?: number | null;
  };
  income?: {
    renta_media_persona?: number | null;
    renta_media_hogar?: number | null;
    income_quintile?: number | null;
    income_level?: string | null;
    income_rank_municipal?: number | null;
    income_index?: number | null;
    income_salary?: number | null;
    income_pension?: number | null;
    income_unemployment?: number | null;
    income_social_benefits?: number | null;
    income_other?: number | null;
    pension_dependency_index?: number | null;
    employment_dependency_index?: number | null;
    welfare_dependency_index?: number | null;
    entrepreneurial_activity_signal?: number | null;
    passive_income_signal?: number | null;
  };
};

export type MunicipalitySummary = {
  municipality_id: string;
  name: string;
  section_count: number;
  available_years: number[];
};

export type MunicipalityPopulationSummary = {
  year: number;
  populationTotal: number;
  menTotal: number;
  womenTotal: number;
  menPct: number;
  womenPct: number;
  areaKm2: number;
  density: number | null;
};

export type MunicipalityListResponse = {
  items: MunicipalitySummary[];
};

export type DataSourceMode = "api" | "mock" | "unavailable";

export type StatusTone = "info" | "warning" | "error";
