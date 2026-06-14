import type {
  LayerKey,
  CampaignForecastMetricKey,
  LandBuiltEnvironmentMetricKey,
  RealEstateMetricKey,
  SectionDetail,
  SectionFeature,
  SectionFeatureCollection,
  SectionFeatureProperties,
  SocioeconomicMetricKey,
  TerritorialMetricKey,
} from "@/types/api";

export const DENSITY_COLOR_STOPS = {
  violet: "#8B5CF6",
  red: "#F43F5E",
  yellow: "#F4B740",
  sky: "#67D4F2",
  blue: "#3B82F6",
} as const;

export const AGE_STRUCTURE_COLOR_STOPS = {
  veryYoung: "#2DD4BF",
  youngAdult: "#74C476",
  balanced: "#F2D56B",
  mature: "#F59E4B",
  senior: "#C95C66",
} as const;

export const INCOME_LEVEL_COLOR_STOPS = {
  veryLow: "#8FA6B8",
  low: "#88C7E8",
  medium: "#6EC6B2",
  high: "#E7C85E",
  veryHigh: "#E58B6D",
  fallback: "#64748B",
} as const;

export const REAL_ESTATE_METRICS: Record<
  RealEstateMetricKey,
  { title: string; shortTitle: string; unit: "eurM2" | "ratio"; field: keyof SectionFeatureProperties }
> = {
  cadastralValue: {
    title: "Referencia catastral",
    shortTitle: "Referencia catastral",
    unit: "eurM2",
    field: "valor_catastral_estimado_m2",
  },
  marketPrice: {
    title: "Referencia de mercado",
    shortTitle: "Mercado",
    unit: "eurM2",
    field: "precio_mercado_estimado_m2",
  },
  marketCadastreRatio: {
    title: "Relación mercado/catastro",
    shortTitle: "Ratio de referencia",
    unit: "ratio",
    field: "ratio_mercado_catastro",
  },
};

export const REAL_ESTATE_COLOR_STOPS: Record<RealEstateMetricKey, readonly string[]> = {
  cadastralValue: ["#26384a", "#31546a", "#3f7488", "#57a3b5", "#7fd1dc"],
  marketPrice: ["#8c7546", "#b0904f", "#c99a4c", "#d88442", "#c76338"],
  marketCadastreRatio: ["#3d6f99", "#7d9db1", "#9da4a8", "#c78678", "#dd6f68"],
};

export const LAND_BUILT_ENVIRONMENT_METRICS: Record<
  LandBuiltEnvironmentMetricKey,
  {
    title: string;
    shortTitle: string;
    unit: "density" | "parcelDensity" | "m2" | "percentage" | "index";
    field: keyof SectionFeatureProperties;
  }
> = {
  populationDensity: {
    title: "Densidad de población",
    shortTitle: "Densidad de población",
    unit: "density",
    field: "population_density",
  },
  parcelDensity: {
    title: "Densidad parcelaria",
    shortTitle: "Densidad parcelaria",
    unit: "parcelDensity",
    field: "densidad_parcelaria",
  },
  builtFootprint: {
    title: "Huella construida",
    shortTitle: "Huella construida",
    unit: "m2",
    field: "huella_construida_m2",
  },
  avgPlotSize: {
    title: "Tamaño medio de parcela",
    shortTitle: "Parcela media",
    unit: "m2",
    field: "superficie_media_parcela_m2",
  },
  buildingIntensity: {
    title: "Intensidad edificatoria",
    shortTitle: "Intensidad edificatoria",
    unit: "percentage",
    field: "indice_construido",
  },
  urbanIntensity: {
    title: "Intensidad urbana",
    shortTitle: "Intensidad urbana",
    unit: "index",
    field: "urban_intensity_index",
  },
};

export const LAND_BUILT_ENVIRONMENT_COLOR_STOPS: Record<
  LandBuiltEnvironmentMetricKey,
  readonly [string, string, string, string, string]
> = {
  populationDensity: ["#d6e4ec", "#9eb9c8", "#6f95a8", "#47758c", "#2f5c72"],
  parcelDensity: ["#d9e8df", "#a9cdb6", "#7bae91", "#578b70", "#3f6f59"],
  builtFootprint: ["#e1e5e7", "#b8c2c7", "#8f9fa8", "#6c7f89", "#4f626c"],
  avgPlotSize: ["#d7e5e1", "#abc9c1", "#82aaa0", "#628b82", "#486f67"],
  buildingIntensity: ["#dce5e8", "#b2c7cf", "#88a8b4", "#628895", "#456b78"],
  urbanIntensity: ["#e0e8df", "#b8cfb3", "#91b487", "#6e9566", "#52784d"],
};

export const SOCIOECONOMIC_METRICS: Record<
  SocioeconomicMetricKey,
  {
    title: string;
    shortTitle: string;
    field: keyof SectionFeatureProperties;
    labelField: keyof SectionFeatureProperties;
    completenessField: keyof SectionFeatureProperties;
    colors: readonly [string, string, string, string, string];
    breakdown: readonly { label: string; field: keyof SectionFeatureProperties }[];
  }
> = {
  humanCapital: {
    title: "Capital humano",
    shortTitle: "Capital humano",
    field: "human_capital_index",
    labelField: "human_capital_label",
    completenessField: "human_capital_completeness_pct",
    colors: ["#263f4d", "#315d67", "#417b80", "#58a0a0", "#7fc7c0"],
    breakdown: [
      { label: "Estudios superiores", field: "education_high_norm" },
      { label: "Trabajo cualificado", field: "qualified_occupation_norm" },
      { label: "Empleo", field: "employment_norm" },
      { label: "Renta", field: "income_norm" },
    ],
  },
  vulnerability: {
    title: "Vulnerabilidad",
    shortTitle: "Vulnerabilidad",
    field: "vulnerability_index",
    labelField: "vulnerability_label",
    completenessField: "vulnerability_completeness_pct",
    colors: ["#3c4650", "#69654f", "#99835a", "#b8785e", "#b85f66"],
    breakdown: [
      { label: "Desempleo", field: "unemployment_norm" },
      { label: "Renta baja", field: "low_income_norm" },
      { label: "Baja educación", field: "low_education_norm" },
      { label: "Prestaciones", field: "social_benefits_norm" },
      { label: "Envejecimiento", field: "ageing_pressure_norm" },
    ],
  },
  resilience: {
    title: "Resiliencia",
    shortTitle: "Resiliencia",
    field: "resilience_index",
    labelField: "resilience_label",
    completenessField: "resilience_completeness_pct",
    colors: ["#243f3e", "#315b52", "#427767", "#5c977e", "#87b99a"],
    breakdown: [
      { label: "Empleo", field: "employment_norm" },
      { label: "Renta", field: "income_norm" },
      { label: "Diversidad", field: "income_diversity_norm" },
      { label: "Menor desigualdad", field: "lower_gini_norm" },
      { label: "Educación", field: "education_high_norm" },
    ],
  },
  productiveComplexity: {
    title: "Complejidad productiva",
    shortTitle: "Complejidad",
    field: "productive_complexity_index",
    labelField: "productive_complexity_label",
    completenessField: "productive_complexity_completeness_pct",
    colors: ["#2d3650", "#3c4f73", "#506a8f", "#6988a8", "#8fb0c1"],
    breakdown: [
      { label: "Trabajo cualificado", field: "qualified_occupation_norm" },
      { label: "Diversidad sectorial", field: "sector_diversity_norm" },
      { label: "Actividad empresarial", field: "business_activity_norm" },
      { label: "Autónomos", field: "self_employment_norm" },
    ],
  },
  inequalityPressure: {
    title: "Presión de desigualdad",
    shortTitle: "Desigualdad",
    field: "inequality_pressure_index",
    labelField: "inequality_pressure_label",
    completenessField: "inequality_pressure_completeness_pct",
    colors: ["#40333f", "#644453", "#875767", "#a96a78", "#c6868d"],
    breakdown: [
      { label: "Gini", field: "gini_norm" },
      { label: "P80/P20", field: "p80_p20_norm" },
      { label: "Renta baja", field: "low_income_norm" },
      { label: "Polarización", field: "income_polarization_norm" },
    ],
  },
};

function normalizeLandBuiltEnvironmentMetric(
  metric: LandBuiltEnvironmentMetricKey,
): LandBuiltEnvironmentMetricKey {
  return LAND_BUILT_ENVIRONMENT_METRICS[metric] ? metric : "populationDensity";
}

export const TERRITORIAL_METRICS: Record<
  TerritorialMetricKey,
  {
    title: string;
    shortTitle: string;
    field: keyof SectionFeatureProperties;
    labelField: keyof SectionFeatureProperties;
    colors: readonly [string, string, string, string, string];
    labels: readonly [string, string, string];
  }
> = {
  qualityLife: {
    title: "Calidad de vida",
    shortTitle: "Calidad de vida",
    field: "quality_life_score",
    labelField: "strategic_profile_label",
    colors: ["#8f3d4a", "#b85c55", "#b88a55", "#5e9e99", "#2dd4bf"],
    labels: ["Tensionada", "Equilibrada", "Premium"],
  },
  perceivedSafetyPotential: {
    title: "Potencial de seguridad percibida",
    shortTitle: "Seguridad percibida",
    field: "safety_potential_score",
    labelField: "strategic_profile_label",
    colors: ["#6d28d9", "#7c3aed", "#64748b", "#67a878", "#8bd9a5"],
    labels: ["Atención", "Moderada", "Tranquila"],
  },
  noiseExposurePotential: {
    title: "Exposición potencial al ruido",
    shortTitle: "Ruido",
    field: "noise_exposure_potential",
    labelField: "strategic_profile_label",
    colors: ["#7bd88f", "#6aa683", "#777b8a", "#7c3aed", "#a855f7"],
    labels: ["Baja", "Moderada", "Alta"],
  },
  airQualityPotential: {
    title: "Potencial de calidad del aire",
    shortTitle: "Calidad del aire",
    field: "quality_life_score",
    labelField: "strategic_profile_label",
    colors: ["#64748b", "#64748b", "#64748b", "#64748b", "#64748b"],
    labels: ["Inactiva", "Inactiva", "Inactiva"],
  },
  marketPressure: {
    title: "Presión de mercado",
    shortTitle: "Presión de mercado",
    field: "market_pressure_index",
    labelField: "market_pressure_label",
    colors: ["#2f3a52", "#405b79", "#5e7fa0", "#9a7a52", "#c09a5a"],
    labels: ["Muy baja", "Media", "Muy alta"],
  },
  urbanPrestige: {
    title: "Prestigio urbano",
    shortTitle: "Prestigio",
    field: "urban_prestige_signal",
    labelField: "prestige_label",
    colors: ["#293044", "#414f75", "#64748b", "#8c7891", "#b08aa6"],
    labels: ["Muy bajo", "Medio", "Muy alto"],
  },
  opportunitySignal: {
    title: "Zonas de oportunidad",
    shortTitle: "Oportunidad",
    field: "opportunity_signal_score",
    labelField: "opportunity_label",
    colors: ["#26384a", "#335f72", "#3e8491", "#5d8f90", "#a98f54"],
    labels: ["Muy baja", "Media", "Muy alta"],
  },
  residentialSaturation: {
    title: "Equilibrio residencial",
    shortTitle: "Equilibrio",
    field: "residential_saturation_index",
    labelField: "residential_profile_label",
    colors: ["#2e3b4f", "#455d6c", "#657b84", "#8a7d72", "#b38a62"],
    labels: ["Muy bajo", "Medio", "Muy alto"],
  },
  territorialSignal: {
    title: "Señal inmobiliaria",
    shortTitle: "Señal inmobiliaria",
    field: "territorial_signal_score",
    labelField: "territorial_signal_label",
    colors: ["#30384f", "#405d82", "#5a7da0", "#7c6fa0", "#a277a2"],
    labels: ["Muy baja", "Media", "Muy alta"],
  },
  foreignDemand: {
    title: "Atracción internacional",
    shortTitle: "Atracción internacional",
    field: "foreign_demand_exposure",
    labelField: "confidence_level",
    colors: ["#26364f", "#2f5e7b", "#3b8795", "#589aa1", "#8a7aa0"],
    labels: ["Muy baja", "Media", "Muy alta"],
  },
};

export type RealEstateLegendItem = {
  label: string;
  color: string;
};

export type RealEstateLegend = {
  title: string;
  unit: string;
  items: RealEstateLegendItem[];
};

export type TerritorialLegend = {
  title: string;
  subtitle: string;
  items: RealEstateLegendItem[];
  labels: readonly [string, string, string];
};

export type LandBuiltEnvironmentLegend = {
  title: string;
  subtitle: string;
  items: RealEstateLegendItem[];
  labels: readonly [string, string, string];
};

export type SocioeconomicLegend = {
  title: string;
  subtitle: string;
  items: RealEstateLegendItem[];
  labels: readonly [string, string, string];
};

export const CAMPAIGN_FORECAST_METRICS: Record<
  CampaignForecastMetricKey,
  {
    title: string;
    shortTitle: string;
    color: string;
    field: keyof SectionFeatureProperties;
  }
> = {
  volatility: {
    title: "Volatilidad",
    shortTitle: "Volatilidad",
    color: "#d79a45",
    field: "volatility",
  },
  abstentionRisk: {
    title: "Riesgo de abstención",
    shortTitle: "Abstención",
    color: "#c46f5f",
    field: "abstention_risk",
  },
  localistPotential: {
    title: "Potencial localista",
    shortTitle: "Localista",
    color: "#9b83c8",
    field: "localist_potential",
  },
  swingSections: {
    title: "Cambio electoral",
    shortTitle: "Cambio",
    color: "#5fb7d8",
    field: "swing_sections",
  },
  forecastConfidence: {
    title: "Confianza de previsión",
    shortTitle: "Confianza",
    color: "#75b889",
    field: "forecast_confidence",
  },
};

export const PARTY_COLOR_STOPS = {
  psoe: [255, 0, 0, 220],
  pp: [51, 153, 255, 220],
  vox: [115, 180, 70, 220],
  cs: [255, 88, 36, 220],
  upyd: [226, 0, 122, 220],
  podemos: [109, 80, 179, 220],
  porAndalucia: [20, 184, 166, 215],
  seAcaboLaFiesta: [236, 184, 72, 220],
  porMiPueblo: [139, 92, 246, 210],
  soyDeMijas: [45, 188, 180, 210],
  aMijas: [71, 85, 105, 205],
  adelanteAndalucia: [44, 163, 118, 215],
  conAndalucia: [180, 83, 9, 215],
  sumar: [228, 93, 120, 215],
  pacma: [124, 190, 104, 210],
  iu: [172, 187, 62, 215],
  erc: [245, 158, 11, 215],
  junts: [14, 165, 233, 215],
  ehBildu: [132, 204, 22, 215],
  fallback: [116, 130, 150, 190],
} as const satisfies Record<string, readonly [number, number, number, number]>;

const isPresent = (value?: string | null): value is string =>
  typeof value === "string" && value.trim().length > 0;

const clean = (value?: string | null) =>
  isPresent(value) ? value.trim().replace(/^[•·●▪◦]+\s*/u, "").trim() : null;

function normalizePartyKey(value?: string | null) {
  const normalized = clean(value)
    ?.normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[“”]/g, '"')
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();

  return normalized ?? "";
}

export function normalizePartyName(value?: string | null) {
  const raw = clean(value);
  const key = normalizePartyKey(raw);

  if (!key) {
    return raw ?? "";
  }

  if (key === "PORA") {
    return "POR ANDALUCIA";
  }
  if (key === "P.P." || key === "P P" || key === "PARTIDO POPULAR") {
    return "PP";
  }
  if (key === "UPYD" || key === "UPYD.") {
    return "UPyD";
  }
  if (key === 'AGRUPACION DE ELECTORES "SE ACABO LA FIESTA"' || key === "SE ACABO LA FIESTA") {
    return "SE ACABO LA FIESTA";
  }
  if (key === "CIUDADANOS" || key === "CS.") {
    return "CS";
  }

  return raw ?? "";
}

function stripSectionPrefix(value?: string | null) {
  const normalized = clean(value);

  if (!normalized) {
    return null;
  }

  const stripped = normalized
    .replace(/^[•·●▪◦]\s*/u, "")
    .replace(/^(secci[oó]n|section)\s*\d+\s*[-:.]\s*/i, "")
    .replace(/^(secci[oó]n|section)\s*\d+\s+/i, "")
    .trim();

  return stripped || normalized;
}

function normalizeKnownSectionNames(value?: string | null) {
  const normalized = clean(value);

  if (!normalized) {
    return null;
  }

  if (normalized === "Sierrezuela (Las Lagunas)") {
    return "Sierrezuela";
  }

  return normalized;
}

export function getSectionDisplayName(
  detail?: SectionDetail | null,
  section?: SectionFeatureProperties | null,
) {
  const candidate =
    stripSectionPrefix(detail?.display.label_cliente) ??
    stripSectionPrefix(section?.label_cliente) ??
    stripSectionPrefix(detail?.display.section_name) ??
    stripSectionPrefix(section?.section_name) ??
    stripSectionPrefix(detail?.display.display_name) ??
    stripSectionPrefix(section?.display_name) ??
    clean(detail?.display.nombre_barrio) ??
    clean(detail?.display.neighborhood) ??
    clean(section?.nombre_barrio) ??
    clean(section?.neighborhood) ??
    clean(detail?.display.label) ??
    clean(section?.label) ??
    formatSectionSubtitle(detail?.display.section_number ?? section?.section_number) ??
    clean(detail?.display.section_id) ??
    clean(section?.section_id) ??
    "Selected Section";

  return normalizeKnownSectionNames(candidate) ?? "Selected Section";
}

export function formatSectionSubtitle(sectionNumber?: string | null) {
  const normalized = clean(sectionNumber);
  return normalized ? `Section ${normalized}` : null;
}

export function formatMunicipalitySectionSubtitle(
  municipality?: string | null,
  sectionNumber?: string | null,
) {
  const sectionSubtitle = formatSectionSubtitle(sectionNumber);
  const municipalityName = clean(municipality) ?? "Mijas";

  return sectionSubtitle ? `${municipalityName} - ${sectionSubtitle}` : municipalityName;
}

export function getActiveLayer(layers: Record<LayerKey, boolean>): LayerKey | null {
  return (Object.entries(layers).find(([, enabled]) => enabled)?.[0] as LayerKey | undefined) ?? null;
}

export function getSectionLayerColor(
  section: SectionFeatureProperties,
  activeLayer: LayerKey | null,
  landMetric: LandBuiltEnvironmentMetricKey = "populationDensity",
  territorialMetric: TerritorialMetricKey = "marketPressure",
  socioeconomicMetric: SocioeconomicMetricKey = "humanCapital",
) {
  if (activeLayer === "population") {
    return getPopulationDensityColor(section.population_density);
  }

  if (activeLayer === "ageStructure") {
    return getAverageAgeColor(section.average_age);
  }

  if (activeLayer === "electoralBehavior") {
    return rgbaToCss(getPartyColor(section.winning_party));
  }

  if (activeLayer === "incomeLevel") {
    return getIncomeLevelColor(section.income_quintile, section.renta_media_persona);
  }

  if (activeLayer === "landBuiltEnvironment") {
    return getLandBuiltEnvironmentColor(section, landMetric);
  }

  if (activeLayer === "housingIntelligence") {
    return getTerritorialColor(section, territorialMetric);
  }

  if (activeLayer === "socioeconomicIntelligence") {
    return getSocioeconomicColor(section, socioeconomicMetric);
  }

  if (activeLayer === "electoralForecasting") {
    return getCampaignForecastColor(section);
  }

  return DENSITY_COLOR_STOPS.blue;
}

export function normalizeNumber(value?: number | string | null) {
  if (value == null) {
    return null;
  }

  const numeric =
    typeof value === "string" ? Number(value.replace(/\./g, "").replace(",", ".")) : value;
  return Number.isFinite(numeric) ? numeric : null;
}

export function getPartyColor(winningParty?: string | null): [number, number, number, number] {
  const party = normalizePartyKey(normalizePartyName(winningParty));

  if (party === "PSOE" || party === "PSOE-A") {
    return [...PARTY_COLOR_STOPS.psoe];
  }
  if (party === "PP") {
    return [...PARTY_COLOR_STOPS.pp];
  }
  if (party === "VOX") {
    return [...PARTY_COLOR_STOPS.vox];
  }
  if (party === "CS") {
    return [...PARTY_COLOR_STOPS.cs];
  }
  if (party === "UPYD") {
    return [...PARTY_COLOR_STOPS.upyd];
  }
  if (party === "PODEMOS") {
    return [...PARTY_COLOR_STOPS.podemos];
  }
  if (party === "POR ANDALUCIA") {
    return [...PARTY_COLOR_STOPS.porAndalucia];
  }
  if (party === "SE ACABO LA FIESTA") {
    return [...PARTY_COLOR_STOPS.seAcaboLaFiesta];
  }
  if (party === "POR MI PUEBLO") {
    return [...PARTY_COLOR_STOPS.porMiPueblo];
  }
  if (party === "SOYDEMIJAS") {
    return [...PARTY_COLOR_STOPS.soyDeMijas];
  }
  if (party === "A.MIJAS-A.MIHA") {
    return [...PARTY_COLOR_STOPS.aMijas];
  }
  if (party === "ADELANTE ANDALUCIA") {
    return [...PARTY_COLOR_STOPS.adelanteAndalucia];
  }
  if (party === "CON ANDALUCIA") {
    return [...PARTY_COLOR_STOPS.conAndalucia];
  }
  if (party === "SUMAR") {
    return [...PARTY_COLOR_STOPS.sumar];
  }
  if (party === "PACMA") {
    return [...PARTY_COLOR_STOPS.pacma];
  }
  if (party === "IU" || party === "IZQUIERDA UNIDA") {
    return [...PARTY_COLOR_STOPS.iu];
  }
  if (party === "ERC") {
    return [...PARTY_COLOR_STOPS.erc];
  }
  if (party === "JUNTS") {
    return [...PARTY_COLOR_STOPS.junts];
  }
  if (party === "EH BILDU") {
    return [...PARTY_COLOR_STOPS.ehBildu];
  }

  return [...PARTY_COLOR_STOPS.fallback];
}

function normalizePercentScore(value?: number | string | null) {
  const normalized = normalizeNumber(value);
  if (normalized == null) {
    return null;
  }
  return Math.min(100, Math.max(0, normalized > 0 && normalized <= 1 ? normalized * 100 : normalized));
}

export function getCampaignForecastLeader(section?: SectionFeatureProperties | null) {
  return normalizePartyName(section?.projected_leading_party) || normalizePartyName(section?.winning_party) || "N/A";
}

export function getCampaignForecastVoteShare(section?: SectionFeatureProperties | null) {
  return normalizePercentScore(section?.projected_vote_share ?? section?.winning_party_pct);
}

export function getCampaignForecastMetricValue(
  section: SectionFeatureProperties | null | undefined,
  metric: CampaignForecastMetricKey,
): number | null {
  if (!section) {
    return null;
  }

  const explicitValue = normalizePercentScore(section[CAMPAIGN_FORECAST_METRICS[metric].field] as number | string | null);
  if (explicitValue != null) {
    return explicitValue;
  }

  const turnout = normalizePercentScore(section.turnout);
  const margin = Math.min(100, Math.max(0, normalizeNumber(section.victory_margin_pct) ?? 0));
  const localism = normalizePercentScore(section.localism_index ?? section.local_vote_pct);
  const fragmentation = Math.min(100, Math.max(0, (normalizeNumber(section.fragmentation_index) ?? 0) * 100));
  const competitiveParties = Math.min(100, Math.max(0, ((normalizeNumber(section.competitive_parties_count) ?? 0) / 5) * 100));

  if (metric === "abstentionRisk") {
    return turnout == null ? null : Math.max(0, 100 - turnout);
  }
  if (metric === "swingSections") {
    const closeness = Math.max(0, 100 - margin * 4);
    return Math.min(100, Math.max(0, closeness * 0.72 + competitiveParties * 0.28));
  }
  if (metric === "forecastConfidence") {
    const confidenceFromMargin = Math.min(100, 52 + margin * 3);
    const turnoutStability = turnout == null ? 50 : Math.min(100, Math.max(0, 100 - Math.abs(68 - turnout) * 1.2));
    return Math.min(100, Math.max(0, confidenceFromMargin * 0.68 + turnoutStability * 0.32));
  }
  if (metric === "localistPotential") {
    return localism;
  }
  if (metric === "volatility") {
    const swing: number = getCampaignForecastMetricValue(section, "swingSections") ?? 50;
    const abstention: number = getCampaignForecastMetricValue(section, "abstentionRisk") ?? 50;
    return Math.min(100, Math.max(0, swing * 0.48 + abstention * 0.27 + fragmentation * 0.25));
  }

  return null;
}

export function getCampaignForecastColor(section: SectionFeatureProperties) {
  return rgbaToCss(getPartyColor(getCampaignForecastLeader(section))).replace(/,\s*[\d.]+\)$/, ", 0.72)");
}

export function getCampaignForecastPartyExpression() {
  return [
    "match",
    ["upcase", ["coalesce", ["get", "projected_leading_party"], ["get", "winning_party"], ""]],
    "PSOE",
    "rgba(255, 82, 82, 0.72)",
    "PSOE-A",
    "rgba(255, 82, 82, 0.72)",
    "PP",
    "rgba(76, 157, 224, 0.72)",
    "P.P.",
    "rgba(76, 157, 224, 0.72)",
    "PARTIDO POPULAR",
    "rgba(76, 157, 224, 0.72)",
    "VOX",
    "rgba(111, 174, 90, 0.72)",
    "CS",
    "rgba(224, 126, 64, 0.72)",
    "POR MI PUEBLO",
    "rgba(145, 113, 210, 0.72)",
    "SOYDEMIJAS",
    "rgba(63, 190, 178, 0.72)",
    "A.MIJAS-A.MIHA",
    "rgba(214, 174, 74, 0.72)",
    "rgba(116, 130, 150, 0.62)",
  ] as unknown[];
}

export function rgbaToCss([red, green, blue, alpha]: readonly [number, number, number, number]) {
  return `rgba(${red}, ${green}, ${blue}, ${alpha / 255})`;
}

export function toPercentPoints(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }

  return Math.abs(value) <= 1 ? value * 100 : value;
}

export function parsePercentValue(value?: number | string | null) {
  if (value == null) {
    return null;
  }

  const numeric =
    typeof value === "string" ? Number(value.replace("%", "").replace(",", ".")) : value;

  return Number.isFinite(numeric) ? numeric : null;
}

export function normalizePercent(
  value?: number | string | null,
  scale: "fraction" | "points" = "fraction",
) {
  const numeric = parsePercentValue(value);
  if (numeric == null) {
    return 0;
  }

  if (scale === "fraction" && numeric >= 0 && numeric <= 1) {
    return numeric * 100;
  }

  return numeric;
}

function inferPercentScale(values: (number | string | null | undefined)[]) {
  const numericValues = values
    .map((value) => parsePercentValue(value))
    .filter((value): value is number => value != null);

  if (numericValues.length === 0) {
    return "points";
  }

  return numericValues.some((value) => Math.abs(value) > 1) ? "points" : "fraction";
}

type PartyVoteShareEntry = {
  party: string;
  percentage: number;
  votes?: number;
};

function normalizePartyShareEntries(entries: PartyVoteShareEntry[]) {
  const byParty = new Map<string, PartyVoteShareEntry>();

  entries.forEach((entry) => {
    const party = normalizePartyName(entry.party);
    if (!party || !Number.isFinite(entry.percentage)) {
      return;
    }

    const current = byParty.get(party);
    if (current) {
      current.percentage += entry.percentage;
      current.votes = (current.votes ?? 0) + (entry.votes ?? 0);
      return;
    }

    byParty.set(party, { ...entry, party });
  });

  return Array.from(byParty.values()).sort(
    (a, b) => b.percentage - a.percentage || (b.votes ?? 0) - (a.votes ?? 0),
  );
}

export function formatPercentPoint(value?: number | null) {
  const percent = typeof value === "number" ? toPercentPoints(value) : null;
  return percent == null ? "N/A" : `${percent.toFixed(1)}%`;
}

export function normalizePercentagePoints(value?: number | string | null) {
  const numeric = parsePercentValue(value);
  if (numeric == null) {
    return 0;
  }

  const absolute = Math.abs(numeric);

  if (absolute > 0 && absolute < 0.1) {
    return numeric * 100;
  }

  if (absolute > 50 && absolute <= 100) {
    return numeric / 100;
  }

  return numeric;
}

export function formatSignedPointMargin(value?: number | string | null) {
  if (parsePercentValue(value) == null) {
    return "N/D";
  }

  const margin = normalizePercentagePoints(value);
  return `${margin >= 0 ? "+" : ""}${margin.toFixed(1)} pp`;
}

export function getLocalismCategory(value?: number | string | null) {
  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }

  const percent = typeof value === "number" ? toPercentPoints(value) : null;
  if (percent == null) {
    return "N/D";
  }
  if (percent < 10) {
    return "Bajo";
  }
  if (percent < 20) {
    return "Moderado";
  }
  if (percent < 30) {
    return "Alto";
  }

  return "Muy alto";
}

export function getPartyVoteShare(section: SectionFeatureProperties) {
  const partyResults = section.party_results_json ?? [];
  if (partyResults.length > 0) {
    const scale = inferPercentScale(
      partyResults.map((entry) => entry.pct ?? entry.percentage ?? entry.vote_share),
    );

    return normalizePartyShareEntries(
      partyResults
        .map((entry) => {
          const rawPercentage = entry.pct ?? entry.percentage ?? entry.vote_share;
          const percentage = normalizePercent(rawPercentage, scale);
          const votes = parsePercentValue(entry.votes);

          return {
            party: normalizePartyName(entry.party),
            hasPercentage: parsePercentValue(rawPercentage) != null,
            percentage,
            votes: votes ?? undefined,
          };
        })
        .filter((entry) => entry.party && entry.hasPercentage && Number.isFinite(entry.percentage)),
    );
  }

  const fromApi = section.party_vote_percentages ?? [];
  if (fromApi.length > 0) {
    const scale = inferPercentScale(fromApi.map((entry) => entry.percentage));

    return normalizePartyShareEntries(
      fromApi
        .map((entry) => ({
          party: normalizePartyName(entry.party),
          percentage: normalizePercent(entry.percentage, scale),
        }))
        .filter((entry) => entry.party && Number.isFinite(entry.percentage)),
    );
  }

  const fallbackPercentages = [
    section.pct_pp,
    section.pct_psoe,
    section.pct_vox,
    section.pct_cs,
    section.pct_pacma,
    section.pct_por_mi_pueblo,
    section.pct_soydemijas,
    section.pct_a_mijas,
    section.pct_adelante_andalucia,
    section.pct_con_andalucia,
  ];
  const scale = inferPercentScale(fallbackPercentages);

  return [
    ["PP", section.pct_pp],
    ["PSOE-A", section.pct_psoe],
    ["VOX", section.pct_vox],
    ["CS", section.pct_cs],
    ["PACMA", section.pct_pacma],
    ["POR MI PUEBLO", section.pct_por_mi_pueblo],
    ["SOYDEMIJAS", section.pct_soydemijas],
    ["A.MIJAS-A.MIHA", section.pct_a_mijas],
    ["ADELANTE ANDALUCÍA", section.pct_adelante_andalucia],
    ["CON ANDALUCÍA", section.pct_con_andalucia],
  ]
    .map(([party, value]) => ({
      party: normalizePartyName(String(party)),
      percentage: parsePercentValue(value) == null ? null : normalizePercent(value, scale),
    }))
    .filter(
      (entry): entry is { party: string; percentage: number } => entry.percentage != null,
    )
    .sort((a, b) => b.percentage - a.percentage);
}

export function getPopulationDensityColor(value?: number | null) {
  const density = typeof value === "number" ? value : 0;

  if (density >= 40000) {
    return DENSITY_COLOR_STOPS.violet;
  }
  if (density >= 25000) {
    return DENSITY_COLOR_STOPS.red;
  }
  if (density >= 10000) {
    return DENSITY_COLOR_STOPS.yellow;
  }
  if (density >= 1000) {
    return DENSITY_COLOR_STOPS.sky;
  }

  return DENSITY_COLOR_STOPS.blue;
}

export function getPopulationDensityExpression() {
  return [
    "step",
    ["coalesce", ["to-number", ["get", "population_density"]], 0],
    DENSITY_COLOR_STOPS.blue,
    1000,
    DENSITY_COLOR_STOPS.sky,
    10000,
    DENSITY_COLOR_STOPS.yellow,
    25000,
    DENSITY_COLOR_STOPS.red,
    40000,
    DENSITY_COLOR_STOPS.violet,
  ] as unknown[];
}

export function getAverageAgeColor(value?: number | null) {
  const averageAge = typeof value === "number" ? value : null;

  if (averageAge == null) {
    return "#64748B";
  }
  if (averageAge > 44.5) {
    return AGE_STRUCTURE_COLOR_STOPS.senior;
  }
  if (averageAge >= 42) {
    return AGE_STRUCTURE_COLOR_STOPS.mature;
  }
  if (averageAge >= 39) {
    return AGE_STRUCTURE_COLOR_STOPS.balanced;
  }
  if (averageAge >= 36) {
    return AGE_STRUCTURE_COLOR_STOPS.youngAdult;
  }

  return AGE_STRUCTURE_COLOR_STOPS.veryYoung;
}

export function getAverageAgeExpression() {
  return [
    "step",
    ["coalesce", ["to-number", ["get", "average_age"]], -1],
    "#64748B",
    0,
    AGE_STRUCTURE_COLOR_STOPS.veryYoung,
    36,
    AGE_STRUCTURE_COLOR_STOPS.youngAdult,
    39,
    AGE_STRUCTURE_COLOR_STOPS.balanced,
    42,
    AGE_STRUCTURE_COLOR_STOPS.mature,
    44.500001,
    AGE_STRUCTURE_COLOR_STOPS.senior,
  ] as unknown[];
}

export function getIncomeLevelLabel(quintile?: number | null) {
  switch (quintile) {
    case 1:
      return "Renta muy baja";
    case 2:
      return "Renta baja";
    case 3:
      return "Renta media";
    case 4:
      return "Renta alta";
    case 5:
      return "Renta muy alta";
    default:
      return "N/D";
  }
}

export function getIncomeLevelColor(quintile?: number | null, income?: number | null) {
  const group = typeof quintile === "number" ? quintile : null;

  if (group === 1) {
    return INCOME_LEVEL_COLOR_STOPS.veryLow;
  }
  if (group === 2) {
    return INCOME_LEVEL_COLOR_STOPS.low;
  }
  if (group === 3) {
    return INCOME_LEVEL_COLOR_STOPS.medium;
  }
  if (group === 4) {
    return INCOME_LEVEL_COLOR_STOPS.high;
  }
  if (group === 5) {
    return INCOME_LEVEL_COLOR_STOPS.veryHigh;
  }

  return typeof income === "number" ? INCOME_LEVEL_COLOR_STOPS.medium : INCOME_LEVEL_COLOR_STOPS.fallback;
}

export function getIncomeLevelExpression() {
  return [
    "match",
    ["to-number", ["coalesce", ["get", "income_quintile"], 0]],
    1,
    INCOME_LEVEL_COLOR_STOPS.veryLow,
    2,
    INCOME_LEVEL_COLOR_STOPS.low,
    3,
    INCOME_LEVEL_COLOR_STOPS.medium,
    4,
    INCOME_LEVEL_COLOR_STOPS.high,
    5,
    INCOME_LEVEL_COLOR_STOPS.veryHigh,
    INCOME_LEVEL_COLOR_STOPS.fallback,
  ] as unknown[];
}

export function formatEuro(value?: number | null) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "N/A";
  }

  return `${Math.round(value).toLocaleString("en-US")} €`;
}

export function formatEuroPerM2(value?: number | string | null) {
  const numeric = normalizeNumber(value);
  if (numeric == null) {
    return "N/A";
  }

  return `${Math.round(numeric).toLocaleString("es-ES")} €/m²`;
}

export function formatScore(value?: number | string | null) {
  const numeric = normalizeNumber(value);
  return numeric == null ? "N/A" : `${Math.round(numeric)} / 100`;
}

export function formatRatio(value?: number | string | null) {
  const numeric = normalizeNumber(value);
  if (numeric == null) {
    return "N/A";
  }

  return `${numeric.toFixed(2)}x`;
}

export function formatScorePercent(value?: number | string | null) {
  const numeric = normalizeNumber(value);
  if (numeric == null) {
    return "N/A";
  }

  const normalized = numeric > 0 && numeric <= 1 ? numeric * 100 : numeric;
  const clamped = Math.min(100, Math.max(0, normalized));
  const fixed = clamped.toFixed(1);
  const [integerPart, decimalPart] = fixed.split(".");
  return `${integerPart.padStart(2, "0")}.${decimalPart}%`;
}

export function getRealEstateMetricValue(
  section: SectionFeatureProperties,
  metric: RealEstateMetricKey,
) {
  return normalizeNumber(section[REAL_ESTATE_METRICS[metric].field] as number | string | null);
}

export function hasRealEstateEstimate(section: SectionFeatureProperties) {
  return (
    getRealEstateMetricValue(section, "cadastralValue") != null ||
    getRealEstateMetricValue(section, "marketPrice") != null ||
    getRealEstateMetricValue(section, "marketCadastreRatio") != null
  );
}

export function formatRealEstateMetricValue(value: number | null, metric: RealEstateMetricKey) {
  return REAL_ESTATE_METRICS[metric].unit === "ratio"
    ? formatRatio(value)
    : formatEuroPerM2(value);
}

export function getRealEstateClassificationLabel(value?: string | null) {
  const normalized = value?.trim().toLowerCase();

  switch (normalized) {
    case "sobrecalentada":
      return "Overheated";
    case "oportunidad_inmobiliaria":
      return "Opportunity";
    case "infravalorada":
      return "Undervalued";
    case "alineada":
      return "Aligned";
    case "zona_prime":
      return "Prime Zone";
    case "zona_dinamica":
      return "Dynamic Zone";
    case "zona_expansion":
      return "Expansion Zone";
    case "zona_estable":
      return "Stable Zone";
    default:
      return normalized ? normalized.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "N/A";
  }
}

export function getRealEstateClassificationTone(value?: string | null) {
  const normalized = value?.trim().toLowerCase();

  if (normalized === "sobrecalentada") {
    return "border-rose-300/25 bg-rose-300/10 text-rose-100";
  }
  if (normalized === "oportunidad_inmobiliaria" || normalized === "infravalorada") {
    return "border-cyan-300/25 bg-cyan-300/10 text-cyan-100";
  }
  if (normalized === "zona_prime" || normalized === "zona_dinamica") {
    return "border-amber-300/25 bg-amber-300/10 text-amber-100";
  }

  return "border-white/10 bg-white/[0.06] text-slate-100";
}

export function getTerritorialMetricValue(
  section: SectionFeatureProperties,
  metric: TerritorialMetricKey,
) {
  return normalizeNumber(section[TERRITORIAL_METRICS[metric].field] as number | string | null);
}

export function getSocioeconomicMetricValue(
  section: SectionFeatureProperties,
  metric: SocioeconomicMetricKey,
) {
  return normalizeNumber(section[SOCIOECONOMIC_METRICS[metric].field] as number | string | null);
}

export function getSocioeconomicMetricLabel(
  section: SectionFeatureProperties,
  metric: SocioeconomicMetricKey,
) {
  const value = section[SOCIOECONOMIC_METRICS[metric].labelField];
  return typeof value === "string" && value.trim().length > 0 ? value : "N/A";
}

export function getSocioeconomicCompleteness(
  section: SectionFeatureProperties,
  metric: SocioeconomicMetricKey,
) {
  return normalizeNumber(section[SOCIOECONOMIC_METRICS[metric].completenessField] as number | string | null);
}

export function getLandBuiltEnvironmentMetricValue(
  section: SectionFeatureProperties,
  metric: LandBuiltEnvironmentMetricKey,
) {
  const normalizedMetric = normalizeLandBuiltEnvironmentMetric(metric);
  return normalizeNumber(section[LAND_BUILT_ENVIRONMENT_METRICS[normalizedMetric].field] as number | string | null);
}

export function formatLandBuiltEnvironmentMetricValue(
  value: number | null,
  metric: LandBuiltEnvironmentMetricKey,
) {
  const normalizedMetric = normalizeLandBuiltEnvironmentMetric(metric);
  const unit = LAND_BUILT_ENVIRONMENT_METRICS[normalizedMetric].unit;
  if (unit === "density") {
    return value == null ? "N/A" : `${Math.round(value).toLocaleString("es-ES")} / km²`;
  }
  if (unit === "parcelDensity") {
    return value == null ? "N/A" : `${value.toLocaleString("es-ES", { maximumFractionDigits: 1 })} parcels / km²`;
  }
  if (unit === "m2") {
    return value == null ? "N/A" : `${Math.round(value).toLocaleString("es-ES")} m²`;
  }
  if (unit === "percentage") {
    return value == null ? "N/A" : `${(Math.max(0, value) * 100).toFixed(1)}%`;
  }
  if (unit === "index") {
    return formatScorePercent(value);
  }

  return formatRatio(value);
}

export function hasLandBuiltEnvironment(section: SectionFeatureProperties) {
  return (
    getLandBuiltEnvironmentMetricValue(section, "populationDensity") != null ||
    getLandBuiltEnvironmentMetricValue(section, "parcelDensity") != null ||
    getLandBuiltEnvironmentMetricValue(section, "builtFootprint") != null ||
    getLandBuiltEnvironmentMetricValue(section, "avgPlotSize") != null ||
    getLandBuiltEnvironmentMetricValue(section, "buildingIntensity") != null ||
    getLandBuiltEnvironmentMetricValue(section, "urbanIntensity") != null
  );
}

export function getLandBuiltEnvironmentColor(
  section: SectionFeatureProperties,
  metric: LandBuiltEnvironmentMetricKey,
) {
  const bucket = normalizeNumber(section.land_built_environment_bucket);
  const normalizedMetric = normalizeLandBuiltEnvironmentMetric(metric);
  const colors = LAND_BUILT_ENVIRONMENT_COLOR_STOPS[normalizedMetric];
  if (bucket == null) {
    return "#667085";
  }

  return colors[Math.min(4, Math.max(0, bucket - 1))];
}

export function getTerritorialMetricLabel(
  section: SectionFeatureProperties,
  metric: TerritorialMetricKey,
) {
  const value = section[TERRITORIAL_METRICS[metric].labelField];
  return typeof value === "string" && value.trim().length > 0 ? value : "N/A";
}

export function hasTerritorialSignal(section: SectionFeatureProperties) {
  return (
    getTerritorialMetricValue(section, "qualityLife") != null ||
    getTerritorialMetricValue(section, "territorialSignal") != null ||
    getTerritorialMetricValue(section, "marketPressure") != null ||
    getTerritorialMetricValue(section, "opportunitySignal") != null
  );
}

export function hasSocioeconomicSignal(section: SectionFeatureProperties) {
  return (
    getSocioeconomicMetricValue(section, "humanCapital") != null ||
    getSocioeconomicMetricValue(section, "vulnerability") != null ||
    getSocioeconomicMetricValue(section, "resilience") != null ||
    getSocioeconomicMetricValue(section, "productiveComplexity") != null ||
    getSocioeconomicMetricValue(section, "inequalityPressure") != null
  );
}

export function getTerritorialColor(
  section: SectionFeatureProperties,
  metric: TerritorialMetricKey,
) {
  const value = getTerritorialMetricValue(section, metric);
  if (value == null) {
    return "#667085";
  }

  const colors = TERRITORIAL_METRICS[metric].colors;
  const index = Math.min(4, Math.max(0, Math.floor(value / 20)));
  return colors[index];
}

export function getSocioeconomicColor(
  section: SectionFeatureProperties,
  metric: SocioeconomicMetricKey,
) {
  const value = getSocioeconomicMetricValue(section, metric);
  if (value == null) {
    return "#667085";
  }

  const colors = SOCIOECONOMIC_METRICS[metric].colors;
  const index = Math.min(4, Math.max(0, Math.floor(value / 20)));
  return colors[index];
}

export function getTerritorialExpression(metric: TerritorialMetricKey) {
  const colors = TERRITORIAL_METRICS[metric].colors;
  const field = TERRITORIAL_METRICS[metric].field;

  return [
    "interpolate",
    ["linear"],
    ["to-number", ["coalesce", ["get", field], 0]],
    0,
    colors[0],
    25,
    colors[1],
    50,
    colors[2],
    75,
    colors[3],
    100,
    colors[4],
  ] as unknown[];
}

export function getSocioeconomicExpression(metric: SocioeconomicMetricKey) {
  const colors = SOCIOECONOMIC_METRICS[metric].colors;
  const field = SOCIOECONOMIC_METRICS[metric].field;

  return [
    "interpolate",
    ["linear"],
    ["to-number", ["coalesce", ["get", field], 0]],
    0,
    colors[0],
    25,
    colors[1],
    50,
    colors[2],
    75,
    colors[3],
    100,
    colors[4],
  ] as unknown[];
}

export function buildTerritorialLegend(metric: TerritorialMetricKey): TerritorialLegend {
  const config = TERRITORIAL_METRICS[metric];
  return {
    title: config.title,
    subtitle: "0-100 section-level signal",
    labels: config.labels,
    items: config.colors.map((color, index) => ({
      color,
      label: `${index * 20}-${index === 4 ? 100 : (index + 1) * 20}`,
    })),
  };
}

export function buildLandBuiltEnvironmentLegend(
  metric: LandBuiltEnvironmentMetricKey,
): LandBuiltEnvironmentLegend {
  const normalizedMetric = normalizeLandBuiltEnvironmentMetric(metric);
  const config = LAND_BUILT_ENVIRONMENT_METRICS[normalizedMetric];
  return {
    title: "Territorio / entorno construido",
    subtitle: config.title,
    labels: ["Muy baja", "Media", "Muy alta"],
    items: LAND_BUILT_ENVIRONMENT_COLOR_STOPS[normalizedMetric].map((color, index) => ({
      color,
      label: ["Muy baja", "Baja", "Media", "Alta", "Muy alta"][index],
    })),
  };
}

export function buildSocioeconomicLegend(metric: SocioeconomicMetricKey): SocioeconomicLegend {
  const config = SOCIOECONOMIC_METRICS[metric];
  return {
    title: "Inteligencia socioeconómica",
    subtitle: config.title,
    labels: ["Muy baja", "Media", "Muy alta"],
    items: config.colors.map((color, index) => ({
      color,
      label: ["Muy baja", "Baja", "Media", "Alta", "Muy alta"][index],
    })),
  };
}

export function buildLandBuiltEnvironmentPresentation(
  collection: SectionFeatureCollection | null,
  metric: LandBuiltEnvironmentMetricKey,
) {
  if (!collection) {
    return { collection, legend: null };
  }

  const values = collection.features
    .map((feature) => getLandBuiltEnvironmentMetricValue(feature.properties, metric))
    .filter((value): value is number => value != null);

  if (values.length === 0) {
    return {
      collection: {
        ...collection,
        features: collection.features.map((feature): SectionFeature => ({
          ...feature,
          properties: { ...feature.properties, land_built_environment_bucket: null },
        })),
      },
      legend: null,
    };
  }

  const breaks = getQuantileBreaks(values);
  const normalizedMetric = normalizeLandBuiltEnvironmentMetric(metric);
  const colors = LAND_BUILT_ENVIRONMENT_COLOR_STOPS[normalizedMetric];

  return {
    collection: {
      ...collection,
      features: collection.features.map((feature): SectionFeature => {
        const value = getLandBuiltEnvironmentMetricValue(feature.properties, metric);
        return {
          ...feature,
          properties: {
            ...feature.properties,
            land_built_environment_bucket: getBucket(value, breaks),
          },
        };
      }),
    },
    legend: buildLandBuiltEnvironmentLegend(metric),
  };
}

export function getStrategicReading(section: SectionFeatureProperties) {
  const pressure = getTerritorialMetricValue(section, "marketPressure") ?? 0;
  const opportunity = getTerritorialMetricValue(section, "opportunitySignal") ?? 0;
  const saturation = getTerritorialMetricValue(section, "residentialSaturation") ?? 0;
  const prestige = getTerritorialMetricValue(section, "urbanPrestige") ?? 0;
  const foreignDemand = getTerritorialMetricValue(section, "foreignDemand") ?? 0;

  if (prestige >= 70 && foreignDemand >= 70) {
    return "Perfil premium con demanda internacional.";
  }
  if (pressure >= 70 && opportunity >= 70) {
    return "Zona de alta demanda con potencial estratégico de expansión.";
  }
  if (pressure >= 70 && saturation >= 70) {
    return "Zona consolidada de alta presión con capacidad física limitada.";
  }
  if (opportunity >= 65 && pressure >= 40 && pressure < 70) {
    return "Emerging section with room for strategic positioning.";
  }
  if (saturation >= 70 && opportunity < 45) {
    return "Mature urban area with limited upside.";
  }

  return "Balanced section profile for comparative territorial monitoring.";
}

function getQuantileBreaks(values: number[]) {
  const sortedValues = [...values].sort((a, b) => a - b);
  const maxIndex = sortedValues.length - 1;
  return [1, 2, 3, 4].map((bucket) => {
    const index = Math.min(maxIndex, Math.ceil((bucket / 5) * sortedValues.length) - 1);
    return sortedValues[index];
  });
}

function getBucket(value: number | null, breaks: number[]) {
  if (value == null) {
    return null;
  }

  return breaks.reduce((bucket, threshold) => (value > threshold ? bucket + 1 : bucket), 1);
}

function formatRangeLabel(
  min: number,
  max: number,
  metric: RealEstateMetricKey,
  first: boolean,
  last: boolean,
) {
  if (first) {
    return `≤ ${formatRealEstateMetricValue(max, metric)}`;
  }
  if (last) {
    return `≥ ${formatRealEstateMetricValue(min, metric)}`;
  }

  return `${formatRealEstateMetricValue(min, metric)} - ${formatRealEstateMetricValue(max, metric)}`;
}

export function buildRealEstatePresentation(
  collection: SectionFeatureCollection | null,
  metric: RealEstateMetricKey,
) {
  if (!collection) {
    return {
      collection,
      legend: null,
    };
  }

  const values = collection.features
    .map((feature) => getRealEstateMetricValue(feature.properties, metric))
    .filter((value): value is number => value != null);

  if (values.length === 0) {
    return {
      collection: {
        ...collection,
        features: collection.features.map((feature): SectionFeature => ({
          ...feature,
          properties: { ...feature.properties, real_estate_bucket: null },
        })),
      },
      legend: null,
    };
  }

  const breaks = getQuantileBreaks(values);
  const colors = REAL_ESTATE_COLOR_STOPS[metric];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const rangeEdges = [min, ...breaks, max];

  return {
    collection: {
      ...collection,
      features: collection.features.map((feature): SectionFeature => {
        const value = getRealEstateMetricValue(feature.properties, metric);
        return {
          ...feature,
          properties: {
            ...feature.properties,
            real_estate_bucket: getBucket(value, breaks),
          },
        };
      }),
    },
    legend: {
      title: REAL_ESTATE_METRICS[metric].title,
      unit: REAL_ESTATE_METRICS[metric].unit === "ratio" ? "ratio x" : "€/m²",
      items: colors.map((color, index) => ({
        color,
        label: formatRangeLabel(
          rangeEdges[index],
          rangeEdges[index + 1],
          metric,
          index === 0,
          index === colors.length - 1,
        ),
      })),
    } satisfies RealEstateLegend,
  };
}

export function getPartyColorExpression() {
  return [
    "match",
    ["upcase", ["coalesce", ["get", "winning_party"], ""]],
    "PSOE",
    rgbaToCss(PARTY_COLOR_STOPS.psoe),
    "PSOE-A",
    rgbaToCss(PARTY_COLOR_STOPS.psoe),
    "PP",
    rgbaToCss(PARTY_COLOR_STOPS.pp),
    "P.P.",
    rgbaToCss(PARTY_COLOR_STOPS.pp),
    "PARTIDO POPULAR",
    rgbaToCss(PARTY_COLOR_STOPS.pp),
    "VOX",
    rgbaToCss(PARTY_COLOR_STOPS.vox),
    "CS",
    rgbaToCss(PARTY_COLOR_STOPS.cs),
    "CS.",
    rgbaToCss(PARTY_COLOR_STOPS.cs),
    "CIUDADANOS",
    rgbaToCss(PARTY_COLOR_STOPS.cs),
    "UPYD",
    rgbaToCss(PARTY_COLOR_STOPS.upyd),
    "PODEMOS",
    rgbaToCss(PARTY_COLOR_STOPS.podemos),
    "PORA",
    rgbaToCss(PARTY_COLOR_STOPS.porAndalucia),
    "POR ANDALUCIA",
    rgbaToCss(PARTY_COLOR_STOPS.porAndalucia),
    'AGRUPACIÓN DE ELECTORES "SE ACABÓ LA FIESTA"',
    rgbaToCss(PARTY_COLOR_STOPS.seAcaboLaFiesta),
    'AGRUPACION DE ELECTORES "SE ACABO LA FIESTA"',
    rgbaToCss(PARTY_COLOR_STOPS.seAcaboLaFiesta),
    "SE ACABO LA FIESTA",
    rgbaToCss(PARTY_COLOR_STOPS.seAcaboLaFiesta),
    "POR MI PUEBLO",
    rgbaToCss(PARTY_COLOR_STOPS.porMiPueblo),
    "SOYDEMIJAS",
    rgbaToCss(PARTY_COLOR_STOPS.soyDeMijas),
    "A.MIJAS-A.MIHA",
    rgbaToCss(PARTY_COLOR_STOPS.aMijas),
    "ADELANTE ANDALUCÍA",
    rgbaToCss(PARTY_COLOR_STOPS.adelanteAndalucia),
    "CON ANDALUCÍA",
    rgbaToCss(PARTY_COLOR_STOPS.conAndalucia),
    "SUMAR",
    rgbaToCss(PARTY_COLOR_STOPS.sumar),
    "PACMA",
    rgbaToCss(PARTY_COLOR_STOPS.pacma),
    "IU",
    rgbaToCss(PARTY_COLOR_STOPS.iu),
    "IZQUIERDA UNIDA",
    rgbaToCss(PARTY_COLOR_STOPS.iu),
    "ERC",
    rgbaToCss(PARTY_COLOR_STOPS.erc),
    "JUNTS",
    rgbaToCss(PARTY_COLOR_STOPS.junts),
    "EH BILDU",
    rgbaToCss(PARTY_COLOR_STOPS.ehBildu),
    rgbaToCss(PARTY_COLOR_STOPS.fallback),
  ] as unknown[];
}

export function getRealEstateExpression(metric: RealEstateMetricKey) {
  const colors = REAL_ESTATE_COLOR_STOPS[metric];

  return [
    "match",
    ["to-number", ["coalesce", ["get", "real_estate_bucket"], 0]],
    1,
    colors[0],
    2,
    colors[1],
    3,
    colors[2],
    4,
    colors[3],
    5,
    colors[4],
    "#667085",
  ] as unknown[];
}

export function getLandBuiltEnvironmentExpression(metric: LandBuiltEnvironmentMetricKey) {
  const normalizedMetric = normalizeLandBuiltEnvironmentMetric(metric);
  const colors = LAND_BUILT_ENVIRONMENT_COLOR_STOPS[normalizedMetric];

  return [
    "match",
    ["to-number", ["coalesce", ["get", "land_built_environment_bucket"], 0]],
    1,
    colors[0],
    2,
    colors[1],
    3,
    colors[2],
    4,
    colors[3],
    5,
    colors[4],
    "#667085",
  ] as unknown[];
}

export function getLayerFillExpression(
  activeLayer: LayerKey | null,
  realEstateMetric: RealEstateMetricKey = "marketCadastreRatio",
  territorialMetric: TerritorialMetricKey = "marketPressure",
  landBuiltEnvironmentMetric: LandBuiltEnvironmentMetricKey = "populationDensity",
  socioeconomicMetric: SocioeconomicMetricKey = "humanCapital",
) {
  if (activeLayer === "ageStructure") {
    return getAverageAgeExpression();
  }

  if (activeLayer === "electoralBehavior") {
    return getPartyColorExpression();
  }

  if (activeLayer === "incomeLevel") {
    return getIncomeLevelExpression();
  }

  if (activeLayer === "landBuiltEnvironment") {
    return getLandBuiltEnvironmentExpression(landBuiltEnvironmentMetric);
  }

  if (activeLayer === "housingIntelligence") {
    return getTerritorialExpression(territorialMetric);
  }

  if (activeLayer === "socioeconomicIntelligence") {
    return getSocioeconomicExpression(socioeconomicMetric);
  }

  if (activeLayer === "electoralForecasting") {
    return getCampaignForecastPartyExpression();
  }

  return getPopulationDensityExpression();
}
