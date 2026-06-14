import { calculateDHondtSeats } from "@/features/ask-soctrace/services/electoralCalculations";
import type { ElectoralScenarioId, SectionFeatureCollection, SectionFeatureProperties } from "@/types/api";

export type CampaignScenario = {
  id: ElectoralScenarioId;
  name: string;
  label: string;
  description: string;
  contextualForecastCopy: string;
  assumptions: string;
  targetSeats: Record<string, number>;
  voteShare: Record<string, number>;
  sectionProjections: Array<{
    sectionId: string;
    sectionName: string;
    parties: Record<string, number>;
    indicators?: {
      swing?: number;
      localist?: number;
      volatility?: number;
      confidence?: number;
    };
  }>;
  dhondtValidation: {
    seats: Record<string, number>;
    matchesTarget: boolean;
  };
};

const COUNCIL_SEATS = 25;
const THRESHOLD_PCT = 5;

const scenarioDefinitions: Array<{
  id: ElectoralScenarioId;
  name: string;
  description: string;
  contextualForecastCopy: string;
  assumptions: string;
  targetSeats: Record<string, number>;
  voteShare: Record<string, number>;
}> = [
  {
    id: "structural" as const,
    name: "Estructural",
    description: "Proyección estructural municipal 2027:",
    contextualForecastCopy:
      "PSOE sería el principal receptor del anterior votante local de Cs, a su vez PP y VOX serían los principales receptores de quienes votaron a PmP en 2023.",
    assumptions:
      "Proyección realizada considerando que las tendencias de voto se mantienen desde los comicios de 2015 en base a la evolución del resto de variables socioeconómicas.",
    targetSeats: { PSOE: 11, PP: 10, VOX: 4 },
    voteShare: { PSOE: 41, PP: 38, VOX: 16 },
  },
  {
    id: "candidate_reset" as const,
    name: "Nuevo liderazgo conservador",
    description: "Escenario de candidatura renovada en el PP:",
    contextualForecastCopy:
      "El PP se recupera dejando atrás el desgaste del anterior líder e impulsado por las tendencias ideológicas en otros comicios. El PSOE frena el desgaste estructural nacional con la suma de votos provenientes de Cs y nuevos votantes.",
    assumptions:
      "Considerando la actual tendencia de voto, se calculan mediante contrapesos el impacto favorable de una candidatura renovada en el PP. Esto se calcula considerando las tendencias de voto por sección en otros comicios, no solo municipales.",
    targetSeats: { PP: 12, PSOE: 9, VOX: 4 },
    voteShare: { PP: 43, PSOE: 34, VOX: 15 },
  },
  {
    id: "localist_fragmentation" as const,
    name: "Segmentación localista",
    description: "Escenario de fragmentación conservadora y entrada progresista:",
    contextualForecastCopy:
      "PSOE crece ligeramente con la incursión del votante de Cs, PP sufre el desgaste de la entrada del anterior líder local conservador. Impacto con la presencia en el pleno de Adelante Andalucía entre el votante que espera escenarios políticos renovados.",
    assumptions:
      "Considera el desgaste del PP con la incursión localista conservadora del exalcalde conservador, la incursión de Adelante Andalucía en la banda progresista y la intención de voto de los hasta ahora votantes de Cs.",
    targetSeats: { PSOE: 10, PP: 8, VOX: 3, "Adelante Andalucía": 2, "Mijas 100%": 2 },
    voteShare: { PSOE: 36, PP: 29, VOX: 12, "Adelante Andalucía": 8, "Mijas 100%": 7 },
  },
  {
    id: "oraculum_ready" as const,
    name: "Oraculum",
    description: "Escenario mixto con capa de validación de sondeos:",
    contextualForecastCopy:
      "El PP haría valer su candidatura renovada y las tendencias de otros comicios para ser la formación más votada. PSOE mantendría su porcentaje de voto. Adelante Andalucía y Mijas 100% principales novedades, aunque con impacto menor para los localistas conservadores.",
    assumptions:
      "Incorpora la capa de sondeos de validación sobre la proyección estructural y la consideración de las tendencias de voto de los escenarios anteriores.",
    targetSeats: { PP: 10, PSOE: 9, VOX: 3, "Adelante Andalucía": 2, "Mijas 100%": 1 },
    voteShare: { PP: 37, PSOE: 34, VOX: 12, "Adelante Andalucía": 8, "Mijas 100%": 5.5 },
  },
];

const primaryLocalistSections = new Set(["31", "23", "27"]);
const secondaryLocalistSections = new Set(["37", "25", "07", "7", "30", "22"]);
const progressiveBoostSections = new Set(["01", "1", "02", "2"]);

function sectionNumber(section: SectionFeatureProperties) {
  return String(section.section_number ?? section.section_id?.slice(-2) ?? "").replace(/^0+/, "") || "";
}

function sectionLabel(section: SectionFeatureProperties) {
  return section.label_cliente ?? `Seccion ${section.section_number ?? section.section_id}`;
}

function score(value?: number | null, fallback = 50) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function baseIndicators(section: SectionFeatureProperties) {
  return {
    swing: score(section.swing_sections),
    localist: score(section.localist_potential),
    volatility: score(section.volatility),
    confidence: score(section.forecast_confidence),
  };
}

function sectionDeltas(scenarioId: ElectoralScenarioId, section: SectionFeatureProperties) {
  const indicators = baseIndicators(section);
  const number = sectionNumber(section);
  const localistPrimary = primaryLocalistSections.has(number);
  const localistSecondary = secondaryLocalistSections.has(number);
  const progressiveArea = progressiveBoostSections.has(number);
  const localistWeight =
    (indicators.localist - 50) / 18 +
    (indicators.volatility - 50) / 35 +
    (localistPrimary ? 2.8 : 0) +
    (localistSecondary ? 1.4 : 0);
  const progressiveWeight =
    (indicators.swing - 50) / 42 +
    (progressiveArea ? 2.4 : 0) +
    (number === "1" || number === "2" ? 0.6 : 0);

  if (scenarioId === "candidate_reset") {
    const conservativePotential = Math.max(0, (score(section.right_bloc_pct, 50) - 45) / 14);
    return { PP: 1.5 + conservativePotential, PSOE: -1.1, VOX: -0.4 };
  }
  if (scenarioId === "localist_fragmentation") {
    const mijas100 = Math.max(0, localistWeight);
    const adelante = Math.max(0, progressiveWeight);
    return {
      "Mijas 100%": mijas100,
      "Adelante Andalucía": adelante,
      PP: -mijas100 * 0.85,
      PSOE: -adelante * 0.75,
      VOX: -mijas100 * 0.15,
    };
  }
  if (scenarioId === "oraculum_ready") {
    const mijas100 = Math.max(0, localistWeight) * 0.55;
    const adelante = Math.max(0, progressiveWeight) * 0.7;
    return {
      "Mijas 100%": mijas100,
      "Adelante Andalucía": adelante,
      PP: -mijas100 * 0.75 + 0.5,
      PSOE: -adelante * 0.55,
      VOX: -mijas100 * 0.1,
    };
  }
  return {};
}

function buildSectionProjections(
  collection: SectionFeatureCollection | null | undefined,
  scenarioId: ElectoralScenarioId,
  voteShare: Record<string, number>,
) {
  const sections = collection?.features ?? [];
  if (sections.length === 0) {
    return [];
  }

  const parties = Object.keys(voteShare);
  const rawRows = sections.map((feature) => {
    const indicators = baseIndicators(feature.properties);
    const deltas = sectionDeltas(scenarioId, feature.properties);
    const projected = Object.fromEntries(
      parties.map((party) => [party, Math.max(0.2, voteShare[party] + (deltas[party as keyof typeof deltas] ?? 0))]),
    ) as Record<string, number>;
    return {
      sectionId: feature.properties.section_id,
      sectionName: sectionLabel(feature.properties),
      parties: projected,
      indicators,
    };
  });

  const averages = Object.fromEntries(
    parties.map((party) => [
      party,
      rawRows.reduce((total, row) => total + row.parties[party], 0) / rawRows.length,
    ]),
  ) as Record<string, number>;

  return rawRows.map((row) => ({
    ...row,
    parties: Object.fromEntries(
      parties.map((party) => [party, Math.max(0.1, row.parties[party] + voteShare[party] - averages[party])]),
    ) as Record<string, number>,
  }));
}

function validateSeats(voteShare: Record<string, number>, targetSeats: Record<string, number>) {
  const seats = calculateDHondtSeats({
    parties: Object.entries(voteShare).map(([party, percentage]) => ({ party, percentage })),
    totalSeats: COUNCIL_SEATS,
    thresholdPct: THRESHOLD_PCT,
  });
  const allocation = Object.fromEntries(seats.map((item) => [item.party, item.seats]));
  const targetParties = Object.keys(targetSeats);
  return {
    seats: allocation,
    matchesTarget:
      targetParties.every((party) => allocation[party] === targetSeats[party]) &&
      Object.keys(allocation).every((party) => targetSeats[party] === allocation[party]),
  };
}

export function buildCampaignScenarios(collection?: SectionFeatureCollection | null): CampaignScenario[] {
  return scenarioDefinitions.map((definition) => ({
    ...definition,
    label: definition.name,
    sectionProjections: buildSectionProjections(collection, definition.id, definition.voteShare),
    dhondtValidation: validateSeats(definition.voteShare, definition.targetSeats),
  }));
}

export function getCampaignScenarioOptions() {
  return scenarioDefinitions.map((scenario) => ({ id: scenario.id, label: scenario.name }));
}
