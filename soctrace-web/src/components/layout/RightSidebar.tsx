import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Accessibility,
  Activity,
  BarChart3,
  ChevronDown,
  Factory,
  Gem,
  Globe2,
  Grid3X3,
  Gauge,
  Library,
  Play,
  Ruler,
  Scale,
  SignalHigh,
  Target,
  UserRound,
  UsersRound,
} from "lucide-react";
import { HoverTooltip } from "@/components/ui/HoverTooltip";
import { SectionShapePreview } from "@/components/dashboard/SectionShapePreview";
import {
  AgeGenderPyramidChart,
  generateAgeStructureInsight,
  type AgeGenderPyramidRow,
} from "@/components/charts/AgeGenderPyramidChart";
import {
  formatEuroPerM2,
  formatEuro,
  formatLandBuiltEnvironmentMetricValue,
  formatMunicipalitySectionSubtitle,
  formatScorePercent,
  formatScore,
  CAMPAIGN_FORECAST_METRICS,
  getActiveLayer,
  getCampaignForecastLeader,
  getCampaignForecastMetricValue,
  getCampaignForecastVoteShare,
  getLandBuiltEnvironmentMetricValue,
  getPartyVoteShare,
  getPartyColor,
  getSectionDisplayName,
  getSectionLayerColor,
  getSocioeconomicCompleteness,
  getSocioeconomicMetricLabel,
  getSocioeconomicMetricValue,
  getTerritorialMetricLabel,
  getTerritorialMetricValue,
  hasLandBuiltEnvironment,
  hasSocioeconomicSignal,
  hasTerritorialSignal,
  LAND_BUILT_ENVIRONMENT_METRICS,
  SOCIOECONOMIC_METRICS,
  TERRITORIAL_METRICS,
  normalizePartyName,
  rgbaToCss,
} from "@/lib/sectionPresentation";
import { Panel } from "@/components/ui/Panel";
import { fetchSectionsGeoJson } from "@/lib/api";
import { calculateDHondtSeats } from "@/features/ask-soctrace/services/electoralCalculations";
import { buildCampaignScenarios, getCampaignScenarioOptions, type CampaignScenario } from "@/features/forecast/scenarios/campaignScenarios";
import { normalizeSectionId } from "@/lib/sectionIdentity";
import { useDashboardStore } from "@/store/useDashboardStore";
import { askSocTraceTestCategories, askSocTraceTests, type AskSocTraceTest } from "@/features/ask-soctrace/config/askSocTraceTests";
import type { AskSocTraceResponse } from "@/features/ask-soctrace/types";
import {
  ageStructureYears,
  electionContests,
  incomeYears,
  populationYears,
  SOCIAL_DEVELOPMENT_UI_YEAR,
  type AgeCohortPoint,
  type AgeCohortYearPoint,
  type CampaignForecastMetricKey,
  type ElectionContest,
  type ElectoralScenarioId,
  type ElectionType,
  type IncomeSourceKey,
  type IncomeSourcePoint,
  type LandBuiltEnvironmentMetricKey,
  type MunicipalityAgeStructureSummary,
  type MunicipalityIncomeSummary,
  type MunicipalityPopulationSummary,
  type ProductivePotentialVariableKey,
  type SectionDetail,
  type SectionFeatureCollection,
  type SectionFeatureProperties,
  type SocioeconomicMetricKey,
  type TerritorialMetricKey,
} from "@/types/api";

const tabs = [
  { id: "overview", label: "Resumen" },
  { id: "demographics", label: "Demografía" },
  { id: "electoral", label: "Electoral" },
] as const;

function AskTestsPanel({
  onRunTest,
  onClose,
}: {
  onRunTest: (test: AskSocTraceTest) => void;
  onClose: () => void;
}) {
  const [openCategory, setOpenCategory] = useState<string | null>(askSocTraceTestCategories[0] ?? null);

  return (
    <Panel className="flex h-full min-h-0 flex-col overflow-y-auto p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-cyan-100">
            <Library className="h-4 w-4" />
            <p className="text-sm font-semibold">Consultas disponibles</p>
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Explora algunas de las preguntas que actualmente puede responder el agente SocTrace utilizando datos reales del municipio.
          </p>
        </div>
        <button type="button" onClick={onClose} className="rounded-full border border-white/10 px-3 py-1 text-[0.65rem] text-slate-400 transition hover:border-cyan-200/25 hover:text-cyan-100">
          Volver
        </button>
      </div>

      <div className="mt-5 space-y-2">
        {askSocTraceTestCategories.map((category) => {
          const tests = askSocTraceTests.filter((test) => test.category === category);
          if (!tests.length) return null;
          const isOpen = openCategory === category;
          const availableCount = tests.filter((test) => test.status === "available").length;
          return (
            <section key={category} className="overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.025]">
              <button
                type="button"
                onClick={() => setOpenCategory(isOpen ? null : category)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition hover:bg-cyan-200/[0.04]"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-slate-400">{category}</span>
                  <span className="mt-0.5 block text-[0.62rem] text-slate-600">{availableCount} disponibles · {tests.length - availableCount} próximamente</span>
                </span>
                <ChevronDown className={`h-3.5 w-3.5 shrink-0 text-slate-500 transition-transform ${isOpen ? "rotate-180 text-cyan-200" : ""}`} />
              </button>
              <div className={`grid transition-[grid-template-rows] duration-200 ease-out ${isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
                <div className="min-h-0 overflow-hidden">
                  <div className="grid gap-2 border-t border-white/[0.06] p-3">
                {tests.map((test) => {
                  const runnable = test.status === "available";
                  const statusLabel = runnable ? "Disponible" : "Próximamente";
                  return (
                    <button
                      key={test.id}
                      type="button"
                      disabled={!runnable}
                      title={runnable ? undefined : "Esta consulta estará disponible en futuras versiones del agente SocTrace."}
                      aria-label={runnable ? test.title : `${test.title}. Próximamente.`}
                      onClick={() => runnable && onRunTest(test)}
                      className={`group flex items-start gap-2 rounded-xl border px-3 py-2 text-left transition ${
                        runnable
                          ? "border-white/[0.06] bg-[#0b1322]/72 hover:border-cyan-200/20 hover:bg-cyan-200/[0.06]"
                          : "cursor-not-allowed border-white/[0.04] bg-slate-950/40 opacity-50"
                      }`}
                    >
                      <Play className={`mt-0.5 h-3.5 w-3.5 shrink-0 transition ${runnable ? "text-cyan-300/70 group-hover:text-cyan-200" : "text-slate-600"}`} />
                      <span className="min-w-0 flex-1 text-xs leading-5 text-slate-300">
                        {test.title}
                      </span>
                      <span className={`rounded-full border px-1.5 py-0.5 text-[0.58rem] uppercase ${
                        runnable
                          ? "border-emerald-300/20 text-emerald-200"
                          : "border-slate-500/20 text-slate-500"
                      }`}>
                        {statusLabel}
                      </span>
                    </button>
                  );
                })}
                  </div>
                </div>
              </div>
            </section>
          );
        })}
      </div>
    </Panel>
  );
}

function valueFromUnknown(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value.replace(/[^\d,.-]/g, "").replace(".", "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function chartRowsFromResponse(response: AskSocTraceResponse | null): Record<string, unknown>[] {
  if (!response) return [];
  if (response.chart_spec?.data?.length) return response.chart_spec.data;
  if (response.table?.rows?.length) {
    return response.table.rows.map((row) => Object.fromEntries(response.table!.columns.map((column, index) => [column, row[index]])));
  }
  if (response.entities?.length) {
    return response.entities.map((entity) => ({
      name: entity.name,
      value: entity.value ?? entity.description ?? "",
    }));
  }
  return [];
}

function AskChartPanel({
  response,
  onBackToTests,
  onClose,
}: {
  response: AskSocTraceResponse | null;
  onBackToTests: () => void;
  onClose: () => void;
}) {
  const rows = chartRowsFromResponse(response);
  const kind = response?.chart_spec?.kind ?? (response?.entities?.length ? "table" : "none");
  const xKey = response?.chart_spec?.x ?? Object.keys(rows[0] ?? {})[0] ?? "name";
  const yKey = response?.chart_spec?.y ?? Object.keys(rows[0] ?? {})[1] ?? "value";
  const barRows = rows
    .map((row) => ({ label: String(row[xKey] ?? row.name ?? row.section_name ?? ""), value: valueFromUnknown(row[yKey] ?? row.value) }))
    .filter((row) => row.label && row.value != null)
    .slice(0, 8);
  const maxValue = Math.max(...barRows.map((row) => row.value ?? 0), 1);
  const numericRows = rows
    .map((row) => ({
      label: String(row[xKey] ?? row.year ?? row.name ?? ""),
      x: valueFromUnknown(row[xKey] ?? row.year),
      y: valueFromUnknown(row[yKey] ?? row.value),
    }))
    .filter((row) => row.y != null);
  const yValues = numericRows.map((row) => row.y ?? 0);
  const minY = Math.min(...yValues, 0);
  const maxY = Math.max(...yValues, 1);
  const rangeY = Math.max(maxY - minY, 1);
  const linePoints = numericRows.map((row, index) => {
    const x = numericRows.length <= 1 ? 50 : (index / (numericRows.length - 1)) * 100;
    const y = 90 - (((row.y ?? 0) - minY) / rangeY) * 80;
    return `${x},${y}`;
  }).join(" ");
  const scatterPoints = numericRows
    .filter((row) => row.x != null)
    .map((row) => {
      const xValues = numericRows.map((item) => item.x ?? 0);
      const minX = Math.min(...xValues, 0);
      const maxX = Math.max(...xValues, 1);
      const rangeX = Math.max(maxX - minX, 1);
      return {
        cx: 8 + (((row.x ?? 0) - minX) / rangeX) * 84,
        cy: 90 - (((row.y ?? 0) - minY) / rangeY) * 80,
        label: row.label,
      };
    });

  return (
    <Panel className="flex h-full min-h-0 flex-col overflow-y-auto p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-cyan-100">
            <BarChart3 className="h-4 w-4" />
            <p className="text-sm font-semibold">Salida de Ask SocTrace</p>
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Visualización generada desde la última consulta ejecutada en Ask SocTrace.
          </p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={onBackToTests} className="rounded-full border border-white/10 px-3 py-1 text-[0.65rem] text-slate-400 transition hover:border-cyan-200/25 hover:text-cyan-100">
            Tests
          </button>
          <button type="button" onClick={onClose} className="rounded-full border border-white/10 px-3 py-1 text-[0.65rem] text-slate-400 transition hover:border-cyan-200/25 hover:text-cyan-100">
            Cerrar
          </button>
        </div>
      </div>

      {!response ? (
        <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5 text-sm text-slate-400">
          Preparando visualización...
        </div>
      ) : rows.length === 0 || kind === "none" ? (
        kind === "metric" && response.chart_spec?.value !== undefined ? (
          <div className="mt-6 rounded-2xl border border-cyan-200/10 bg-cyan-200/[0.045] p-5">
            <p className="text-xs font-semibold text-slate-400">{response.chart_spec?.title ?? "Resultado"}</p>
            <p className="mt-3 text-3xl font-semibold tabular-nums text-cyan-100">{String(response.chart_spec.value)}</p>
          </div>
        ) : (
        <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-5 text-sm leading-6 text-slate-400">
          No visualización disponible todavía para esta consulta.
        </div>
        )
      ) : kind === "bar" && barRows.length ? (
        <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
          <p className="text-xs font-semibold text-slate-300">{response.chart_spec?.title ?? "Resultado analítico"}</p>
          <div className="mt-4 space-y-3">
            {barRows.map((row) => (
              <div key={row.label}>
                <div className="flex items-center justify-between gap-3 text-[0.7rem] text-slate-400">
                  <span className="truncate">{row.label}</span>
                  <span className="tabular-nums text-slate-300">{row.value}</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-white/[0.06]">
                  <div className="h-full rounded-full bg-cyan-300/70" style={{ width: `${Math.max(4, ((row.value ?? 0) / maxValue) * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : kind === "line" && numericRows.length ? (
        <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
          <p className="text-xs font-semibold text-slate-300">{response.chart_spec?.title ?? "Evolución"}</p>
          <svg viewBox="0 0 100 100" className="mt-4 h-48 w-full overflow-visible" role="img" aria-label={response.chart_spec?.title ?? "Gráfico de línea"}>
            <polyline fill="none" stroke="rgba(103,232,249,0.85)" strokeWidth="2.5" points={linePoints} />
            {linePoints.split(" ").map((point, index) => {
              const [cx, cy] = point.split(",");
              return <circle key={`${point}-${index}`} cx={cx} cy={cy} r="2.5" fill="rgb(165,243,252)" />;
            })}
          </svg>
          <div className="mt-2 flex justify-between gap-3 text-[0.68rem] text-slate-500">
            <span>{numericRows[0]?.label}</span>
            <span>{numericRows[numericRows.length - 1]?.label}</span>
          </div>
        </div>
      ) : kind === "scatter" && scatterPoints.length ? (
        <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
          <p className="text-xs font-semibold text-slate-300">{response.chart_spec?.title ?? "Relación entre variables"}</p>
          <svg viewBox="0 0 100 100" className="mt-4 h-48 w-full overflow-visible" role="img" aria-label={response.chart_spec?.title ?? "Gráfico de dispersión"}>
            <line x1="8" y1="92" x2="96" y2="92" stroke="rgba(148,163,184,0.25)" />
            <line x1="8" y1="8" x2="8" y2="92" stroke="rgba(148,163,184,0.25)" />
            {scatterPoints.map((point, index) => (
              <circle key={`${point.label}-${index}`} cx={point.cx} cy={point.cy} r="2.8" fill="rgba(103,232,249,0.85)" />
            ))}
          </svg>
        </div>
      ) : (
        <div className="mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.025]">
          <p className="border-b border-white/[0.06] px-3 py-2 text-xs font-semibold text-slate-300">{response.chart_spec?.title ?? "Resultado analítico"}</p>
          <div className="max-h-[30rem] overflow-auto">
            {rows.slice(0, 18).map((row, index) => (
              <div key={index} className="border-b border-white/[0.045] px-3 py-2 text-xs leading-5 text-slate-400 last:border-0">
                {Object.values(row).filter(Boolean).slice(0, 3).join(" · ")}
              </div>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

const number = (value?: number | null) =>
  value == null ? "--" : value.toLocaleString("es-ES");

const percentage = (value?: number | null) =>
  value == null ? "--" : `${(value * 100).toFixed(1)}%`;

const OPERATIONAL_DATA_YEAR = "2023";

type PopulationPoint = {
  year: string;
  value: number | null;
};

type ChartPoint = PopulationPoint & {
  x: number;
  y: number;
};

type AgeCohortDefinition = {
  cohort: string;
  color: string;
  populationField: keyof SectionDetail["demography"];
  featureField?: keyof SectionFeatureProperties;
};

type AgeSeriesPoint = AgeCohortYearPoint & {
  x: number;
  y: number;
};

type IncomeBarPoint = {
  year: string;
  individualIncome: number | null;
  householdIncome: number | null;
};

type IncomeSourceSeriesPoint = IncomeSourcePoint & {
  x: number;
  y: number;
};

type PartySharePoint = {
  party: string;
  percentage: number;
  votes?: number;
};

type ElectoralHistoryPoint = {
  contestId: string;
  label: string;
  party: string;
  percentage: number | null;
};

type LandBuiltEnvironmentStats = {
  metric: LandBuiltEnvironmentMetricKey;
  value: number | null;
  average: number | null;
  min: number | null;
  max: number | null;
  percentile: number | null;
  rank: number | null;
  total: number;
  relative: number | null;
  builtOccupationPct: number | null;
  footprintRatio: number | null;
  urbanIntensity: number | null;
};

const LAND_BUILT_ENVIRONMENT_ACCENT = {
  populationDensity: "#67d4f2",
  parcelDensity: "#6ec6b2",
  builtFootprint: "#8fa6b8",
  avgPlotSize: "#86a99f",
  buildingIntensity: "#7da6b6",
  urbanIntensity: "#88b874",
} as const satisfies Record<LandBuiltEnvironmentMetricKey, string>;

const LAND_BUILT_ENVIRONMENT_EXPLAINERS = {
  parcelDensity: {
    tagline: "Parcel Structure / Morphology",
    explanation: "Number of cadastral parcels per unit of surface area.",
  },
  builtFootprint: {
    tagline: "Physical Occupancy",
    explanation: "Aggregated built surface within the selected territory.",
  },
  avgPlotSize: {
    tagline: "Residential Typology",
    explanation: "Average size of cadastral parcels.",
  },
  buildingIntensity: {
    tagline: "Urban Development Pressure",
    explanation: "Relative built intensity within the selected territory.",
  },
  urbanIntensity: {
    tagline: "Overall Urban Intensity",
    explanation: "Composite 0-100 index of physical urban occupation based on density, built footprint, parcel density and plot size.",
  },
} as const;

function formatCompactNumber(value?: number | null, maximumFractionDigits = 0) {
  return value == null || !Number.isFinite(value)
    ? "N/A"
    : value.toLocaleString("es-ES", { maximumFractionDigits });
}

function getLandMetricRawValue(section: SectionFeatureProperties, metric: LandBuiltEnvironmentMetricKey) {
  return getLandBuiltEnvironmentMetricValue(section, metric);
}

function getAreaM2(section?: SectionFeatureProperties | null) {
  const areaKm2 = toFiniteNumber(section?.area_km2);
  return areaKm2 != null ? areaKm2 * 1_000_000 : null;
}

function getBuiltOccupationPct(section?: SectionFeatureProperties | null) {
  const footprint = toFiniteNumber(section?.huella_construida_m2);
  const areaM2 = getAreaM2(section);
  return footprint != null && areaM2 != null && areaM2 > 0 ? (footprint / areaM2) * 100 : null;
}

function getLandBuiltEnvironmentStats({
  collection,
  section,
  metric,
}: {
  collection?: SectionFeatureCollection | null;
  section?: SectionFeatureProperties | null;
  metric: LandBuiltEnvironmentMetricKey;
}): LandBuiltEnvironmentStats {
  const features = collection?.features ?? [];
  const values = features
    .map((feature) => getLandMetricRawValue(feature.properties, metric))
    .filter((value): value is number => value != null && Number.isFinite(value));
  const sorted = [...values].sort((a, b) => a - b);
  const selectedValue = section ? getLandMetricRawValue(section, metric) : null;
  const municipalityValue =
    metric === "builtFootprint"
      ? features.reduce((total, feature) => total + (toFiniteNumber(feature.properties.huella_construida_m2) ?? 0), 0)
      : values.length > 0
        ? values.reduce((total, value) => total + value, 0) / values.length
        : null;
  const value = section ? selectedValue : municipalityValue;
  const average = values.length > 0 ? values.reduce((total, item) => total + item, 0) / values.length : null;
  const lowerCount = value == null ? 0 : sorted.filter((item) => item <= value).length;
  const rank =
    value == null
      ? null
      : [...values].sort((a, b) => b - a).findIndex((item) => item === value) + 1 || null;
  const totalAreaM2 = features.reduce((total, feature) => total + (getAreaM2(feature.properties) ?? 0), 0);
  const totalFootprint = features.reduce(
    (total, feature) => total + (toFiniteNumber(feature.properties.huella_construida_m2) ?? 0),
    0,
  );
  const builtOccupationPct = section
    ? getBuiltOccupationPct(section)
    : totalAreaM2 > 0
      ? (totalFootprint / totalAreaM2) * 100
      : null;
  const footprintRatio =
    metric === "builtFootprint"
      ? builtOccupationPct
      : section
        ? toFiniteNumber(section.indice_construido)
        : null;
  const urbanIntensityValues = features
    .map((feature) => toFiniteNumber(feature.properties.urban_intensity_index))
    .filter((item): item is number => item != null);
  const urbanIntensity = section
    ? toFiniteNumber(section.urban_intensity_index)
    : urbanIntensityValues.length > 0
      ? urbanIntensityValues.reduce((total, item) => total + item, 0) / urbanIntensityValues.length
      : null;

  return {
    metric,
    value,
    average,
    min: sorted[0] ?? null,
    max: sorted[sorted.length - 1] ?? null,
    percentile: value == null || sorted.length === 0 ? null : Math.round((lowerCount / sorted.length) * 100),
    rank,
    total: sorted.length,
    relative: value != null && average != null && average > 0 ? ((value - average) / average) * 100 : null,
    builtOccupationPct,
    footprintRatio,
    urbanIntensity,
  };
}

function getLandIntensityLabel(percentile?: number | null) {
  if (percentile == null) {
    return "No comparable signal";
  }
  if (percentile >= 80) {
    return "Very high";
  }
  if (percentile >= 60) {
    return "High";
  }
  if (percentile >= 40) {
    return "Moderate";
  }
  if (percentile >= 20) {
    return "Low";
  }
  return "Very low";
}

function getLandBuiltEnvironmentInsight({
  metric,
  stats,
  isMunicipality,
}: {
  metric: LandBuiltEnvironmentMetricKey;
  stats: LandBuiltEnvironmentStats;
  isMunicipality: boolean;
}) {
  const level = getLandIntensityLabel(stats.percentile).toLowerCase();
  const direction = stats.relative == null ? "near municipal baseline" : stats.relative >= 0 ? "above municipal average" : "below municipal average";

  if (isMunicipality) {
    return "Municipal baseline summarizes urban form, parcel structure and built occupation across all sections.";
  }

  if (metric === "populationDensity") {
    return `${level} residential pressure, ${direction}, indicating concentrated demand on local urban fabric.`;
  }
  if (metric === "parcelDensity") {
    return `${level} parcel fragmentation, ${direction}, suggesting a finer-grained land ownership pattern.`;
  }
  if (metric === "builtFootprint") {
    return `${level} built occupation, ${direction}, with physical footprint shaping redevelopment capacity.`;
  }
  if (metric === "avgPlotSize") {
    return `${level} plot scale, ${direction}, framing compactness versus spacious land structure.`;
  }
  if (metric === "urbanIntensity") {
    return `${level} composite urban intensity, combining density, built footprint, parcel density and plot size.`;
  }

  return `${level} building intensity, ${direction}, describing relative built intensity within the selected territory.`;
}

function LandBuiltEnvironmentExplainer({ metric }: { metric: LandBuiltEnvironmentMetricKey }) {
  const explainer = (LAND_BUILT_ENVIRONMENT_EXPLAINERS as Partial<
    Record<LandBuiltEnvironmentMetricKey, { tagline: string; explanation: string }>
  >)[metric];
  if (!explainer) {
    return null;
  }

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.07] bg-white/[0.035] px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]">
      <p className="text-[0.72rem] font-semibold uppercase tracking-[0.14em] text-slate-200">{explainer.tagline}</p>
      <p className="mt-1.5 text-xs font-medium leading-5 text-slate-400">{explainer.explanation}</p>
    </div>
  );
}

function LandBuiltEnvironmentKpiCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: typeof UsersRound;
  accent: string;
}) {
  return (
    <div className="flex min-h-[5.15rem] items-center justify-between rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3 shadow-[0_18px_40px_rgba(0,0,0,0.16)]">
      <div className="min-w-0">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.13em] text-slate-500">{label}</p>
        <p className="mt-2 text-[1.25rem] font-semibold leading-none tabular-nums text-white">{value}</p>
      </div>
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.045]"
        style={{ color: accent }}
      >
        <Icon className="h-5 w-5" strokeWidth={1.7} />
      </div>
    </div>
  );
}

function LandBuiltEnvironmentHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Land / Built Environment
        </p>
        <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
          2023
        </span>
      </div>
      <h2 className="font-manrope mt-3 text-left text-balance text-[1.8rem] font-semibold tracking-[-0.04em] text-white">
        {title}
      </h2>
      <p className="font-manrope mt-2 max-w-[15rem] text-left text-sm font-medium text-slate-400">
        {subtitle}
      </p>
    </div>
  );
}

function DensityGradientHero({ stats, accent }: { stats: LandBuiltEnvironmentStats; accent: string }) {
  const marker = Math.min(98, Math.max(2, stats.percentile ?? 50));
  return (
    <div className="rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Density Gradient</p>
        <p className="text-xs font-semibold text-slate-300">{getLandIntensityLabel(stats.percentile)}</p>
      </div>
      <div className="relative mt-8 h-5 rounded-full border border-white/10 bg-[linear-gradient(90deg,#243241,#315462,#47758c,#6a9baa,#8ab9bf)] shadow-[inset_0_0_18px_rgba(255,255,255,0.05)]">
        <div
          className="absolute top-1/2 h-9 w-1.5 -translate-y-1/2 rounded-full border border-white/50 bg-white shadow-[0_0_20px_rgba(103,212,242,0.28)]"
          style={{ left: `calc(${marker}% - 3px)` }}
        />
      </div>
      <div className="mt-3 flex justify-between text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-slate-500">
        <span>Low</span>
        <span>High</span>
      </div>
      <div className="mt-5 grid grid-cols-3 gap-2">
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.035] px-3 py-2">
          <p className="text-[0.65rem] text-slate-500">Percentile</p>
          <p className="mt-1 text-sm font-semibold text-white">P{stats.percentile ?? "--"}</p>
        </div>
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.035] px-3 py-2">
          <p className="text-[0.65rem] text-slate-500">Rank</p>
          <p className="mt-1 text-sm font-semibold text-white">
            {stats.rank && stats.total ? `${stats.rank}/${stats.total}` : "--"}
          </p>
        </div>
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.035] px-3 py-2">
          <p className="text-[0.65rem] text-slate-500">Level</p>
          <p className="mt-1 text-sm font-semibold" style={{ color: accent }}>{getLandIntensityLabel(stats.percentile)}</p>
        </div>
      </div>
    </div>
  );
}

function ParcelCompactnessHero({ stats, accent }: { stats: LandBuiltEnvironmentStats; accent: string }) {
  const activeCells = Math.max(4, Math.round(((stats.percentile ?? 50) / 100) * 36));
  return (
    <div className="rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Parcel Compactness</p>
        <p className="text-xs font-semibold text-slate-300">{getLandIntensityLabel(stats.percentile)}</p>
      </div>
      <div className="mt-5 grid grid-cols-9 gap-1.5">
        {Array.from({ length: 36 }).map((_, index) => (
          <span
            key={index}
            className="aspect-square rounded-[0.35rem] border border-white/[0.055]"
            style={{
              background:
                index < activeCells
                  ? `linear-gradient(135deg, ${accent}, rgba(15,23,42,0.62))`
                  : "rgba(148,163,184,0.08)",
              opacity: index < activeCells ? 0.9 : 0.55,
            }}
          />
        ))}
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-white/[0.06] pt-3 text-xs">
        <span className="text-slate-500">Avg plot size</span>
        <span className="font-semibold tabular-nums text-slate-100">{formatCompactNumber(stats.average, 1)}</span>
      </div>
    </div>
  );
}

function FootprintHero({ stats, accent }: { stats: LandBuiltEnvironmentStats; accent: string }) {
  const fill = Math.min(100, Math.max(0, stats.builtOccupationPct ?? stats.percentile ?? 0));
  return (
    <div className="rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Built Footprint</p>
        <p className="text-xs font-semibold text-slate-300">{fill.toFixed(1)}% occupied</p>
      </div>
      <div className="mt-5 grid grid-cols-12 gap-1.5">
        {Array.from({ length: 48 }).map((_, index) => {
          const active = index < Math.round((fill / 100) * 48);
          return (
            <span
              key={index}
              className="h-5 rounded-[0.28rem] border border-white/[0.055]"
              style={{ background: active ? accent : "rgba(148,163,184,0.075)" }}
            />
          );
        })}
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-white/[0.06] pt-3 text-xs">
        <span className="text-slate-500">Percentile</span>
        <span className="font-semibold tabular-nums text-slate-100">P{stats.percentile ?? "--"}</span>
      </div>
    </div>
  );
}

function ScaleSpectrumHero({ stats, accent }: { stats: LandBuiltEnvironmentStats; accent: string }) {
  const marker = Math.min(98, Math.max(2, stats.percentile ?? 50));
  return (
    <div className="rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Scale Spectrum</p>
        <p className="text-xs font-semibold text-slate-300">P{stats.percentile ?? "--"}</p>
      </div>
      <div className="relative mt-8 h-3 rounded-full border border-white/10 bg-[linear-gradient(90deg,#284654,#4f7d7b,#7aa196,#a9c4b8)]">
        <span
          className="absolute top-1/2 h-8 w-8 -translate-y-1/2 rounded-full border border-white/30 bg-[#07111f] shadow-[0_0_24px_rgba(110,198,178,0.24)]"
          style={{ left: `calc(${marker}% - 16px)` }}
        >
          <span className="absolute inset-2 rounded-full" style={{ background: accent }} />
        </span>
      </div>
      <div className="mt-4 flex justify-between text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-slate-500">
        <span>Compact</span>
        <span>Spacious</span>
      </div>
    </div>
  );
}

function SkylineHero({ stats, accent }: { stats: LandBuiltEnvironmentStats; accent: string }) {
  const percentile = stats.percentile ?? 50;
  const bars = [0.22, 0.34, 0.46, 0.58, 0.7, 0.84, 1].map((height, index) => ({
    height: Math.max(18, height * (55 + percentile * 0.7) - index * 2),
    opacity: 0.34 + index * 0.085,
  }));
  return (
    <div className="rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          {stats.metric === "urbanIntensity" ? "Urban Intensity" : "Building Intensity"}
        </p>
        <p className="text-xs font-semibold text-slate-300">{getLandIntensityLabel(stats.percentile)}</p>
      </div>
      <div className="mt-6 flex h-32 items-end justify-center gap-2 rounded-2xl border border-white/[0.045] bg-white/[0.025] px-4 pb-3">
        {bars.map((bar, index) => (
          <span
            key={index}
            className="w-full max-w-7 rounded-t-lg border border-white/10"
            style={{
              height: bar.height,
              opacity: bar.opacity,
              background: `linear-gradient(180deg, ${accent}, rgba(15,23,42,0.76))`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function LandBuiltEnvironmentHero({ stats, accent }: { stats: LandBuiltEnvironmentStats; accent: string }) {
  if (stats.metric === "populationDensity") {
    return <DensityGradientHero stats={stats} accent={accent} />;
  }
  if (stats.metric === "parcelDensity") {
    return <ParcelCompactnessHero stats={stats} accent={accent} />;
  }
  if (stats.metric === "builtFootprint") {
    return <FootprintHero stats={stats} accent={accent} />;
  }
  if (stats.metric === "avgPlotSize") {
    return <ScaleSpectrumHero stats={stats} accent={accent} />;
  }

  return <SkylineHero stats={stats} accent={accent} />;
}

function UrbanOccupationRadial({ value, accent }: { value?: number | null; accent: string }) {
  const normalized = Math.min(100, Math.max(0, value ?? 0));
  const circumference = 2 * Math.PI * 36;
  return (
    <div className="flex h-full min-h-[12rem] flex-col rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Urban Occupation</p>
      <div className="mt-4 flex flex-1 items-center justify-center">
        <svg className="h-28 w-28" viewBox="0 0 96 96" role="img" aria-label="Urban occupation level">
          <circle cx="48" cy="48" r="36" fill="none" stroke="rgba(148,163,184,0.14)" strokeWidth="10" />
          <circle
            cx="48"
            cy="48"
            r="36"
            fill="none"
            stroke={accent}
            strokeLinecap="round"
            strokeWidth="10"
            strokeDasharray={`${(normalized / 100) * circumference} ${circumference}`}
            transform="rotate(-90 48 48)"
          />
          <text x="48" y="47" textAnchor="middle" className="fill-white text-[16px] font-semibold">
            {normalized.toFixed(0)}%
          </text>
          <text x="48" y="62" textAnchor="middle" className="fill-slate-500 text-[8px] font-semibold uppercase">
            level
          </text>
        </svg>
      </div>
    </div>
  );
}

function LandBuiltEnvironmentInsightCard({ insight, metric }: { insight: string; metric: LandBuiltEnvironmentMetricKey }) {
  return (
    <div className="flex h-full min-h-[12rem] flex-col justify-between rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-4">
      <div>
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Key Insight</p>
        <p className="mt-4 text-xs font-medium leading-5 text-slate-300">{insight}</p>
      </div>
      <div className="mt-5 rounded-2xl border border-cyan-200/10 bg-cyan-200/[0.045] px-3 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-cyan-100">
        {LAND_BUILT_ENVIRONMENT_METRICS[metric].title}
      </div>
    </div>
  );
}

function LandBuiltEnvironmentAnalytics({
  title,
  subtitle,
  section,
  collection,
  metric,
}: {
  title: string;
  subtitle: string;
  section?: SectionFeatureProperties | null;
  collection?: SectionFeatureCollection | null;
  metric: LandBuiltEnvironmentMetricKey;
}) {
  const stats = getLandBuiltEnvironmentStats({ collection, section, metric });
  const accent = LAND_BUILT_ENVIRONMENT_ACCENT[metric];
  const hasMetrics = section
    ? hasLandBuiltEnvironment(section)
    : (collection?.features.some((feature) => hasLandBuiltEnvironment(feature.properties)) ?? false);
  const valueLabel = formatLandBuiltEnvironmentMetricValue(stats.value, metric);
  const urbanIntensityLabel = formatScorePercent(stats.urbanIntensity);
  const populationDensityValues = collection?.features
    .map((feature) => getLandBuiltEnvironmentMetricValue(feature.properties, "populationDensity"))
    .filter((value): value is number => value != null && Number.isFinite(value)) ?? [];
  const populationDensityValue = section
    ? getLandBuiltEnvironmentMetricValue(section, "populationDensity")
    : populationDensityValues.length > 0
      ? populationDensityValues.reduce((accumulator, value) => accumulator + value, 0) / populationDensityValues.length
      : null;
  const kpiLabel = metric === "urbanIntensity"
    ? "Densidad de población"
    : metric === "populationDensity"
      ? "Densidad de población"
      : LAND_BUILT_ENVIRONMENT_METRICS[metric].title;
  const primaryValueLabel = metric === "urbanIntensity"
    ? formatLandBuiltEnvironmentMetricValue(populationDensityValue, "populationDensity")
    : valueLabel;
  const insight = getLandBuiltEnvironmentInsight({ metric, stats, isMunicipality: !section });

  if (!hasMetrics) {
    return (
      <Panel className="flex h-full flex-col p-4">
        <LandBuiltEnvironmentHeader title={title} subtitle={subtitle} />
        <Panel className="mt-6 p-4">
          <p className="text-sm text-slate-300">No land or built-environment fields available.</p>
        </Panel>
      </Panel>
    );
  }

  return (
    <Panel className="flex h-full min-h-0 min-w-0 flex-col overflow-y-auto overflow-x-hidden p-4">
      <LandBuiltEnvironmentHeader title={title} subtitle={subtitle} />

      <LandBuiltEnvironmentExplainer metric={metric} />

      <div className="mt-5 grid grid-cols-2 gap-3">
        <LandBuiltEnvironmentKpiCard label={kpiLabel} value={primaryValueLabel} icon={metric === "avgPlotSize" ? Ruler : Grid3X3} accent={accent} />
        <LandBuiltEnvironmentKpiCard label="Urban Intensity" value={urbanIntensityLabel} icon={SignalHigh} accent={accent} />
      </div>

      <div className="mt-4">
        <LandBuiltEnvironmentHero stats={stats} accent={accent} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <UrbanOccupationRadial value={stats.builtOccupationPct ?? stats.percentile} accent={accent} />
        <LandBuiltEnvironmentInsightCard insight={insight} metric={metric} />
      </div>
    </Panel>
  );
}

const SOCIOECONOMIC_SIGNAL_ORDER = [
  "humanCapital",
  "vulnerability",
  "resilience",
  "productiveComplexity",
  "inequalityPressure",
] as const satisfies readonly SocioeconomicMetricKey[];

function formatScoreShort(value?: number | null) {
  return value == null || !Number.isFinite(value) ? "N/A" : `${Math.round(value)}`;
}

function formatUiPercent(value?: number | null) {
  return value == null || !Number.isFinite(value) ? "N/A" : `${value.toFixed(1)}%`;
}

function SocioeconomicSignalGrid({ section }: { section: SectionFeatureProperties }) {
  return (
    <div className="mt-4 grid gap-2">
      {SOCIOECONOMIC_SIGNAL_ORDER.map((metric) => {
        const config = SOCIOECONOMIC_METRICS[metric];
        const value = getSocioeconomicMetricValue(section, metric);
        const label = getSocioeconomicMetricLabel(section, metric);
        const color = config.colors[Math.min(4, Math.max(0, Math.floor((value ?? 0) / 20)))];
        const width = Math.min(100, Math.max(0, value ?? 0));

        return (
          <div key={metric} className="rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-slate-300">{config.title}</p>
                <p className="mt-1 text-[0.68rem] text-slate-500">{label}</p>
              </div>
              <p className="text-lg font-semibold tabular-nums text-white">{formatScoreShort(value)}</p>
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-white/[0.07]">
              <div className="h-full rounded-full" style={{ width: `${width}%`, backgroundColor: color }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SocioeconomicPentagon({ section }: { section: SectionFeatureProperties }) {
  const center = 64;
  const radius = 46;
  const points = SOCIOECONOMIC_SIGNAL_ORDER.map((metric, index) => {
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / SOCIOECONOMIC_SIGNAL_ORDER.length;
    const valueRadius = ((getSocioeconomicMetricValue(section, metric) ?? 0) / 100) * radius;
    return {
      x: center + Math.cos(angle) * valueRadius,
      y: center + Math.sin(angle) * valueRadius,
      labelX: center + Math.cos(angle) * (radius + 13),
      labelY: center + Math.sin(angle) * (radius + 13),
      metric,
    };
  });
  const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");
  const rings = [0.33, 0.66, 1].map((scale) =>
    SOCIOECONOMIC_SIGNAL_ORDER.map((_, index) => {
      const angle = -Math.PI / 2 + (index * 2 * Math.PI) / SOCIOECONOMIC_SIGNAL_ORDER.length;
      return `${center + Math.cos(angle) * radius * scale},${center + Math.sin(angle) * radius * scale}`;
    }).join(" "),
  );

  return (
    <div className="mt-4 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Five-signal profile</p>
      <svg className="mt-3 h-44 w-full overflow-visible" viewBox="0 0 128 128" role="img" aria-label="Socioeconomic five-signal profile">
        {rings.map((ring) => (
          <polygon key={ring} points={ring} fill="none" stroke="rgba(148,163,184,0.16)" strokeWidth="1" />
        ))}
        {points.map((point) => (
          <line key={point.metric} x1={center} y1={center} x2={point.labelX - (point.labelX - center) * 0.22} y2={point.labelY - (point.labelY - center) * 0.22} stroke="rgba(148,163,184,0.12)" />
        ))}
        <polygon points={polygon} fill="rgba(103,212,242,0.18)" stroke="#7fc7c0" strokeWidth="2" />
        {points.map((point) => (
          <circle key={point.metric} cx={point.x} cy={point.y} r="2.6" fill="#d9fbff" />
        ))}
      </svg>
      <div className="grid grid-cols-2 gap-2 text-[0.68rem] text-slate-500">
        {SOCIOECONOMIC_SIGNAL_ORDER.map((metric) => (
          <span key={metric}>{SOCIOECONOMIC_METRICS[metric].shortTitle}</span>
        ))}
      </div>
    </div>
  );
}

function SocioeconomicBreakdown({
  section,
  metric,
}: {
  section: SectionFeatureProperties;
  metric: SocioeconomicMetricKey;
}) {
  const config = SOCIOECONOMIC_METRICS[metric];

  return (
    <div className="mt-4 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">{config.title} breakdown</p>
      <div className="mt-4 grid gap-3">
        {config.breakdown.map((item) => {
          const value = toFiniteNumber(section[item.field] as number | string | null);
          const width = Math.min(100, Math.max(0, value ?? 0));
          return (
            <div key={item.label}>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">{item.label}</span>
                <span className="font-semibold tabular-nums text-slate-100">{formatScoreShort(value)}</span>
              </div>
              <div className="mt-1.5 h-1.5 rounded-full bg-white/[0.07]">
                <div className="h-full rounded-full bg-cyan-200/70" style={{ width: `${width}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SocioeconomicProfilePanel({
  title,
  subtitle,
  section,
  metric,
  year = "2023",
  silhouette,
}: {
  title: string;
  subtitle: string;
  section: SectionFeatureProperties;
  metric: SocioeconomicMetricKey;
  year?: string;
  silhouette?: ReactNode;
}) {
  const hasSignal = hasSocioeconomicSignal(section);
  const activeScore = getSocioeconomicMetricValue(section, metric);
  const activeLabel = getSocioeconomicMetricLabel(section, metric);
  const completeness = getSocioeconomicCompleteness(section, metric);
  const activeConfig = SOCIOECONOMIC_METRICS[metric];

  return (
    <Panel className="flex h-full min-h-0 flex-col overflow-y-auto p-4">
      <div className="relative">
        <div className="flex w-full flex-col pr-16">
          <div className="flex items-center justify-between gap-3">
            <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Inteligencia socioeconómica
            </p>
            <span className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">{year}</span>
          </div>
          <h2 className="font-manrope mt-3 text-left text-balance text-[1.8rem] font-semibold tracking-[-0.04em] text-white">
            {title}
          </h2>
          <p className="font-manrope mt-2 max-w-[15rem] text-left text-sm font-medium text-slate-400">{subtitle}</p>
        </div>
        {silhouette}
      </div>

      {hasSignal ? (
        <>
          <div className="mt-5 rounded-3xl border border-white/8 bg-white/[0.03] p-4">
            <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Socioeconomic Profile</p>
            <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-4">
              <p className="text-xs text-slate-500">Active Signal · {activeConfig.title}</p>
              <p className="mt-1 text-3xl font-semibold tabular-nums text-white">{formatScore(activeScore)}</p>
              <div className="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-3">
                <span className="text-xs text-slate-500">Level</span>
                <span className="text-sm font-semibold text-slate-100">{activeLabel}</span>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-3">
                <span className="text-xs text-slate-500">Data Completeness</span>
                <span className="text-sm font-semibold tabular-nums text-slate-100">{formatUiPercent(completeness)}</span>
              </div>
            </div>
            <p className="mt-3 text-[0.68rem] leading-4 text-slate-500">Comparative signal, not an absolute measure.</p>
          </div>

          <SocioeconomicSignalGrid section={section} />
          <SocioeconomicPentagon section={section} />
          <SocioeconomicBreakdown section={section} metric={metric} />
        </>
      ) : (
        <Panel className="mt-6 p-4">
          <p className="text-sm text-slate-300">No socioeconomic signal available for this section.</p>
        </Panel>
      )}
    </Panel>
  );
}

type SocioeconomicSignalPoint = {
  metric: SocioeconomicMetricKey;
  value: number | null;
};

const socioeconomicSignalMeta: Record<
  SocioeconomicMetricKey,
  {
    tooltip: string;
    statuses: readonly [string, string, string, string, string];
    icon: typeof Activity;
  }
> = {
  humanCapital: {
    tooltip: "Reflects education, skills and demographic capacity supporting long-term social development.",
    statuses: ["Emerging Talent Base", "Developing Skills Pool", "Stable Human Capital", "Advanced Talent Base", "Knowledge Advantage"],
    icon: UsersRound,
  },
  vulnerability: {
    tooltip: "Captures exposure to social risk, economic fragility and structural disadvantage.",
    statuses: ["Low Exposure", "Contained Risk", "Social Strain", "Elevated Vulnerability", "Structural Fragility"],
    icon: Activity,
  },
  resilience: {
    tooltip: "Measures the capacity of the area to absorb pressure and maintain social stability.",
    statuses: ["Fragile Response", "Limited Buffer", "Adaptive Capacity", "Strong Resilience", "Robust Social Fabric"],
    icon: Scale,
  },
  productiveComplexity: {
    tooltip: "Represents diversity and sophistication of the local socioeconomic and productive structure.",
    statuses: ["Basic Economic Mix", "Narrow Productive Base", "Diversifying Structure", "Complex Local Economy", "Advanced Productive Fabric"],
    icon: Factory,
  },
  inequalityPressure: {
    tooltip: "Indicates potential socioeconomic imbalance and uneven distribution of opportunity.",
    statuses: ["Balanced Distribution", "Mild Tension", "Uneven Structure", "High Inequality Pressure", "Polarized Territory"],
    icon: Gauge,
  },
};

function normalizeSocioeconomicScore(value?: number | null) {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }

  return Math.min(100, Math.max(0, value > 0 && value <= 1 ? value * 100 : value));
}

function getSocioeconomicStatus(metric: SocioeconomicMetricKey, value?: number | null) {
  const score = normalizeSocioeconomicScore(value);
  if (score == null) {
    return "No signal";
  }
  const index = Math.min(4, Math.max(0, Math.floor(score / 20)));
  return socioeconomicSignalMeta[metric].statuses[index];
}

function getSocioeconomicProfileFromCollection(
  collection?: SectionFeatureCollection | null,
  sectionId?: string | null,
) {
  if (!collection || collection.features.length === 0) {
    return null;
  }

  if (sectionId) {
    const normalizedId = normalizeSectionId(sectionId);
    return collection.features.find((feature) => normalizeSectionId(feature.properties.section_id) === normalizedId)
      ?.properties ?? null;
  }

  // TODO: replace simple section mean with official municipal aggregate or population-weighted mean
  // once a stable municipal socioeconomic contract is exposed by the API.
  return buildMunicipalitySocioeconomicProfile(collection);
}

function getSocioeconomicSignalPoints(section?: SectionFeatureProperties | null): SocioeconomicSignalPoint[] {
  return SOCIOECONOMIC_SIGNAL_ORDER.map((metric) => ({
    metric,
    value: section ? normalizeSocioeconomicScore(getSocioeconomicMetricValue(section, metric)) : null,
  }));
}

function hasCompleteSocioeconomicProfile(section?: SectionFeatureProperties | null) {
  if (!section) {
    return false;
  }

  return SOCIOECONOMIC_SIGNAL_ORDER.every(
    (metric) => normalizeSocioeconomicScore(getSocioeconomicMetricValue(section, metric)) != null,
  );
}

function SocioeconomicBubbleOverlapChart({ points }: { points: SocioeconomicSignalPoint[] }) {
  const positions: Record<SocioeconomicMetricKey, { x: number; y: number }> = {
    humanCapital: { x: 112, y: 72 },
    vulnerability: { x: 174, y: 74 },
    resilience: { x: 144, y: 112 },
    productiveComplexity: { x: 90, y: 122 },
    inequalityPressure: { x: 198, y: 122 },
  };

  return (
    <div className="rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Annual synthetic profile</p>
      <svg className="mt-2 h-[210px] w-full overflow-visible" viewBox="0 0 288 190" role="img" aria-label="Socioeconomic overlapping circles" preserveAspectRatio="xMidYMid meet">
        {points.map(({ metric, value }) => {
          const score = value ?? 0;
          const radius = 28 + (score / 100) * 28;
          const position = positions[metric];
          const color = SOCIOECONOMIC_METRICS[metric].colors[3];
          return (
            <g key={metric}>
              <circle cx={position.x} cy={position.y} r={radius} fill={color} fillOpacity="0.22" stroke={color} strokeOpacity="0.72" strokeWidth="1.4" />
              <text x={position.x} y={position.y - 2} textAnchor="middle" fill="#f8fafc" fontSize="14" fontWeight="700">
                {value == null ? "N/A" : `${value.toFixed(1)}%`}
              </text>
              <text x={position.x} y={position.y + 13} textAnchor="middle" fill="rgba(203,213,225,0.72)" fontSize="8" fontWeight="600">
                {SOCIOECONOMIC_METRICS[metric].shortTitle}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function SocioeconomicPictogramRows({ points }: { points: SocioeconomicSignalPoint[] }) {
  return (
    <div className="mt-3 grid gap-2">
      {points.map(({ metric, value }) => {
        const config = SOCIOECONOMIC_METRICS[metric];
        const meta = socioeconomicSignalMeta[metric];
        const Icon = meta.icon;
        const score = value ?? 0;
        const activeIcons = value == null ? 0 : Math.min(5, Math.max(1, Math.ceil(score / 20)));
        const color = config.colors[Math.min(4, Math.max(0, Math.floor(score / 20)))];
        return (
          <div key={metric} className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5">
            <div className="flex items-start justify-between gap-3">
              <HoverTooltip
                tooltipClassName="w-56"
                content={
                  <div className="rounded-xl border border-white/10 bg-[#070b14]/95 px-3 py-2 text-[0.7rem] font-medium leading-4 text-slate-200 shadow-[0_16px_40px_rgba(0,0,0,0.36)]">
                    {meta.tooltip}
                  </div>
                }
              >
                <p className="cursor-help text-xs font-semibold text-slate-200">{config.title}</p>
              </HoverTooltip>
              <span className="shrink-0 rounded-full border border-white/[0.08] bg-[#071018] px-2 py-0.5 text-[0.62rem] font-semibold text-slate-300">
                {getSocioeconomicStatus(metric, value)}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-1.5">
              {Array.from({ length: 5 }).map((_, index) => (
                <span
                  key={index}
                  className="grid h-6 w-6 place-items-center rounded-[0.55rem] border"
                  style={{
                    borderColor: index < activeIcons ? `${color}55` : "rgba(255,255,255,0.055)",
                    backgroundColor: index < activeIcons ? `${color}24` : "rgba(255,255,255,0.025)",
                    color: index < activeIcons ? color : "rgba(100,116,139,0.7)",
                  }}
                >
                  <Icon className="h-3.5 w-3.5" strokeWidth={1.8} />
                </span>
              ))}
              <span className="ml-auto text-xs font-semibold tabular-nums text-slate-400">
                {value == null ? "N/A" : `${value.toFixed(1)}%`}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SocioeconomicIntelligencePanel({
  title,
  subtitle,
  selectedSectionId,
  municipalityId,
  currentCollection,
  currentSection,
  year,
  subLayer,
  productiveVariable,
  onProductiveVariableChange,
  onRoot,
}: {
  title: string;
  subtitle: string;
  selectedSectionId?: string | null;
  municipalityId: string;
  currentCollection?: SectionFeatureCollection | null;
  currentSection?: SectionFeatureProperties | null;
  year: string;
  subLayer: string | null;
  productiveVariable: ProductivePotentialVariableKey;
  onProductiveVariableChange: (variable: ProductivePotentialVariableKey) => void;
  onRoot: () => void;
}) {
  const [latestProductiveCollection, setLatestProductiveCollection] = useState<SectionFeatureCollection | null>(null);
  const activeSubLayer = subLayer === "productivePotential" ? "productivePotential" : "socialDevelopment";

  useEffect(() => {
    if (activeSubLayer !== "productivePotential" || year === SOCIAL_DEVELOPMENT_UI_YEAR || latestProductiveCollection) {
      return undefined;
    }

    let active = true;
    void fetchSectionsGeoJson(municipalityId, SOCIAL_DEVELOPMENT_UI_YEAR, "socioeconomicIntelligence")
      .then((collection) => {
        if (active) {
          setLatestProductiveCollection(collection);
        }
      })
      .catch((error) => {
        if (active) {
          console.error("[SocTrace] productive potential latest-data preload failed", error);
        }
      });

    return () => {
      active = false;
    };
  }, [activeSubLayer, latestProductiveCollection, municipalityId, year]);

  const activeProfile = useMemo(
    () =>
      selectedSectionId && currentSection
        ? currentSection
        : getSocioeconomicProfileFromCollection(currentCollection, selectedSectionId),
    [currentCollection, currentSection, selectedSectionId],
  );
  const latestProductiveProfile = useMemo(
    () =>
      year === SOCIAL_DEVELOPMENT_UI_YEAR
        ? activeProfile
        : getSocioeconomicProfileFromCollection(latestProductiveCollection, selectedSectionId),
    [activeProfile, latestProductiveCollection, selectedSectionId, year],
  );
  const productiveProfile = useMemo(
    () => mergeProductiveProfiles(activeProfile, latestProductiveProfile),
    [activeProfile, latestProductiveProfile],
  );
  const activePoints = getSocioeconomicSignalPoints(activeProfile);

  return (
    <Panel className="flex h-auto min-h-full flex-col overflow-visible p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Inteligencia socioeconómica
          </p>
          <h2 className="font-manrope mt-2 truncate text-left text-[1.7rem] font-semibold tracking-[-0.04em] text-white">
            {title}
          </h2>
          <p className="font-manrope mt-1.5 text-left text-sm font-medium text-slate-400">{subtitle}</p>
          <p className="mt-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-cyan-200/70">
            {activeSubLayer === "productivePotential" ? "Potencial productivo" : "Desarrollo social"}
          </p>
        </div>
        {activeSubLayer === "productivePotential" ? (
          <button
            type="button"
            onClick={onRoot}
            className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100 transition hover:border-cyan-200/30 hover:bg-cyan-200/[0.13] hover:text-white"
          >
            Root
          </button>
        ) : null}
      </div>

      {activeSubLayer === "productivePotential" ? (
        <ProductivePotentialPanel
          section={productiveProfile}
          activeVariable={productiveVariable}
          onVariableChange={onProductiveVariableChange}
        />
      ) : (
        <SocialDevelopmentPanel section={activeProfile} points={activePoints} />
      )}
    </Panel>
  );
}

function SocialDevelopmentPanel({
  section,
  points,
}: {
  section?: SectionFeatureProperties | null;
  points: SocioeconomicSignalPoint[];
}) {
  if (!hasCompleteSocioeconomicProfile(section)) {
    return (
      <Panel className="mt-6 p-4">
        <p className="text-sm text-slate-300">No socioeconomic signal available for this selection.</p>
      </Panel>
    );
  }

  return (
    <>
      <SocialDevelopmentRadarChart points={points} />
      <SocioeconomicPictogramRows points={points} />
    </>
  );
}

function mergeProductiveProfiles(
  current?: SectionFeatureProperties | null,
  fallback?: SectionFeatureProperties | null,
) {
  if (!current) {
    return fallback ?? null;
  }
  if (!fallback) {
    return current;
  }

  const merged: SectionFeatureProperties = { ...current };
  (Object.keys(fallback) as (keyof SectionFeatureProperties)[]).forEach((key) => {
    if (merged[key] == null && fallback[key] != null) {
      (merged as Record<keyof SectionFeatureProperties, SectionFeatureProperties[keyof SectionFeatureProperties]>)[key] = fallback[key];
    }
  });
  return merged;
}

function SocialDevelopmentRadarChart({ points }: { points: SocioeconomicSignalPoint[] }) {
  const size = 300;
  const centerX = size / 2;
  const centerY = size / 2;
  const radarRadius = 84;
  const labelRadius = radarRadius + 20;
  const plotted = points.map((point, index) => {
    const value = point.value ?? 0;
    const angle = -Math.PI / 2 + (index / points.length) * Math.PI * 2;
    const radius = (Math.min(100, Math.max(0, value)) / 100) * radarRadius;
    const labelX = centerX + Math.cos(angle) * labelRadius;
    const labelY = centerY + Math.sin(angle) * labelRadius;
    const horizontalAlignment =
      labelX < centerX - 18 ? "right" : labelX > centerX + 18 ? "left" : "center";
    const verticalAlignment =
      labelY < centerY - 58 ? "top" : labelY > centerY + 58 ? "bottom" : "middle";
    const anchor =
      verticalAlignment === "top"
        ? "top"
        : verticalAlignment === "bottom"
          ? "bottom"
          : horizontalAlignment;

    return {
      ...point,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      labelX,
      labelY,
      anchor,
    };
  });
  const polygon = plotted.map((point) => `${point.x},${point.y}`).join(" ");
  const rings = [0.35, 0.68, 1];

  return (
    <div className="mt-4 min-w-0 rounded-2xl border border-white/[0.06] bg-[#0d1423] p-2.5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Social Development Radar
        </p>
        <p className="text-[0.68rem] font-semibold text-slate-500">score %</p>
      </div>
      <div className="relative mx-auto mt-1.5 aspect-square w-[240px] max-w-full overflow-visible">
        <svg className="absolute inset-0 h-full w-full overflow-visible" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Social Development radar" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="socioeconomic-radar-fill">
              <stop offset="0%" stopColor="#67e8f9" stopOpacity="0.38" />
              <stop offset="100%" stopColor="#67e8f9" stopOpacity="0.08" />
            </radialGradient>
          </defs>
          {rings.map((ring) => (
            <polygon
              key={ring}
              points={points
                .map((_, index) => {
                  const angle = -Math.PI / 2 + (index / points.length) * Math.PI * 2;
                  return `${centerX + Math.cos(angle) * radarRadius * ring},${centerY + Math.sin(angle) * radarRadius * ring}`;
                })
                .join(" ")}
              fill="none"
              stroke="rgba(148,163,184,0.16)"
              strokeWidth="1"
            />
          ))}
          {points.map((_, index) => {
            const angle = -Math.PI / 2 + (index / points.length) * Math.PI * 2;
            return (
              <line
                key={index}
                x1={centerX}
                y1={centerY}
                x2={centerX + Math.cos(angle) * radarRadius}
                y2={centerY + Math.sin(angle) * radarRadius}
                stroke="rgba(148,163,184,0.13)"
              />
            );
          })}
          <polygon points={polygon} fill="url(#socioeconomic-radar-fill)" stroke="#67e8f9" strokeWidth="2.5" />
          {plotted.map((point) => (
            <g key={point.metric}>
              <circle cx={point.x} cy={point.y} r="3" fill="#cffafe" />
            </g>
          ))}
        </svg>
        {plotted.map((point) => (
          <div
            key={point.metric}
            className={`absolute w-[4.6rem] ${
              point.anchor === "right"
                ? "-translate-x-full -translate-y-1/2"
                : point.anchor === "top"
                  ? "-translate-x-1/2 -translate-y-full"
                  : point.anchor === "bottom"
                    ? "-translate-x-1/2"
                    : point.anchor === "center"
                      ? "-translate-x-1/2 -translate-y-1/2"
                      : "-translate-y-1/2"
            }`}
            style={{
              left: `${(point.labelX / size) * 100}%`,
              top: `${(point.labelY / size) * 100}%`,
            }}
            aria-hidden="true"
          >
            <span
              className={`block w-full whitespace-normal text-[0.52rem] font-semibold leading-[0.62rem] text-slate-400 ${
                point.anchor === "right" ? "text-right" : point.anchor === "top" || point.anchor === "bottom" || point.anchor === "center" ? "text-center" : "text-left"
              }`}
            >
              {SOCIOECONOMIC_METRICS[point.metric].shortTitle}
            </span>
            <span
              className={`mt-0.5 block text-[0.62rem] font-semibold tabular-nums text-cyan-100 ${
                point.anchor === "right" ? "text-right" : point.anchor === "top" || point.anchor === "bottom" || point.anchor === "center" ? "text-center" : "text-left"
              }`}
            >
              {point.value == null ? "N/A" : `${point.value.toFixed(1)}%`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const productiveVariableLabels: Record<ProductivePotentialVariableKey, string> = {
  educationLevel: "Education Level",
  occupation: "Occupation",
  economicActivity: "Economic Activity",
  incomeSource: "Income Source",
  professionalStatus: "Professional Status",
};

const productiveVariableButtons: ProductivePotentialVariableKey[] = [
  "educationLevel",
  "occupation",
  "economicActivity",
  "incomeSource",
  "professionalStatus",
];

type ProductiveDistributionItem = {
  label: string;
  value: number | null;
  color: string;
};

function normalizeShare(value?: number | null) {
  if (value == null || !Number.isFinite(value)) {
    return null;
  }
  return value > 0 && value <= 1 ? value * 100 : value;
}

function normalizeDistribution(items: ProductiveDistributionItem[]) {
  const valid = items
    .map((item) => ({ ...item, value: normalizeShare(item.value) }))
    .filter((item): item is ProductiveDistributionItem & { value: number } => item.value != null && item.value > 0);
  const total = valid.reduce((sum, item) => sum + item.value, 0);
  if (total <= 0) {
    return [];
  }
  return valid.map((item) => ({ ...item, value: (item.value / total) * 100 }));
}

function getProductiveDistribution(
  section: SectionFeatureProperties | null | undefined,
  variable: ProductivePotentialVariableKey,
) {
  if (!section) {
    return [];
  }

  const distributions: Record<ProductivePotentialVariableKey, ProductiveDistributionItem[]> = {
    educationLevel: [
      { label: "Primary or below", value: section.pct_primary_or_below ?? section.pct_no_studies ?? null, color: "#67e8f9" },
      { label: "Lower secondary", value: section.pct_lower_secondary ?? null, color: "#93c5fd" },
      { label: "Upper secondary", value: section.pct_upper_secondary ?? null, color: "#c4b5fd" },
      { label: "Higher studies", value: section.pct_higher_studies ?? null, color: "#99f6e4" },
    ],
    occupation: [
      { label: "Employed", value: section.pct_employed ?? null, color: "#99f6e4" },
      { label: "Unemployed", value: section.pct_unemployed ?? null, color: "#fca5a5" },
      { label: "Student", value: section.pct_student ?? null, color: "#93c5fd" },
      { label: "Pensioner", value: section.pct_pensioner ?? null, color: "#c4b5fd" },
      { label: "Other inactive", value: section.pct_other_inactive ?? null, color: "#fcd34d" },
    ],
    economicActivity: [
      { label: "Services", value: section.pct_services ?? null, color: "#67e8f9" },
      { label: "Construction", value: section.pct_construction ?? null, color: "#fbbf24" },
      { label: "Industry", value: section.pct_industry ?? null, color: "#a7f3d0" },
      { label: "Agriculture", value: section.pct_agriculture ?? null, color: "#86efac" },
    ],
    incomeSource: [
      { label: "Salary", value: section.income_salary ?? null, color: "#67e8f9" },
      { label: "Pension", value: section.income_pension ?? null, color: "#c4b5fd" },
      { label: "Unemployment benefits", value: section.income_unemployment_benefits ?? section.income_unemployment ?? null, color: "#fca5a5" },
      { label: "Social benefits", value: section.income_social_benefits ?? null, color: "#fcd34d" },
      { label: "Other income", value: section.income_other ?? null, color: "#99f6e4" },
    ],
    professionalStatus: [
      { label: "Employee or other", value: section.pct_employee_or_other ?? section.pct_employee ?? null, color: "#67e8f9" },
      { label: "Self-employed", value: section.pct_self_employed ?? null, color: "#99f6e4" },
    ],
  };

  if (
    variable === "educationLevel" &&
    section.pct_lower_secondary == null &&
    section.pct_upper_secondary == null &&
    section.pct_secondary_studies != null
  ) {
    return normalizeDistribution([
      { label: "Primary or below", value: section.pct_no_studies ?? null, color: "#67e8f9" },
      { label: "Secondary studies", value: section.pct_secondary_studies ?? null, color: "#93c5fd" },
      { label: "Higher studies", value: section.pct_higher_studies ?? null, color: "#99f6e4" },
    ]);
  }
  return normalizeDistribution(distributions[variable]);
}

function polarToCartesian(cx: number, cy: number, radius: number, angle: number) {
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function describeArc(cx: number, cy: number, radius: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, radius, startAngle);
  const end = polarToCartesian(cx, cy, radius, endAngle);
  const largeArcFlag = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
}

function ProductivePotentialDonut({
  section,
  activeVariable,
}: {
  section?: SectionFeatureProperties | null;
  activeVariable: ProductivePotentialVariableKey;
}) {
  const data = getProductiveDistribution(section, activeVariable);
  const dominant = data.reduce((best, item) => (item.value > best.value ? item : best), data[0] ?? { value: 0 });
  const size = 240;
  const center = size / 2;
  const baseRadius = 78;
  let cursor = -Math.PI / 2;

  if (data.length === 0) {
    return (
      <div className="mt-4 flex h-72 items-center justify-center rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 text-sm text-slate-500">
        No productive distribution available.
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-3xl border border-cyan-300/12 bg-[radial-gradient(circle_at_50%_0%,rgba(34,211,238,0.12),rgba(255,255,255,0.025)_54%)] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          {productiveVariableLabels[activeVariable]}
        </p>
        <p className="text-[0.68rem] font-semibold text-slate-500">share %</p>
      </div>
      <div className="relative mx-auto mt-2 h-[240px] w-[240px] max-w-full">
        <svg className="h-full w-full overflow-visible" viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${productiveVariableLabels[activeVariable]} donut`}>
          <circle cx={center} cy={center} r={baseRadius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="28" />
          {data.map((item) => {
            const startAngle = cursor;
            const endAngle = cursor + (item.value / 100) * Math.PI * 2 - 0.012;
            cursor = endAngle + 0.012;
            const dominantSegment = item.label === dominant.label;
            return (
              <path
                key={item.label}
                d={describeArc(center, center, dominantSegment ? baseRadius + 3 : baseRadius, startAngle, endAngle)}
                fill="none"
                stroke={item.color}
                strokeLinecap="round"
                strokeWidth={dominantSegment ? 36 : 27}
                opacity={dominantSegment ? 0.98 : 0.72}
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 grid place-items-center text-center">
          <div>
            <p className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-slate-500">
              {productiveVariableLabels[activeVariable]}
            </p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-white">
              {dominant.value.toFixed(1)}%
            </p>
            <p className="mt-1 max-w-[7rem] text-[0.68rem] font-semibold text-cyan-100">
              {dominant.label}
            </p>
          </div>
        </div>
      </div>
      <div className="mt-2 grid gap-2">
        {data.map((item) => (
          <div key={item.label} className="flex items-center justify-between gap-3 rounded-2xl border border-white/[0.055] bg-white/[0.03] px-3 py-2">
            <span className="flex min-w-0 items-center gap-2 text-xs font-medium text-slate-300">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="truncate">{item.label}</span>
            </span>
            <span className="shrink-0 text-xs font-semibold tabular-nums text-slate-100">{item.value.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProductiveVariableSelector({
  activeVariable,
  onChange,
}: {
  activeVariable: ProductivePotentialVariableKey;
  onChange: (variable: ProductivePotentialVariableKey) => void;
}) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-1.5">
      {productiveVariableButtons.filter((variable) => variable !== activeVariable).map((variable) => {
        const active = activeVariable === variable;
        return (
          <button
            key={variable}
            type="button"
            onClick={() => onChange(variable)}
            className={`min-h-9 rounded-2xl border px-2.5 py-2 text-xs font-semibold transition ${
              active
                ? "border-cyan-300/28 bg-cyan-300/[0.11] text-cyan-50 shadow-[0_0_22px_rgba(34,211,238,0.08)]"
                : "border-white/[0.07] bg-white/[0.035] text-slate-400 hover:border-cyan-300/15 hover:bg-white/[0.055] hover:text-slate-100"
            }`}
          >
            {productiveVariableLabels[variable]}
          </button>
        );
      })}
    </div>
  );
}

function getGiniStatus(value?: number | null) {
  if (value == null || !Number.isFinite(value)) {
    return "No wealth distribution signal";
  }
  if (value < 0.26) return "Balanced distribution";
  if (value < 0.31) return "Mild concentration";
  if (value < 0.36) return "Uneven distribution";
  if (value < 0.42) return "High inequality pressure";
  return "Strong concentration";
}

function GiniGaugeChart({ section }: { section?: SectionFeatureProperties | null }) {
  const raw = normalizeShare(section?.gini_index);
  const gini = raw == null ? null : raw > 1 ? raw / 100 : raw;
  const normalized = gini == null ? 0 : Math.min(1, Math.max(0, gini));
  const radius = 74;
  const center = 120;
  const baseline = 116;
  const arcPath = `M ${center - radius} ${baseline} A ${radius} ${radius} 0 0 1 ${center + radius} ${baseline}`;
  const circumference = Math.PI * radius;
  const dash = normalized * circumference;

  return (
    <div className="mt-3 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Gini / Wealth Distribution</p>
        <p className="text-[0.68rem] font-semibold text-slate-500">0-1</p>
      </div>
      <div className="relative mt-2 h-32">
        <svg className="h-full w-full overflow-visible" viewBox="0 0 240 140" role="img" aria-label="Gini gauge" preserveAspectRatio="xMidYMid meet">
          <path d={arcPath} fill="none" stroke="rgba(148,163,184,0.14)" strokeLinecap="round" strokeWidth="13" />
          <path d={arcPath} fill="none" stroke="#67e8f9" strokeDasharray={`${dash} ${circumference}`} strokeLinecap="round" strokeWidth="13" />
        </svg>
        <div className="absolute inset-x-0 bottom-3 text-center">
          <p className="text-[1.65rem] font-semibold leading-none tabular-nums text-white">
            {gini == null ? "N/A" : gini.toFixed(2)}
          </p>
          <p className="mt-1 text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Gini index</p>
        </div>
      </div>
      <div className="flex items-center justify-between border-t border-white/[0.06] pt-3">
        <span className="text-xs text-slate-500">Interpretation</span>
        <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-xs font-semibold text-cyan-100">
          {getGiniStatus(gini)}
        </span>
      </div>
    </div>
  );
}

function ProductivePotentialPanel({
  section,
  activeVariable,
  onVariableChange,
}: {
  section?: SectionFeatureProperties | null;
  activeVariable: ProductivePotentialVariableKey;
  onVariableChange: (variable: ProductivePotentialVariableKey) => void;
}) {
  return (
    <>
      <ProductivePotentialDonut section={section} activeVariable={activeVariable} />
      <ProductiveVariableSelector activeVariable={activeVariable} onChange={onVariableChange} />
      <GiniGaugeChart section={section} />
    </>
  );
}

function buildMunicipalitySocioeconomicProfile(
  collection?: SectionFeatureCollection | null,
): SectionFeatureProperties | null {
  if (!collection || collection.features.length === 0) {
    return null;
  }

  const averageField = (field: keyof SectionFeatureProperties) => {
    const values = collection.features
      .map((feature) => toFiniteNumber(feature.properties[field] as number | string | null))
      .filter((value): value is number => value != null);
    return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
  };

  return {
    section_id: "municipality",
    municipality_id: collection.features[0]?.properties.municipality_id ?? "29070",
    municipality: collection.features[0]?.properties.municipality ?? "Mijas",
    district: "Municipality",
    section_number: null,
    label_cliente: "Mijas",
    human_capital_index: averageField("human_capital_index"),
    vulnerability_index: averageField("vulnerability_index"),
    resilience_index: averageField("resilience_index"),
    productive_complexity_index: averageField("productive_complexity_index"),
    inequality_pressure_index: averageField("inequality_pressure_index"),
    human_capital_completeness_pct: averageField("human_capital_completeness_pct"),
    vulnerability_completeness_pct: averageField("vulnerability_completeness_pct"),
    resilience_completeness_pct: averageField("resilience_completeness_pct"),
    productive_complexity_completeness_pct: averageField("productive_complexity_completeness_pct"),
    inequality_pressure_completeness_pct: averageField("inequality_pressure_completeness_pct"),
    human_capital_label: "Municipal baseline",
    vulnerability_label: "Municipal baseline",
    resilience_label: "Municipal baseline",
    productive_complexity_label: "Municipal baseline",
    inequality_pressure_label: "Municipal baseline",
    pct_higher_studies: averageField("pct_higher_studies"),
    pct_no_studies: averageField("pct_no_studies"),
    pct_primary_or_below: averageField("pct_primary_or_below"),
    pct_lower_secondary: averageField("pct_lower_secondary"),
    pct_upper_secondary: averageField("pct_upper_secondary"),
    pct_secondary_studies: averageField("pct_secondary_studies"),
    pct_employed: averageField("pct_employed"),
    pct_unemployed: averageField("pct_unemployed"),
    pct_student: averageField("pct_student"),
    pct_pensioner: averageField("pct_pensioner"),
    pct_other_inactive: averageField("pct_other_inactive"),
    pct_self_employed: averageField("pct_self_employed"),
    pct_employee: averageField("pct_employee"),
    pct_employee_or_other: averageField("pct_employee_or_other"),
    pct_services: averageField("pct_services"),
    pct_construction: averageField("pct_construction"),
    pct_industry: averageField("pct_industry"),
    pct_agriculture: averageField("pct_agriculture"),
    pct_directors_managers: averageField("pct_directors_managers"),
    pct_technicians_professionals: averageField("pct_technicians_professionals"),
    pct_directors_managers_professionals: averageField("pct_directors_managers_professionals"),
    pct_qualified_occupations: averageField("pct_qualified_occupations"),
    pct_skilled_workers: averageField("pct_skilled_workers"),
    pct_elementary_occupations: averageField("pct_elementary_occupations"),
    gini_index: averageField("gini_index"),
    p80_p20_ratio: averageField("p80_p20_ratio"),
    income_salary: averageField("income_salary"),
    income_pension: averageField("income_pension"),
    income_unemployment_benefits: averageField("income_unemployment_benefits"),
    income_social_benefits: averageField("income_social_benefits"),
    income_other: averageField("income_other"),
    education_high_norm: averageField("education_high_norm"),
    low_education_norm: averageField("low_education_norm"),
    qualified_occupation_norm: averageField("qualified_occupation_norm"),
    employment_norm: averageField("employment_norm"),
    unemployment_norm: averageField("unemployment_norm"),
    income_norm: averageField("income_norm"),
    low_income_norm: averageField("low_income_norm"),
    social_benefits_norm: averageField("social_benefits_norm"),
    ageing_pressure_norm: averageField("ageing_pressure_norm"),
    gini_norm: averageField("gini_norm"),
    lower_gini_norm: averageField("lower_gini_norm"),
    p80_p20_norm: averageField("p80_p20_norm"),
    income_diversity_norm: averageField("income_diversity_norm"),
    sector_diversity_norm: averageField("sector_diversity_norm"),
    business_activity_norm: averageField("business_activity_norm"),
    self_employment_norm: averageField("self_employment_norm"),
    income_polarization_norm: averageField("income_polarization_norm"),
  };
}

function buildMunicipalityHousingProfile(
  collection?: SectionFeatureCollection | null,
): SectionFeatureProperties | null {
  if (!collection || collection.features.length === 0) {
    return null;
  }

  const averageField = (field: keyof SectionFeatureProperties) => {
    const values = collection.features
      .map((feature) => toFiniteNumber(feature.properties[field] as number | string | null))
      .filter((value): value is number => value != null);
    return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
  };

  return {
    section_id: "municipality",
    municipality_id: collection.features[0]?.properties.municipality_id ?? "29070",
    municipality: collection.features[0]?.properties.municipality ?? "Mijas",
    district: "Municipality",
    section_number: null,
    label_cliente: "Mijas",
    quality_life_score: averageField("quality_life_score"),
    market_pressure_index: averageField("market_pressure_index"),
    opportunity_signal_score: averageField("opportunity_signal_score"),
    opportunity_zone_score: averageField("opportunity_zone_score"),
    residential_saturation_index: averageField("residential_saturation_index"),
    residential_balance_score:
      averageField("residential_balance_score") ??
      (averageField("residential_saturation_index") == null
        ? null
        : 100 - (averageField("residential_saturation_index") ?? 0)),
    urban_prestige_signal: averageField("urban_prestige_signal"),
    foreign_demand_exposure: averageField("foreign_demand_exposure"),
    international_appeal_score: averageField("international_appeal_score") ?? averageField("foreign_demand_exposure"),
    territorial_signal_score: averageField("territorial_signal_score"),
    housing_signal_score: averageField("housing_signal_score"),
    safety_potential_score: averageField("safety_potential_score"),
    noise_exposure_potential: averageField("noise_exposure_potential"),
    housing_stress_index: averageField("housing_stress_index"),
    daily_life_access_score: averageField("daily_life_access_score"),
    quietness_potential: averageField("quietness_potential"),
    residential_stability_proxy: averageField("residential_stability_proxy"),
    socioeconomic_resilience_proxy: averageField("socioeconomic_resilience_proxy"),
    mobility_friction_proxy: averageField("mobility_friction_proxy"),
    extreme_market_pressure: averageField("extreme_market_pressure"),
    market_reference_m2: averageField("market_reference_m2"),
    market_pressure_label: "Municipal baseline",
    opportunity_label: "Municipal baseline",
    residential_profile_label: "Municipal baseline",
    prestige_label: "Municipal baseline",
    territorial_signal_label: "Municipal baseline",
    strategic_profile_label: "Municipal absolute position",
    confidence_level: "Municipal baseline",
    calibration_source: "municipal aggregation",
  };
}

function getHousingStrategicReadingText(metric: TerritorialMetricKey) {
  const readings: Partial<Record<TerritorialMetricKey, string>> = {
    qualityLife:
      "Calidad de vida resume habitabilidad, presión residencial, oportunidad y estabilidad estratégica.",
    perceivedSafetyPotential:
      "Es una señal sintética de percepción de seguridad residencial, no una capa de predicción del delito.",
    noiseExposurePotential:
      "Esta señal estima exposición potencial al ruido a partir de proxies de presión urbana, no decibelios medidos.",
    airQualityPotential:
      "El potencial de calidad del aire queda reservado para integrar futuros datos ambientales.",
    marketPressure:
      "High comparative pressure indicates stronger market tension relative to other sections.",
    urbanPrestige:
      "This signal summarizes territorial attractiveness and consolidated residential positioning.",
    opportunitySignal:
      "This section combines market signals and territorial conditions suggesting strategic opportunity.",
    residentialSaturation:
      "This signal reflects built intensity and capacity constraints in the residential fabric.",
    territorialSignal:
      "The composite housing score summarizes market, territorial and demand signals for comparison.",
    foreignDemand:
      "This signal estimates relative exposure to external residential demand within the municipality.",
  };

  return readings[metric] ?? readings.qualityLife;
}

function HousingStrategicReadingBox({ metric }: { metric: TerritorialMetricKey }) {
  return (
    <div className="rounded-2xl border border-violet-300/12 bg-violet-300/[0.045] px-3 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-violet-100">
        Strategic Reading
      </p>
      <p className="mt-2 text-xs font-medium leading-5 text-slate-300">
        {getHousingStrategicReadingText(metric)}
      </p>
    </div>
  );
}

type HousingRadarMetricKey =
  | "marketPressure"
  | "urbanPrestige"
  | "opportunityZones"
  | "residentialBalance"
  | "housingSignal"
  | "internationalAppeal";

const housingRadarAxes: {
  id: HousingRadarMetricKey;
  label: string;
  tooltip: string;
  accent: "teal" | "blue" | "amber" | "emerald" | "violet" | "cyan";
  icon: typeof SignalHigh;
}[] = [
  {
    id: "marketPressure",
    label: "Market Pressure",
    tooltip: "Strength of residential and market demand in this section.",
    accent: "amber",
    icon: Activity,
  },
  {
    id: "urbanPrestige",
    label: "Urban Prestige",
    tooltip: "Perceived territorial attractiveness and premium residential character.",
    accent: "violet",
    icon: Gem,
  },
  {
    id: "opportunityZones",
    label: "Opportunity Zones",
    tooltip: "Strategic potential for residential, urban or market positioning.",
    accent: "cyan",
    icon: Target,
  },
  {
    id: "residentialBalance",
    label: "Residential Balance",
    tooltip: "Residential balance and breathing space considering density, built footprint and comfort.",
    accent: "emerald",
    icon: Scale,
  },
  {
    id: "housingSignal",
    label: "Housing Signal Score",
    tooltip: "Overall strategic housing-related signal for this section.",
    accent: "blue",
    icon: Gauge,
  },
  {
    id: "internationalAppeal",
    label: "International Appeal",
    tooltip: "Attractiveness for international or non-local residential demand.",
    accent: "teal",
    icon: Globe2,
  },
];

function clampHousingScore(value?: number | string | null) {
  const numeric = toFiniteNumber(value);
  return numeric == null ? null : Math.min(100, Math.max(0, numeric));
}

function getHousingRadarValue(section: SectionFeatureProperties, metric: HousingRadarMetricKey) {
  if (metric === "marketPressure") {
    return clampHousingScore(section.market_pressure_index);
  }
  if (metric === "urbanPrestige") {
    return clampHousingScore(section.urban_prestige_signal);
  }
  if (metric === "opportunityZones") {
    return clampHousingScore(section.opportunity_zone_score ?? section.opportunity_signal_score);
  }
  if (metric === "residentialBalance") {
    const explicit = clampHousingScore(section.residential_balance_score);
    if (explicit != null) {
      return explicit;
    }
    const saturation = clampHousingScore(section.residential_saturation_index);
    return saturation == null ? null : 100 - saturation;
  }
  if (metric === "housingSignal") {
    return clampHousingScore(section.housing_signal_score ?? section.territorial_signal_score);
  }

  return clampHousingScore(section.international_appeal_score ?? section.foreign_demand_exposure);
}

function getHousingMetricQualitativeLabel(metric: HousingRadarMetricKey, value?: number | null) {
  if (value == null) {
    return "N/A";
  }

  if (metric === "residentialBalance") {
    if (value <= 25) return "Low Balance";
    if (value <= 50) return "Moderate";
    if (value <= 75) return "Balanced";
    return "Strong Balance";
  }

  if (metric === "marketPressure") {
    if (value <= 25) return "Low Pressure";
    if (value <= 50) return "Moderate";
    if (value <= 75) return "High";
    return "Very High";
  }

  if (value <= 25) return "Low";
  if (value <= 50) return "Moderate";
  if (value <= 75) return "High";
  return "Very High";
}

function formatHousingMetricScore(value?: number | null) {
  return value == null ? "—" : value.toFixed(1);
}

function getQualityLifeLabel(section: SectionFeatureProperties) {
  const explicit = section.strategic_profile_label?.trim();
  if (explicit) {
    return explicit;
  }

  const score = toFiniteNumber(section.quality_life_score);
  if (score == null) {
    return "N/A";
  }
  if (score >= 82) {
    return "Premium";
  }
  if (score >= 68) {
    return "High";
  }
  if (score >= 52) {
    return "Balanced";
  }
  if ((section.housing_stress_index ?? 0) >= 70 || (getHousingRadarValue(section, "residentialBalance") ?? 100) < 35) {
    return "Pressured";
  }
  return "Low";
}

function buildHousingStrategicReading(section: SectionFeatureProperties, scope: "municipality" | "section") {
  const prestige = toFiniteNumber(section.urban_prestige_signal) ?? 50;
  const pressure = toFiniteNumber(section.market_pressure_index) ?? 50;
  const balance = getHousingRadarValue(section, "residentialBalance") ?? 50;
  const stress = toFiniteNumber(section.housing_stress_index) ?? 50;
  const safety = toFiniteNumber(section.safety_potential_score) ?? 50;
  const noise = toFiniteNumber(section.noise_exposure_potential) ?? 50;
  const opportunity = toFiniteNumber(section.opportunity_zone_score) ?? 50;
  const prefix = scope === "municipality" ? "Mijas" : "This section";

  if (prestige >= 70 && pressure >= 68 && balance <= 45) {
    return `${prefix} shows strong market pressure but only moderate residential balance, suggesting a more pressured urban environment.`;
  }
  if (safety >= 68 && noise <= 42 && stress <= 48) {
    return `${prefix} offers balanced residential quality, lower pressure and strong livability conditions.`;
  }
  if (opportunity >= 70 && pressure <= 62) {
    return `${prefix} shows strategic upside with opportunity signals that are not solely explained by market pressure.`;
  }
  if (stress >= 70 || noise >= 72) {
    return `${prefix} keeps relevant demand signals, but quality is moderated by lower residential balance and exposure pressure.`;
  }
  return `${prefix} presents a balanced residential intelligence profile across prestige, opportunity, pressure and livability conditions.`;
}

function HousingRadarChart({ section }: { section: SectionFeatureProperties }) {
  const size = 300;
  const centerX = size / 2;
  const centerY = size / 2;
  const radarRadius = 82;
  const labelOffset = 18;
  const labelRadius = radarRadius + labelOffset;
  const points = housingRadarAxes.map((axis, index) => {
    const value = getHousingRadarValue(section, axis.id) ?? 50;
    const angle = -Math.PI / 2 + (index / housingRadarAxes.length) * Math.PI * 2;
    const radius = (Math.min(100, Math.max(0, value)) / 100) * radarRadius;
    const labelX = centerX + Math.cos(angle) * labelRadius;
    const labelY = centerY + Math.sin(angle) * labelRadius - (axis.id === "urbanPrestige" ? 7 : 0);
    const horizontalAlignment =
      labelX < centerX - 18 ? "right" : labelX > centerX + 18 ? "left" : "center";
    const verticalAlignment =
      labelY < centerY - 58 ? "top" : labelY > centerY + 58 ? "bottom" : "middle";
    const anchor =
      verticalAlignment === "top"
        ? "top"
        : verticalAlignment === "bottom"
          ? "bottom"
          : horizontalAlignment;

    return {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      labelX,
      labelY,
      label: axis.label,
      tooltip: axis.tooltip,
      anchor,
    };
  });
  const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");
  const rings = [0.35, 0.68, 1];

  return (
    <div className="mt-3 min-w-0 rounded-2xl border border-white/[0.06] bg-[#0d1423] p-2.5">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Residential DNA
      </p>
      <div className="relative mx-auto mt-1.5 aspect-square w-[230px] max-w-full overflow-visible">
      <svg className="absolute inset-0 h-full w-full overflow-visible" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Radar de inteligencia inmobiliaria" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id="housing-radar-fill">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.42" />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0.08" />
          </radialGradient>
        </defs>
        {rings.map((ring) => (
          <polygon
            key={ring}
            points={housingRadarAxes
              .map((_, index) => {
                const angle = -Math.PI / 2 + (index / housingRadarAxes.length) * Math.PI * 2;
                return `${centerX + Math.cos(angle) * radarRadius * ring},${centerY + Math.sin(angle) * radarRadius * ring}`;
              })
              .join(" ")}
            fill="none"
            stroke="rgba(148,163,184,0.16)"
            strokeWidth="1"
          />
        ))}
        {housingRadarAxes.map((_, index) => {
          const angle = -Math.PI / 2 + (index / housingRadarAxes.length) * Math.PI * 2;
          return (
            <line
              key={index}
              x1={centerX}
              y1={centerY}
              x2={centerX + Math.cos(angle) * radarRadius}
              y2={centerY + Math.sin(angle) * radarRadius}
              stroke="rgba(148,163,184,0.13)"
            />
          );
        })}
        <polygon points={polygon} fill="url(#housing-radar-fill)" stroke="#2dd4bf" strokeWidth="2.5" />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="3" fill="#99f6e4" />
          </g>
        ))}
      </svg>
      {points.map((point) => (
        <div
          key={point.label}
          className={`absolute w-[4rem] ${
            point.anchor === "right"
              ? "-translate-x-full -translate-y-1/2"
              : point.anchor === "top"
                ? "-translate-x-1/2 -translate-y-full"
                : point.anchor === "bottom"
                  ? "-translate-x-1/2"
                  : point.anchor === "center"
                    ? "-translate-x-1/2 -translate-y-1/2"
                    : "-translate-y-1/2"
            }`}
          style={{
            left: `${(point.labelX / size) * 100}%`,
            top: `${(point.labelY / size) * 100}%`,
          }}
          aria-hidden="true"
        >
          <span
            className={`block w-full whitespace-normal text-[0.52rem] font-semibold leading-[0.62rem] text-slate-400 ${
              point.anchor === "right" ? "text-right" : point.anchor === "top" || point.anchor === "bottom" || point.anchor === "center" ? "text-center" : "text-left"
            }`}
          >
            {point.label}
          </span>
        </div>
      ))}
      </div>
    </div>
  );
}

function HousingMetricCard({
  axis,
  value,
}: {
  axis: (typeof housingRadarAxes)[number];
  value: number | null;
}) {
  const tone = {
    teal: "border-teal-300/16 bg-teal-300/[0.055] text-teal-300 shadow-[0_0_34px_rgba(45,212,191,0.055)]",
    blue: "border-blue-300/16 bg-blue-300/[0.055] text-blue-300 shadow-[0_0_34px_rgba(96,165,250,0.055)]",
    amber: "border-amber-300/16 bg-amber-300/[0.055] text-amber-300 shadow-[0_0_34px_rgba(251,191,36,0.055)]",
    emerald: "border-emerald-300/16 bg-emerald-300/[0.055] text-emerald-300 shadow-[0_0_34px_rgba(52,211,153,0.055)]",
    violet: "border-violet-300/16 bg-violet-300/[0.055] text-violet-300 shadow-[0_0_34px_rgba(167,139,250,0.055)]",
    cyan: "border-cyan-300/16 bg-cyan-300/[0.055] text-cyan-300 shadow-[0_0_34px_rgba(34,211,238,0.055)]",
  }[axis.accent];
  const Icon = axis.icon;

  return (
    <HoverTooltip
      autoFlip
      className="min-w-0"
      tooltipClassName="w-56"
      content={
        <div className="rounded-xl border border-white/10 bg-[#070b14]/95 px-3 py-2 text-[0.7rem] font-medium leading-4 text-slate-200 shadow-[0_16px_40px_rgba(0,0,0,0.36)]">
          {axis.tooltip}
        </div>
      }
    >
      <div className={`flex h-[5.1rem] min-w-0 flex-col justify-between overflow-hidden rounded-2xl border px-2.5 py-2.5 ${tone}`}>
        <div className="flex min-w-0 items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-1.5">
            <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-80" strokeWidth={1.8} />
            <p className="min-w-0 text-[0.62rem] font-medium leading-[0.72rem] text-slate-400">
              <span className="block overflow-hidden text-ellipsis [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]">
                {axis.label}
              </span>
            </p>
          </div>
          <span className="shrink-0 text-[0.68rem] font-semibold leading-none opacity-80">%</span>
        </div>
        <div className="min-w-0">
          <p className="truncate text-[1.12rem] font-semibold leading-none tracking-[-0.02em] tabular-nums">
            {formatHousingMetricScore(value)}
          </p>
          <p className="mt-1.5 truncate text-[0.64rem] font-semibold leading-3 text-slate-100">
            {getHousingMetricQualitativeLabel(axis.id, value)}
          </p>
        </div>
      </div>
    </HoverTooltip>
  );
}

function HousingQualityPanel({
  title,
  subtitle,
  section,
  scope,
}: {
  title: string;
  subtitle: string;
  section: SectionFeatureProperties;
  scope: "municipality" | "section";
}) {
  const score = section.quality_life_score ?? section.territorial_signal_score;
  const label = getQualityLifeLabel(section);
  const accent = TERRITORIAL_METRICS.qualityLife.colors[4];
  const metricCards = housingRadarAxes.map((axis) => ({
    axis,
    value: getHousingRadarValue(section, axis.id),
  }));

  return (
    <Panel className="flex h-auto min-h-full flex-col overflow-visible p-3 pb-4">
      <div>
        <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-teal-200/70">
          Inteligencia inmobiliaria
        </p>
        <h2 className="font-manrope mt-1.5 text-left text-balance text-[1.55rem] font-semibold tracking-[-0.04em] text-white">
          {title}
        </h2>
        <p className="font-manrope mt-1.5 max-w-[15rem] text-left text-xs font-medium text-slate-400">
          {subtitle}
        </p>
      </div>

      <div className="mt-3 rounded-3xl border border-teal-300/12 bg-[radial-gradient(circle_at_50%_0%,rgba(45,212,191,0.13),rgba(255,255,255,0.025)_54%)] p-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Puntuación de calidad de vida
        </p>
        <ArcProgressScore value={score} accent={accent} />
        <div className="mt-2 flex items-center justify-between border-t border-white/[0.06] pt-2.5">
          <span className="text-xs text-slate-500">Posición estratégica</span>
          <span className="rounded-full border border-teal-300/20 bg-teal-300/10 px-2.5 py-1 text-xs font-semibold text-teal-100">
            {label}
          </span>
        </div>
      </div>

      <HousingRadarChart section={section} />

      <div
        className="mt-3 grid min-w-0 grid-cols-3 gap-1.5"
      >
        {metricCards.map((item) => (
          <HousingMetricCard key={item.axis.id} axis={item.axis} value={item.value} />
        ))}
      </div>

      <div className="mt-3 rounded-2xl border border-white/[0.06] bg-white/[0.035] p-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Strategic Reading
        </p>
        <p className="mt-2 text-xs leading-5 text-slate-300">
          {buildHousingStrategicReading(section, scope)}
        </p>
      </div>
    </Panel>
  );
}

function ArcProgressScore({
  value,
  accent,
}: {
  value?: number | null;
  accent: string;
}) {
  const normalized = value == null || !Number.isFinite(value)
    ? 0
    : Math.min(100, Math.max(0, value > 0 && value <= 1 ? value * 100 : value));
  const radius = 74;
  const center = 120;
  const baseline = 116;
  const arcPath = `M ${center - radius} ${baseline} A ${radius} ${radius} 0 0 1 ${center + radius} ${baseline}`;
  const circumference = Math.PI * radius;
  const dash = (normalized / 100) * circumference;

  return (
    <div className="mt-2.5 flex w-full justify-center">
      <div className="relative h-28 w-full max-w-[18.5rem]">
        <svg className="h-full w-full overflow-visible" viewBox="0 0 240 140" role="img" aria-label="Market pressure score" preserveAspectRatio="xMidYMid meet">
          <path
            d={arcPath}
            fill="none"
            stroke="rgba(148,163,184,0.14)"
            strokeLinecap="round"
            strokeWidth="13"
          />
          <path
            d={arcPath}
            fill="none"
            stroke={accent}
            strokeDasharray={`${dash} ${circumference}`}
            strokeLinecap="round"
            strokeWidth="13"
          />
        </svg>
        <div className="absolute inset-x-0 bottom-3 text-center">
          <p className="text-[1.65rem] font-semibold leading-none tabular-nums text-white">{formatScorePercent(value)}</p>
          <p className="mt-1 text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-slate-500">score</p>
        </div>
      </div>
    </div>
  );
}

const ELECTION_TYPE_STYLES: Record<
  ElectionType,
  { label: string; border: string; bg: string; text: string; glow: string }
> = {
  municipales: {
    label: "Municipales",
    border: "border-amber-200/20",
    bg: "bg-amber-200/[0.08]",
    text: "text-amber-100",
    glow: "shadow-[0_0_34px_rgba(251,191,36,0.08)]",
  },
  andaluzas: {
    label: "Andaluzas",
    border: "border-emerald-200/20",
    bg: "bg-emerald-200/[0.08]",
    text: "text-emerald-100",
    glow: "shadow-[0_0_34px_rgba(52,211,153,0.08)]",
  },
  congreso: {
    label: "Congreso",
    border: "border-orange-200/20",
    bg: "bg-orange-200/[0.08]",
    text: "text-orange-100",
    glow: "shadow-[0_0_34px_rgba(251,146,60,0.08)]",
  },
  europeas: {
    label: "Europeas",
    border: "border-sky-200/20",
    bg: "bg-sky-200/[0.08]",
    text: "text-sky-100",
    glow: "shadow-[0_0_34px_rgba(125,211,252,0.08)]",
  },
};

const AGE_COHORTS: AgeCohortDefinition[] = [
  { cohort: "0-14", color: "#2dd4bf", populationField: "population_0_14", featureField: "population_0_14" },
  { cohort: "15-29", color: "#74c476", populationField: "population_15_29", featureField: "population_15_29" },
  { cohort: "30-44", color: "#f2d56b", populationField: "population_30_44", featureField: "population_30_44" },
  { cohort: "45-64", color: "#f59e4b", populationField: "population_45_64", featureField: "population_45_64" },
  { cohort: "65+", color: "#c95c66", populationField: "population_65_plus", featureField: "population_65_plus" },
];

const INCOME_SOURCES: { key: IncomeSourceKey; label: string; color: string }[] = [
  { key: "income_salary", label: "Wages", color: "#67e8f9" },
  { key: "income_pension", label: "Pensions", color: "#c4b5fd" },
  { key: "income_unemployment", label: "Unemployment", color: "#fca5a5" },
  { key: "income_social_benefits", label: "Other benefits", color: "#fcd34d" },
  { key: "income_other", label: "Other income", color: "#86efac" },
];

function electionTypeLabel(type: ElectionType) {
  return ELECTION_TYPE_STYLES[type].label;
}

function ElectionTypePill({ type }: { type: ElectionType }) {
  const style = ELECTION_TYPE_STYLES[type];
  return (
    <span
      className={`inline-flex w-fit rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold ${style.border} ${style.bg} ${style.text} ${style.glow}`}
    >
      {style.label}
    </span>
  );
}

function getFeaturePartyShare(section?: SectionFeatureProperties | null): PartySharePoint[] {
  return section ? getPartyVoteShare(section) : [];
}

function aggregateElectionCollection(collection?: SectionFeatureCollection | null): PartySharePoint[] {
  if (!collection) {
    return [];
  }

  const votesByParty = new Map<string, number>();
  collection.features.forEach((feature) => {
    getFeaturePartyShare(feature.properties).forEach((entry) => {
      if (entry.votes != null && Number.isFinite(entry.votes)) {
        votesByParty.set(entry.party, (votesByParty.get(entry.party) ?? 0) + entry.votes);
      }
    });
  });

  const totalVotes = Array.from(votesByParty.values()).reduce((total, value) => total + value, 0);
  if (totalVotes > 0) {
    return Array.from(votesByParty.entries())
      .map(([party, votes]) => ({ party, votes, percentage: (votes / totalVotes) * 100 }))
      .sort((a, b) => b.percentage - a.percentage || (b.votes ?? 0) - (a.votes ?? 0));
  }

  const percentagesByParty = new Map<string, { total: number; count: number }>();
  collection.features.forEach((feature) => {
    getFeaturePartyShare(feature.properties).forEach((entry) => {
      const current = percentagesByParty.get(entry.party) ?? { total: 0, count: 0 };
      percentagesByParty.set(entry.party, {
        total: current.total + entry.percentage,
        count: current.count + 1,
      });
    });
  });

  return Array.from(percentagesByParty.entries())
    .map(([party, value]) => ({ party, percentage: value.count > 0 ? value.total / value.count : 0 }))
    .sort((a, b) => b.percentage - a.percentage);
}

function getSectionFromCollection(
  collection: SectionFeatureCollection | undefined,
  sectionId: string,
) {
  return collection?.features.find((feature) => feature.properties.section_id === sectionId)?.properties;
}

function getTurnout(section?: SectionFeatureProperties | null) {
  return typeof section?.turnout === "number" && Number.isFinite(section.turnout)
    ? section.turnout * (section.turnout <= 1 ? 100 : 1)
    : null;
}

function toFiniteNumber(value?: number | string | null) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function aggregateTurnout(collection?: SectionFeatureCollection | null) {
  if (!collection || collection.features.length === 0) {
    return null;
  }
  const values = collection.features
    .map((feature) => getTurnout(feature.properties))
    .filter((value): value is number => value != null);
  return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
}

const campaignForecastMetricOrder = [
  "volatility",
  "abstentionRisk",
  "localistPotential",
  "swingSections",
  "forecastConfidence",
] as const satisfies readonly CampaignForecastMetricKey[];

function averageForecastField(
  collection: SectionFeatureCollection | null | undefined,
  metric: CampaignForecastMetricKey,
) {
  const values = (collection?.features ?? [])
    .map((feature) => getCampaignForecastMetricValue(feature.properties, metric))
    .filter((value): value is number => value != null);
  return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
}

function buildMunicipalityCampaignProfile(collection?: SectionFeatureCollection | null): SectionFeatureProperties | null {
  if (!collection || collection.features.length === 0) {
    return null;
  }

  const partyShare = aggregateElectionCollection(collection);
  const leadingParty = partyShare[0]?.party ?? "N/A";
  const leadingPct = partyShare[0]?.percentage ?? null;
  const runnerUpPct = partyShare[1]?.percentage ?? null;
  const margin = leadingPct != null && runnerUpPct != null ? leadingPct - runnerUpPct : null;
  const averageField = (field: keyof SectionFeatureProperties) => {
    const values = collection.features
      .map((feature) => toFiniteNumber(feature.properties[field] as number | string | null))
      .filter((value): value is number => value != null);
    return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
  };

  return {
    section_id: "mijas-total",
    municipality_id: "29070",
    municipality: "Mijas",
    district: "Municipality",
    section_number: null,
    label_cliente: "Mijas total",
    winning_party: leadingParty,
    winning_party_pct: leadingPct,
    projected_leading_party: leadingParty,
    projected_vote_share: leadingPct,
    runner_up_pct: runnerUpPct,
    victory_margin_pct: margin,
    turnout: aggregateTurnout(collection),
    local_vote_pct: averageField("local_vote_pct"),
    national_vote_pct: averageField("national_vote_pct"),
    left_bloc_pct: averageField("left_bloc_pct"),
    right_bloc_pct: averageField("right_bloc_pct"),
    localism_index: averageField("localism_index"),
    fragmentation_index: averageField("fragmentation_index"),
    competitive_parties_count: averageField("competitive_parties_count"),
    volatility: averageForecastField(collection, "volatility"),
    abstention_risk: averageForecastField(collection, "abstentionRisk"),
    localist_potential: averageForecastField(collection, "localistPotential"),
    swing_sections: averageForecastField(collection, "swingSections"),
    forecast_confidence: averageForecastField(collection, "forecastConfidence"),
    structural_forecast_confidence: averageField("structural_forecast_confidence"),
    contextual_vote_adjustment_pct: averageField("contextual_vote_adjustment_pct"),
    contextual_uncertainty: averageField("contextual_uncertainty"),
    has_contextual_adjustments: collection.features.some(
      (feature) => feature.properties.has_contextual_adjustments,
    ),
    turnout_forecast: averageField("turnout_forecast"),
    forecast_swing_territory_count: collection.features.filter(
      (feature) => feature.properties.is_swing_section,
    ).length,
    forecast_confidence_level:
      (averageForecastField(collection, "forecastConfidence") ?? 0) >= 75
        ? "high"
        : (averageForecastField(collection, "forecastConfidence") ?? 0) >= 55
          ? "medium"
          : "low",
    forecast_interpretation:
      "Municipal forecast is an internally modeled structural baseline for 2027. It is not polling and has not been calibrated with Oraculum inputs.",
  };
}

function formatForecastPercent(value?: number | null) {
  return value == null || !Number.isFinite(value) ? "N/A" : `${value.toFixed(1)}%`;
}

const campaignMetricMeanings: Record<CampaignForecastMetricKey, string> = {
  volatility: "Mide cuánto ha cambiado el comportamiento electoral de esta zona entre elecciones anteriores.",
  abstentionRisk: "Estima el riesgo de menor participación a partir de patrones de participación y condiciones locales.",
  localistPotential: "Captura la fuerza potencial del voto localista y la identidad política de proximidad.",
  swingSections: "Mide la probabilidad de cambio electoral en la sección según señales competitivas actuales.",
  forecastConfidence: "Indica la robustez de la señal de previsión electoral disponible.",
};

function ElectoralForecastRing({
  metric,
  value,
}: {
  metric: CampaignForecastMetricKey;
  value: number | null;
}) {
  const config = CAMPAIGN_FORECAST_METRICS[metric];
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(100, Math.max(0, value ?? 0));
  const dashOffset = circumference * (1 - progress / 100);

  return (
    <div className="mt-5 rounded-3xl border border-white/[0.06] bg-[#0d1423] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]">
      <div className="relative mx-auto h-44 w-44">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 160 160" role="img" aria-label={`${config.title} forecast score`}>
          <circle cx="80" cy="80" r={radius} fill="none" stroke="rgba(148,163,184,0.13)" strokeWidth="15" />
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke={config.color}
            strokeWidth="15"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={{
              filter: `drop-shadow(0 0 10px ${config.color}40)`,
              transition: "stroke-dashoffset 520ms ease, stroke 280ms ease",
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <p className="text-3xl font-semibold tabular-nums text-white">{formatForecastPercent(value)}</p>
          <p className="mt-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-slate-500">{config.shortTitle}</p>
        </div>
      </div>
      <div className="mt-3 border-t border-white/[0.06] pt-3">
        <p className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Lectura del indicador</p>
        <p className="mt-1.5 text-xs leading-5 text-slate-400">{campaignMetricMeanings[metric]}</p>
      </div>
    </div>
  );
}

function ForecastVariableSelector({
  activeMetric,
  onMetricChange,
}: {
  activeMetric: CampaignForecastMetricKey;
  onMetricChange: (metric: CampaignForecastMetricKey) => void;
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {campaignForecastMetricOrder
        .filter((metric) => metric !== activeMetric)
        .map((metric) => {
          const config = CAMPAIGN_FORECAST_METRICS[metric];
          return (
            <button
              key={metric}
              type="button"
              onClick={() => onMetricChange(metric)}
              className="h-7 rounded-[0.65rem] border border-white/[0.08] bg-white/[0.025] px-2 text-[0.64rem] font-semibold text-slate-400 transition hover:border-cyan-300/20 hover:bg-white/[0.055] hover:text-slate-100"
            >
              {config.title}
            </button>
          );
        })}
    </div>
  );
}

function ForecastOutlookCard({
  profile,
  isMunicipality,
  scenario,
}: {
  profile: SectionFeatureProperties;
  isMunicipality: boolean;
  scenario?: CampaignScenario | null;
}) {
  const leader = getCampaignForecastLeader(profile);
  const confidence = getCampaignForecastMetricValue(profile, "forecastConfidence");
  const swing = getCampaignForecastMetricValue(profile, "swingSections");
  const partyColor = rgbaToCss(getPartyColor(leader));
  const body = profile.forecast_interpretation ?? (isMunicipality
    ? "La previsión mantiene apoyos más sólidos en secciones urbanas consolidadas, con presión competitiva en zonas de cambio y mayor valor de movilización."
    : swing != null && swing >= 58
      ? "Esta sección muestra una previsión competitiva: la segmentación, la participación y la volatilidad local pueden afectar a la ventaja estimada."
      : "Esta sección presenta una tendencia territorial más consolidada, con menor exposición al cambio electoral y una señal de previsión más clara.");

  return (
    <div className="mt-4 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Lectura de previsión</p>
        <span className="rounded-full border border-white/[0.08] bg-white/[0.035] px-2 py-0.5 text-[0.62rem] font-semibold text-slate-400">
          Base estimada
        </span>
      </div>
      <p className="mt-4 text-xs text-slate-500">Liderazgo previsto</p>
      <div className="mt-1.5 flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: partyColor }} />
        <p className="text-xl font-semibold text-white">{leader}</p>
      </div>
      <p className="mt-3 text-sm leading-5 text-slate-400">{body}</p>
      {profile.has_contextual_adjustments ? (
        <div
          className="mt-3 rounded-2xl border border-cyan-200/10 bg-cyan-200/[0.045] px-3 py-2 text-[0.68rem] leading-4 text-cyan-100/75"
          title="This forecast combines structural electoral data with validated local contextual priors. Contextual priors are treated as hypotheses, not facts."
        >
          {scenario?.contextualForecastCopy ?? "Previsión con ajuste contextual."}
        </div>
      ) : null}
      {scenario?.id === "localist_fragmentation" ? (
        <div className="mt-2 inline-flex rounded-full border border-amber-200/15 bg-amber-200/[0.055] px-2 py-1 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-amber-100/80">
          Escenario condicionado
        </div>
      ) : null}
      <div className="mt-4 grid grid-cols-2 gap-2 border-t border-white/[0.06] pt-3 text-xs">
        <div>
          <p className="text-slate-500">Ventaja estimada</p>
          <p className="mt-1 font-semibold tabular-nums text-slate-100">{formatForecastPercent(getCampaignForecastVoteShare(profile))}</p>
        </div>
        <div>
          <p className="text-slate-500">Confianza</p>
          <p className="mt-1 font-semibold tabular-nums text-slate-100">{formatForecastPercent(confidence)}</p>
        </div>
      </div>
    </div>
  );
}

function getSectionScenarioInterpretation(
  scenarioId: ElectoralScenarioId,
  section: SectionFeatureProperties,
) {
  const drivers = section.contextual_drivers ?? [];
  const driverValue = (prior: string) =>
    toFiniteNumber(drivers.find((driver) => driver.prior === prior)?.value);
  const ppReserve = driverValue("pp_brand_reserve");
  const csPool = driverValue("cs_orphan_vote_pool");

  if (scenarioId === "candidate_reset") {
    return `En Nuevo liderazgo conservador, esta sección prueba el potencial de recuperación del PP a partir de reserva de marca local (${formatForecastPercent(ppReserve)}) y una bolsa incierta de transferencia de Cs (${formatForecastPercent(csPool)}).`;
  }
  if (scenarioId === "localist_fragmentation") {
    return "En Segmentación localista, esta sección se interpreta como una prueba condicionada de fragmentación del centro-derecha y entrada progresista. Es una hipótesis de prototipo, no una encuesta en tiempo real.";
  }
  if (scenarioId === "oraculum_ready") {
    return "En Oraculum, esta sección combina la tendencia estructural con la validación manual de prototipo. No incorpora sondeos en tiempo real.";
  }
  return section.forecast_interpretation ?? "Esta sección muestra la tendencia estructural de previsión con ajustes contextuales acotados.";
}

function ScenarioSelector({
  activeScenarioId,
  onChange,
}: {
  activeScenarioId: ElectoralScenarioId;
  onChange: (scenarioId: ElectoralScenarioId) => void;
}) {
  return (
    <div className="mt-4 rounded-2xl border border-white/[0.07] bg-[#080f1c]/80 p-1.5">
      <div className="grid grid-cols-2 gap-1 xl:grid-cols-4">
        {getCampaignScenarioOptions().map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={`rounded-xl px-2 py-2 text-[0.62rem] font-semibold transition ${
              activeScenarioId === option.id
                ? "border border-cyan-200/18 bg-cyan-200/[0.10] text-cyan-100"
                : "border border-transparent text-slate-500 hover:bg-white/[0.035] hover:text-slate-300"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ScenarioAssumptionCard({
  scenario,
}: {
  scenario?: CampaignScenario | null;
}) {
  return (
    <div className="mt-3 rounded-2xl border border-white/[0.06] bg-white/[0.025] px-3 py-3">
      <p className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Suposiciones del escenario</p>
      <p className="mt-2 text-xs leading-5 text-slate-400">
        {scenario?.assumptions ?? "Escenario de prototipo pendiente de carga."}
      </p>
    </div>
  );
}

function CampaignBuilderIntroBox() {
  return (
    <div className="mt-4 rounded-2xl border border-cyan-200/10 bg-cyan-200/[0.045] px-3 py-3">
      <p className="text-xs leading-5 text-slate-300">
        El Constructor de Campaña muestra los índices más relevantes a considerar de cara a una campaña electoral:
        cuáles son tus objetivos y cómo llegar a ellos de forma efectiva.
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-400">
        En base al trabajo previo con la información histórica, estructuras de comunicación y reciente actualidad política,
        SocTrace ha proyectado varios posibles escenarios para los comicios de mayo de 2027.
      </p>
    </div>
  );
}

function ForecastedPlenaryStructure({
  partyVoteShares,
  validation,
}: {
  partyVoteShares: PartySharePoint[];
  validation?: CampaignScenario["dhondtValidation"] | null;
}) {
  const seats = calculateDHondtSeats({
    parties: partyVoteShares.map((item) => ({
      party: normalizePartyName(item.party) || item.party,
      percentage: toFiniteNumber(item.percentage) ?? 0,
    })),
    totalSeats: 25,
    thresholdPct: 5,
  });

  if (seats.length === 0) {
    return (
      <div className="mt-4 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Proyección del pleno
        </p>
        <p className="mt-3 text-sm text-slate-400">No hay porcentaje de voto previsto disponible.</p>
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Proyección del pleno
        </p>
        <span className="rounded-full border border-white/[0.08] bg-white/[0.035] px-2 py-0.5 text-[0.62rem] font-semibold text-slate-400">
          {validation?.matchesTarget ? "D'Hondt validado" : "Revisar D'Hondt"}
        </span>
      </div>
      <div className="mt-4 grid gap-3">
        {seats.map((item) => {
          const color = rgbaToCss(getPartyColor(item.party));
          return (
            <div key={item.party} className="flex flex-col gap-1.5 border-t border-white/[0.045] pt-3 first:border-t-0 first:pt-0">
              <div className="flex flex-wrap items-center gap-1.5">
                {Array.from({ length: item.seats }).map((_, index) => (
                  <UserRound
                    key={`${item.party}-${index}`}
                    className="h-4 w-4"
                    style={{ color }}
                    strokeWidth={2.1}
                    aria-hidden="true"
                  />
                ))}
                <p className="ml-1 text-xs font-semibold text-slate-200">
                  {item.seats} concejales · {item.party}
                </p>
              </div>
              <p className="text-[0.62rem] font-semibold tabular-nums text-slate-500">
                {item.percentage.toFixed(1)}% de voto estimado válido
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ForecastVoteShareCard({
  partyVoteShares,
}: {
  partyVoteShares: PartySharePoint[];
}) {
  return (
    <div className="mt-4 rounded-3xl border border-white/[0.06] bg-[#0b1220]/75 p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Porcentaje estimado de voto
      </p>
      <div className="mt-3 space-y-2">
        {partyVoteShares.map((item) => {
          const color = rgbaToCss(getPartyColor(item.party));
          return (
            <div key={item.party} className="flex items-center justify-between gap-3 text-xs">
              <span className="flex min-w-0 items-center gap-2 text-slate-300">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: color }} />
                <span className="truncate">{item.party}</span>
              </span>
              <span className="shrink-0 font-semibold tabular-nums text-slate-100">{item.percentage.toFixed(1)}%</span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-[0.66rem] leading-4 text-slate-500">
        Ajuste manual de prototipo basado en encuestas tradicionales y datos propios.
      </p>
    </div>
  );
}

function partyVoteLeader(voteShare: Record<string, number>) {
  const [party, percentage] = Object.entries(voteShare).sort((a, b) => b[1] - a[1])[0] ?? [];
  return party ? { party, percentage } : null;
}

function averageScenarioIndicator(
  scenario: CampaignScenario,
  indicator: keyof NonNullable<CampaignScenario["sectionProjections"][number]["indicators"]>,
) {
  const values = scenario.sectionProjections
    .map((section) => section.indicators?.[indicator])
    .filter((value): value is number => value != null && Number.isFinite(value));
  return values.length ? values.reduce((total, value) => total + value, 0) / values.length : null;
}

function CampaignBuilderPanel({
  title,
  subtitle,
  collection,
  selectedSection,
  metric,
  onMetricChange,
  onRoot,
}: {
  title: string;
  subtitle: string;
  collection?: SectionFeatureCollection | null;
  selectedSection?: SectionFeatureProperties | null;
  metric: CampaignForecastMetricKey;
  onMetricChange: (metric: CampaignForecastMetricKey) => void;
  onRoot: () => void;
}) {
  const [activeScenarioId, setActiveScenarioId] = useState<ElectoralScenarioId>("structural");
  const scenarios = useMemo(() => buildCampaignScenarios(collection), [collection]);
  const activeScenario = scenarios.find((scenario) => scenario.id === activeScenarioId) ?? scenarios[0];
  const baseProfile = selectedSection ?? buildMunicipalityCampaignProfile(collection);
  const selectedSectionProjection = selectedSection
    ? activeScenario?.sectionProjections.find((projection) => projection.sectionId === selectedSection.section_id)
    : null;
  const profile = baseProfile
    ? {
        ...baseProfile,
        ...(selectedSection
          ? { forecast_interpretation: getSectionScenarioInterpretation(activeScenarioId, baseProfile) }
          : activeScenario
            ? {
                projected_leading_party: partyVoteLeader(activeScenario.voteShare)?.party,
                projected_vote_share: partyVoteLeader(activeScenario.voteShare)?.percentage,
                volatility: averageScenarioIndicator(activeScenario, "volatility"),
                forecast_confidence: averageScenarioIndicator(activeScenario, "confidence"),
                contextual_uncertainty: 100 - (averageScenarioIndicator(activeScenario, "confidence") ?? 0),
                forecast_swing_territory_count: activeScenario.sectionProjections.filter((section) => (section.indicators?.swing ?? 0) >= 58).length,
                forecast_interpretation: activeScenario.description,
              }
            : {}),
        has_contextual_adjustments: true,
      }
    : null;
  const value = getCampaignForecastMetricValue(profile, metric);
  const partyVoteShares = activeScenario
    ? Object.entries(activeScenario.voteShare)
        .map(([party, percentage]) => ({ party, percentage }))
        .sort((a, b) => b.percentage - a.percentage)
    : aggregateElectionCollection(collection);
  const isMunicipality = !selectedSection;

  if (!profile) {
    return (
      <Panel className="flex h-full items-center justify-center p-6 text-center text-sm text-slate-400">
        Cargando señales de previsión electoral del Constructor de Campaña.
      </Panel>
    );
  }

  return (
    <Panel className="flex h-full min-h-0 flex-col overflow-y-auto p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Previsión electoral
          </p>
          <h2 className="font-manrope mt-2 truncate text-left text-[1.7rem] font-semibold tracking-[-0.04em] text-white">
            {title}
          </h2>
          <p className="font-manrope mt-1.5 text-left text-sm font-medium text-slate-400">{subtitle}</p>
          <p className="mt-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-cyan-200/70">
            Constructor de Campaña
          </p>
        </div>
        <button
          type="button"
          onClick={onRoot}
          className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100 transition hover:border-cyan-200/30 hover:bg-cyan-200/[0.13] hover:text-white"
        >
          Inicio
        </button>
      </div>
      <CampaignBuilderIntroBox />
      <ScenarioSelector activeScenarioId={activeScenarioId} onChange={setActiveScenarioId} />
      <ScenarioAssumptionCard scenario={activeScenario} />
      <ForecastOutlookCard profile={profile} isMunicipality={isMunicipality} scenario={activeScenario} />
      {isMunicipality ? <ForecastedPlenaryStructure partyVoteShares={partyVoteShares} validation={activeScenario?.dhondtValidation} /> : null}
      <ForecastVoteShareCard partyVoteShares={selectedSectionProjection ? Object.entries(selectedSectionProjection.parties).map(([party, percentage]) => ({ party, percentage })) : partyVoteShares} />
      <ElectoralForecastRing metric={metric} value={value} />
      <ForecastVariableSelector activeMetric={metric} onMetricChange={onMetricChange} />
      <div className="mt-4 grid grid-cols-2 gap-2">
        {campaignForecastMetricOrder.map((item) => {
          const config = CAMPAIGN_FORECAST_METRICS[item];
          const itemValue = getCampaignForecastMetricValue(profile, item);
          return (
            <div key={item} className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5">
              <p className="text-[0.64rem] font-semibold uppercase tracking-[0.12em] text-slate-500">{config.shortTitle}</p>
              <p className="mt-1 text-sm font-semibold tabular-nums text-slate-100">{formatForecastPercent(itemValue)}</p>
            </div>
          );
        })}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5">
          <p className="text-[0.64rem] font-semibold uppercase tracking-[0.12em] text-slate-500">Previsión de participación</p>
          <p className="mt-1 text-sm font-semibold tabular-nums text-slate-100">{formatForecastPercent(toFiniteNumber(profile.turnout_forecast))}</p>
        </div>
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5">
          <p className="text-[0.64rem] font-semibold uppercase tracking-[0.12em] text-slate-500">{isMunicipality ? "Territorios de cambio" : "Nivel de confianza"}</p>
          <p className="mt-1 text-sm font-semibold tabular-nums capitalize text-slate-100">
            {isMunicipality ? formatCompactNumber(toFiniteNumber(profile.forecast_swing_territory_count)) : profile.forecast_confidence_level ?? "N/A"}
          </p>
        </div>
        {isMunicipality ? (
          <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5">
            <p className="text-[0.64rem] font-semibold uppercase tracking-[0.12em] text-slate-500">Secciones estratégicas</p>
            <p className="mt-1 text-sm font-semibold tabular-nums capitalize text-slate-100">
              {formatCompactNumber(activeScenario?.sectionProjections.filter((section) => (section.indicators?.swing ?? 0) >= 58 || (section.indicators?.localist ?? 0) >= 58).length ?? null)}
            </p>
          </div>
        ) : null}
      </div>
      {selectedSection && selectedSection.contextual_drivers?.length ? (
        <div className="mt-3 rounded-2xl border border-white/[0.06] bg-white/[0.025] px-3 py-3">
          <p className="text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Factores contextuales</p>
          <div className="mt-2 space-y-1.5">
            {selectedSection.contextual_drivers.slice(0, 4).map((driver) => (
              <div key={driver.prior} className="flex items-center justify-between gap-3 text-xs">
                <span className="truncate text-slate-400">{driver.prior.replace(/_/g, " ")}</span>
                <span className="shrink-0 font-semibold tabular-nums text-slate-200">{formatForecastPercent(toFiniteNumber(driver.value))}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <p className="mt-3 text-[0.68rem] leading-4 text-slate-500">
        Estimación estructural 2027 · datos internos · calibración Oraculum pendiente
      </p>
    </Panel>
  );
}

export function getPopulationYAxisDomain(values: number[]): [number, number] {
  if (values.length === 0) {
    return [0, 100];
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const padding = range * 0.15;
  const step = range > 2500 ? 500 : 100;

  const lower = Math.floor((min - padding) / step) * step;
  const upper = Math.ceil((max + padding) / step) * step;

  if (lower === upper) {
    return [Math.max(0, lower - step), upper + step];
  }

  return [Math.max(0, lower), upper];
}

function buildSmoothPath(points: ChartPoint[]) {
  if (points.length === 0) {
    return "";
  }

  if (points.length === 1) {
    return `M ${points[0].x} ${points[0].y}`;
  }

  return points.reduce((path, point, index) => {
    if (index === 0) {
      return `M ${point.x} ${point.y}`;
    }

    const previous = points[index - 1];
    const controlX = (previous.x + point.x) / 2;
    return `${path} C ${controlX} ${previous.y}, ${controlX} ${point.y}, ${point.x} ${point.y}`;
  }, "");
}

function getDrawablePopulationPoints(points: ChartPoint[]) {
  const firstValidIndex = points.findIndex((point) => point.value != null);

  if (firstValidIndex === -1) {
    return [];
  }

  return points.slice(firstValidIndex).filter((point) => point.value != null);
}

function PopulationEvolutionChart({
  points,
  isLoading,
  activeYear,
}: {
  points: PopulationPoint[];
  isLoading: boolean;
  activeYear?: string;
}) {
  const [hoveredPoint, setHoveredPoint] = useState<ChartPoint | null>(null);
  const chart = useMemo(() => {
    const width = 330;
    const height = 188;
    const padding = { top: 18, right: 16, bottom: 34, left: 48 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const values = points
      .map((point) => point.value)
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
    const [minY, maxY] = getPopulationYAxisDomain(values);
    const yRange = Math.max(maxY - minY, 1);
    const xStep = points.length > 1 ? plotWidth / (points.length - 1) : 0;
    const chartPoints = points.map((point, index) => ({
      ...point,
      x: padding.left + index * xStep,
      y:
        point.value == null
          ? 0
          : padding.top + ((maxY - point.value) / yRange) * plotHeight,
    }));
    const visiblePoints = getDrawablePopulationPoints(chartPoints);
    const ticks = [maxY, Math.round((minY + maxY) / 2), minY];

    return {
      width,
      height,
      padding,
      plotWidth,
      plotHeight,
      minY,
      maxY,
      ticks,
      chartPoints,
      visiblePoints,
      path: buildSmoothPath(visiblePoints),
    };
  }, [points]);

  if (chart.visiblePoints.length === 0) {
    return (
      <div className="mt-4 flex h-44 items-center justify-center rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 text-sm text-slate-500">
        {isLoading ? "Loading population series..." : "No population series available."}
      </div>
    );
  }

  return (
    <div className="relative mt-4 rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 px-3 py-3">
      <svg
        className="h-48 w-full overflow-visible"
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        role="img"
        aria-label="Evolución de población de 2021 a 2025"
      >
        <defs>
          <linearGradient id="populationLineGradient" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
          <linearGradient id="populationAreaGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.20" />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
          </linearGradient>
        </defs>

        {chart.ticks.map((tick) => {
          const y =
            chart.padding.top +
            ((chart.maxY - tick) / Math.max(chart.maxY - chart.minY, 1)) * chart.plotHeight;
          return (
            <g key={tick}>
              <line
                x1={chart.padding.left}
                x2={chart.padding.left + chart.plotWidth}
                y1={y}
                y2={y}
                stroke="rgba(148,163,184,0.13)"
                strokeWidth="1"
              />
              <text
                x={chart.padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="fill-slate-500 text-[10px] tabular-nums"
              >
                {tick.toLocaleString("es-ES")}
              </text>
            </g>
          );
        })}

        {chart.visiblePoints.length > 1 ? (
          <path
            d={`${chart.path} L ${chart.visiblePoints[chart.visiblePoints.length - 1].x} ${
              chart.padding.top + chart.plotHeight
            } L ${chart.visiblePoints[0].x} ${chart.padding.top + chart.plotHeight} Z`}
            fill="url(#populationAreaGradient)"
          />
        ) : null}

        <path
          d={chart.path}
          fill="none"
          stroke="url(#populationLineGradient)"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3"
        />

        {chart.chartPoints.map((point) => {
          const isActive = point.year === activeYear;
          return (
          <g key={point.year}>
            <text
              x={point.x}
              y={chart.height - 9}
              textAnchor="middle"
              className="fill-slate-500 text-[10px] tabular-nums"
            >
              {point.year}
            </text>
            {point.value != null ? (
              <circle
                cx={point.x}
                cy={point.y}
                r={isActive ? 6 : 4}
                className="cursor-pointer transition"
                fill={isActive ? "#67e8f9" : "#0b1220"}
                stroke={isActive ? "#e0f2fe" : "#a5f3fc"}
                strokeWidth={isActive ? 2.5 : 2}
                onMouseEnter={() => setHoveredPoint(point)}
                onMouseLeave={() => setHoveredPoint(null)}
                onFocus={() => setHoveredPoint(point)}
                onBlur={() => setHoveredPoint(null)}
                tabIndex={0}
              >
                <title>
                  {point.year}: {point.value.toLocaleString("es-ES")} inhabitants
                </title>
              </circle>
            ) : null}
          </g>
          );
        })}
      </svg>

      {hoveredPoint?.value != null ? (
        <div
          className="pointer-events-none absolute rounded-xl border border-cyan-200/20 bg-[#08111f]/95 px-3 py-2 text-xs shadow-[0_14px_34px_rgba(0,0,0,0.42)]"
          style={{
            left: `calc(${(hoveredPoint.x / chart.width) * 100}% - 2.8rem)`,
            top: `calc(${(hoveredPoint.y / chart.height) * 100}% - 1.9rem)`,
          }}
        >
          <p className="font-semibold text-slate-100">{hoveredPoint.value.toLocaleString("es-ES")}</p>
          <p className="mt-0.5 text-slate-500">{hoveredPoint.year}</p>
        </div>
      ) : null}
    </div>
  );
}

function getCohortPopulation(
  definition: AgeCohortDefinition,
  detail?: SectionDetail,
  section?: SectionFeatureProperties,
) {
  const detailValue = detail?.demography[definition.populationField];
  const fallbackValue = definition.featureField ? section?.[definition.featureField] : undefined;
  const value = typeof detailValue === "number" ? detailValue : fallbackValue;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function buildAgeCohorts(detail?: SectionDetail, section?: SectionFeatureProperties): AgeCohortPoint[] {
  return AGE_COHORTS.map((definition) => ({
    cohort: definition.cohort,
    population: getCohortPopulation(definition, detail, section) ?? 0,
  }));
}

function buildAgeGenderPyramidRows({
  cohorts,
  menTotal,
  womenTotal,
}: {
  cohorts: AgeCohortPoint[];
  menTotal?: number | null;
  womenTotal?: number | null;
}): AgeGenderPyramidRow[] {
  const genderTotal = (menTotal ?? 0) + (womenTotal ?? 0);
  const menShare = genderTotal > 0 ? (menTotal ?? 0) / genderTotal : 0.49;
  const womenShare = genderTotal > 0 ? (womenTotal ?? 0) / genderTotal : 0.51;

  return cohorts.map((cohort) => ({
    cohort: cohort.cohort,
    women: Math.round(cohort.population * womenShare),
    men: Math.round(cohort.population * menShare),
  }));
}

function getDominantCohort(cohorts: AgeCohortPoint[]) {
  return [...cohorts].sort((a, b) => b.population - a.population)[0]?.cohort ?? null;
}

function AgeStructureInsightCard({ insight }: { insight: string }) {
  return (
    <div className="flex h-full min-h-[220px] flex-col justify-between rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-4">
      <div>
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Key Insight
        </p>
        <p className="mt-4 text-xs font-medium leading-5 text-slate-300">{insight}</p>
      </div>
      <div className="mt-5 rounded-2xl border border-cyan-200/10 bg-cyan-200/[0.045] px-3 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-cyan-100">
        Age structure
      </div>
    </div>
  );
}

function AgeStructureStatCard({
  value,
  label,
  tone,
}: {
  value: string;
  label: "Median Age" | "Senior people";
  tone: "green" | "amber";
}) {
  const isGreen = tone === "green";
  const valueClass = isGreen ? "text-emerald-300" : "text-amber-300";
  const borderClass = isGreen
    ? "border-emerald-300/16 bg-emerald-300/[0.055] shadow-[0_0_34px_rgba(52,211,153,0.055)]"
    : "border-amber-300/16 bg-amber-300/[0.055] shadow-[0_0_34px_rgba(251,191,36,0.055)]";
  const iconClass = isGreen ? "text-emerald-200/80" : "text-amber-200/80";

  return (
    <div className={`flex min-h-[5.15rem] items-center justify-between rounded-2xl border px-4 py-3 ${borderClass}`}>
      <div className="min-w-0">
        <p className={`text-[1.65rem] font-semibold leading-none tracking-[-0.04em] tabular-nums ${valueClass}`}>
          {value}
        </p>
        <p className="mt-2 text-xs font-medium text-slate-400">{label}</p>
      </div>
      {isGreen ? (
        <div className={`flex shrink-0 items-center gap-1.5 ${iconClass}`} aria-hidden="true">
          <UsersRound className="h-8 w-8" strokeWidth={1.7} />
          <Scale className="h-4 w-4" strokeWidth={1.8} />
        </div>
      ) : (
        <div className={`flex shrink-0 items-center gap-1.5 ${iconClass}`} aria-hidden="true">
          <Accessibility className="h-9 w-9" strokeWidth={1.65} />
        </div>
      )}
    </div>
  );
}

function AgeStructureTopStats({
  averageAge,
  over65Pct,
}: {
  averageAge?: number | null;
  over65Pct?: number | null;
}) {
  return (
    <div className="mt-4 grid grid-cols-2 gap-3">
      <AgeStructureStatCard
        value={averageAge != null ? `${averageAge.toFixed(1)}` : "--"}
        label="Median Age"
        tone="green"
      />
      <AgeStructureStatCard
        value={over65Pct != null ? `${(over65Pct * 100).toFixed(1)}%` : "--"}
        label="Senior people"
        tone="amber"
      />
    </div>
  );
}

function AgeStructureKpiGrid({
  items,
}: {
  items: { label: string; value: string }[];
}) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 px-4 py-3">
          <p className="text-xs text-slate-500">{item.label}</p>
          <p className="mt-1 text-base font-semibold tabular-nums text-white">{item.value}</p>
        </div>
      ))}
    </div>
  );
}

function getIncomeSourceValue(
  source: IncomeSourceKey,
  detail?: SectionDetail,
  section?: SectionFeatureProperties,
) {
  const detailValue = detail?.income?.[source];
  const fallbackValue = section?.[source];
  const value = typeof detailValue === "number" ? detailValue : fallbackValue;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function AgeCohortBarChart({
  cohorts,
  isLoading,
}: {
  cohorts: AgeCohortPoint[];
  isLoading: boolean;
}) {
  const maxValue = Math.max(...cohorts.map((item) => item.population), 0);

  if (maxValue === 0) {
    return (
      <div className="mt-4 flex h-40 items-center justify-center rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 text-sm text-slate-500">
        {isLoading ? "Loading age cohorts..." : "No age cohort data available."}
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-3">
      <div className="flex h-40 items-end gap-2">
        {cohorts.map((item) => {
          const definition = AGE_COHORTS.find((cohort) => cohort.cohort === item.cohort);
          const height = Math.max(8, (item.population / maxValue) * 116);

          return (
            <div key={item.cohort} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="flex h-6 items-end text-[10px] font-semibold tabular-nums text-slate-300">
                {item.population.toLocaleString("es-ES")}
              </div>
              <div
                className="w-full max-w-10 rounded-t-xl border border-white/10 shadow-[0_0_18px_rgba(34,211,238,0.08)]"
                style={{
                  height,
                  background: `linear-gradient(180deg, ${definition?.color ?? "#67e8f9"}, rgba(15,23,42,0.72))`,
                }}
                title={`${item.cohort}: ${item.population.toLocaleString("es-ES")} inhabitants`}
              />
              <span className="h-5 text-center text-[10px] font-medium text-slate-500">
                {item.cohort}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AgeCohortEvolutionChart({
  points,
  activeYear,
  isLoading,
}: {
  points: AgeCohortYearPoint[];
  activeYear: string;
  isLoading: boolean;
}) {
  const [hoveredPoint, setHoveredPoint] = useState<AgeSeriesPoint | null>(null);
  const chart = useMemo(() => {
    const width = 330;
    const height = 210;
    const padding = { top: 20, right: 18, bottom: 38, left: 48 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const values = points
      .map((point) => point.population)
      .filter((value) => Number.isFinite(value));
    const [, maxY] = getPopulationYAxisDomain(values);
    const minY = 0;
    const yRange = Math.max(maxY - minY, 1);
    const xStep = ageStructureYears.length > 1 ? plotWidth / (ageStructureYears.length - 1) : 0;
    const yearIndex = Object.fromEntries(ageStructureYears.map((year, index) => [year, index]));
    const series = AGE_COHORTS.map((definition) => {
      const seriesPoints = ageStructureYears
        .map((year) => {
          const point = points.find(
            (item) => item.year === year && item.cohort === definition.cohort,
          );

          if (!point) {
            return null;
          }

          return {
            ...point,
            x: padding.left + yearIndex[year] * xStep,
            y: padding.top + ((maxY - point.population) / yRange) * plotHeight,
          };
        })
        .filter((point): point is AgeSeriesPoint => Boolean(point));

      return {
        ...definition,
        points: seriesPoints,
        path: buildSmoothPath(seriesPoints.map((point) => ({ ...point, value: point.population }))),
      };
    });
    const ticks = [maxY, Math.round(maxY / 2), 0];

    return { width, height, padding, plotWidth, plotHeight, maxY, ticks, series };
  }, [points]);

  const hasSeries = chart.series.some((series) => series.points.length > 0);

  if (!hasSeries) {
    return (
      <div className="mt-4 flex h-48 items-center justify-center rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 text-sm text-slate-500">
        {isLoading ? "Loading cohort evolution..." : "No cohort evolution available."}
      </div>
    );
  }

  return (
    <div className="relative mt-4 rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 px-3 py-3">
      <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1">
        {AGE_COHORTS.map((cohort) => (
          <span key={cohort.cohort} className="flex items-center gap-1.5 text-[10px] text-slate-400">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cohort.color }} />
            {cohort.cohort}
          </span>
        ))}
      </div>
      <svg
        className="h-52 w-full overflow-visible"
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        role="img"
        aria-label="Age cohort evolution from 2021 to 2025"
      >
        {chart.ticks.map((tick) => {
          const y =
            chart.padding.top +
            ((chart.maxY - tick) / Math.max(chart.maxY, 1)) * chart.plotHeight;
          return (
            <g key={tick}>
              <line
                x1={chart.padding.left}
                x2={chart.padding.left + chart.plotWidth}
                y1={y}
                y2={y}
                stroke="rgba(148,163,184,0.13)"
                strokeWidth="1"
              />
              <text
                x={chart.padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="fill-slate-500 text-[10px] tabular-nums"
              >
                {tick.toLocaleString("es-ES")}
              </text>
            </g>
          );
        })}

        {chart.series.map((series) =>
          series.points.length > 0 ? (
            <g key={series.cohort}>
              <path
                d={series.path}
                fill="none"
                stroke={series.color}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.4"
                opacity="0.9"
              />
              {series.points.map((point) => {
                const isActive = point.year === activeYear;
                return (
                  <circle
                    key={`${point.cohort}-${point.year}`}
                    cx={point.x}
                    cy={point.y}
                    r={isActive ? 5 : 3.2}
                    fill={isActive ? series.color : "#0b1220"}
                    stroke={series.color}
                    strokeWidth={isActive ? 2.2 : 1.8}
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredPoint(point)}
                    onMouseLeave={() => setHoveredPoint(null)}
                    onFocus={() => setHoveredPoint(point)}
                    onBlur={() => setHoveredPoint(null)}
                    tabIndex={0}
                  >
                    <title>
                      {point.year} · {point.cohort}: {point.population.toLocaleString("es-ES")}
                    </title>
                  </circle>
                );
              })}
            </g>
          ) : null,
        )}

        {ageStructureYears.map((year, index) => (
          <text
            key={year}
            x={chart.padding.left + index * (chart.plotWidth / (ageStructureYears.length - 1))}
            y={chart.height - 10}
            textAnchor="middle"
            className={`fill-slate-500 text-[10px] tabular-nums ${
              year === activeYear ? "font-semibold" : ""
            }`}
          >
            {year}
          </text>
        ))}
      </svg>

      {hoveredPoint ? (
        <div
          className="pointer-events-none absolute rounded-xl border border-cyan-200/20 bg-[#08111f]/95 px-3 py-2 text-xs shadow-[0_14px_34px_rgba(0,0,0,0.42)]"
          style={{
            left: `calc(${(hoveredPoint.x / chart.width) * 100}% - 3rem)`,
            top: `calc(${(hoveredPoint.y / chart.height) * 100}% + 1.1rem)`,
          }}
        >
          <p className="font-semibold text-slate-100">
            {hoveredPoint.population.toLocaleString("es-ES")}
          </p>
          <p className="mt-0.5 text-slate-500">
            {hoveredPoint.cohort} · {hoveredPoint.year}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function MunicipalityGenderDonut({ summary }: { summary?: MunicipalityPopulationSummary }) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const menPct = summary?.menPct ?? 0;
  const womenPct = summary?.womenPct ?? 0;

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Men / Women
          </p>
          <p className="mt-1 text-lg font-semibold tabular-nums text-white">
            {summary ? `${Math.round(menPct * 100)} / ${Math.round(womenPct * 100)}%` : "--"}
          </p>
        </div>
        <svg className="h-24 w-24 shrink-0" viewBox="0 0 96 96" role="img" aria-label="Men and women share">
          <circle cx="48" cy="48" r={radius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="12" />
          {summary ? (
            <>
              <circle
                cx="48"
                cy="48"
                r={radius}
                fill="none"
                stroke="#67e8f9"
                strokeLinecap="round"
                strokeWidth="12"
                strokeDasharray={`${menPct * circumference} ${circumference}`}
                transform="rotate(-90 48 48)"
              />
              <circle
                cx="48"
                cy="48"
                r={radius}
                fill="none"
                stroke="#c4b5fd"
                strokeLinecap="round"
                strokeWidth="12"
                strokeDasharray={`${womenPct * circumference} ${circumference}`}
                strokeDashoffset={-menPct * circumference}
                transform="rotate(-90 48 48)"
              />
            </>
          ) : null}
          <circle cx="48" cy="48" r="22" fill="#0b1220" />
        </svg>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
        <span className="flex items-center gap-1.5 text-slate-400">
          <span className="h-2 w-2 rounded-full bg-cyan-300" />
          Men
        </span>
        <span className="flex items-center gap-1.5 text-slate-400">
          <span className="h-2 w-2 rounded-full bg-violet-300" />
          Women
        </span>
      </div>
    </div>
  );
}

function MunicipalityDensityBar({ summary }: { summary?: MunicipalityPopulationSummary }) {
  const spainAverage = 98;
  const density = summary?.density ?? null;
  const maxValue = Math.max(spainAverage * 1.35, density != null ? density * 1.18 : 0);
  const height = 116;
  const padding = { top: 14, right: 18, bottom: 24, left: 42 };
  const plotHeight = height - padding.top - padding.bottom;
  const densityY =
    density == null ? padding.top + plotHeight : padding.top + ((maxValue - density) / maxValue) * plotHeight;
  const averageY = padding.top + ((maxValue - spainAverage) / maxValue) * plotHeight;
  const barHeight = padding.top + plotHeight - densityY;

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Density
          </p>
          <p className="mt-1 text-lg font-semibold tabular-nums text-white">
            {density != null ? `${Math.round(density).toLocaleString("es-ES")} / km²` : "--"}
          </p>
        </div>
      </div>
      <svg className="mt-1 h-32 w-full overflow-visible" viewBox={`0 0 180 ${height}`} role="img" aria-label="Municipal population density">
        <line x1={padding.left} x2={166} y1={averageY} y2={averageY} stroke="rgba(226,232,240,0.38)" strokeDasharray="3 4" />
        <text x={166} y={averageY - 5} textAnchor="end" className="fill-slate-500 text-[9px]">
          Spain avg · 98/km²
        </text>
        <rect x="78" y={densityY} width="34" height={Math.max(barHeight, density == null ? 0 : 2)} rx="7" fill="#22d3ee" opacity="0.78" />
        <line x1={padding.left} x2={166} y1={padding.top + plotHeight} y2={padding.top + plotHeight} stroke="rgba(148,163,184,0.16)" />
        <text x="95" y={height - 5} textAnchor="middle" className="fill-slate-500 text-[10px]">
          Mijas
        </text>
      </svg>
    </div>
  );
}

function MunicipalityPopulationOverview({
  summaries,
  selectedYear,
  isLoading,
}: {
  summaries: MunicipalityPopulationSummary[];
  selectedYear: string;
  isLoading: boolean;
}) {
  const activeSummary = summaries.find((summary) => String(summary.year) === selectedYear);
  const points = populationYears.map((year) => ({
    year,
    value: summaries.find((summary) => String(summary.year) === year)?.populationTotal ?? null,
  }));

  return (
    <Panel className="flex h-full flex-col p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Evolution
          </p>
          <h2 className="font-manrope mt-2 text-left text-[1.35rem] font-semibold text-white">
            Mijas
          </h2>
          <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
            Municipality overview
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
          {selectedYear}
        </span>
      </div>

      <div className="mt-4 rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
        <p className="text-xs text-slate-500">Total population {selectedYear}</p>
        <p className="mt-1 text-3xl font-semibold tabular-nums text-white">
          {activeSummary ? activeSummary.populationTotal.toLocaleString("es-ES") : "--"}
        </p>
      </div>

      <PopulationEvolutionChart points={points} isLoading={isLoading} activeYear={selectedYear} />

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <MunicipalityGenderDonut summary={activeSummary} />
        <MunicipalityDensityBar summary={activeSummary} />
      </div>
    </Panel>
  );
}

function MunicipalityAgeStructureOverview({
  summaries,
  selectedYear,
  isLoading,
}: {
  summaries: MunicipalityAgeStructureSummary[];
  selectedYear: string;
  isLoading: boolean;
}) {
  const activeSummary = summaries.find((summary) => String(summary.year) === selectedYear);
  const points = ageStructureYears.flatMap((year) => {
    const summary = summaries.find((item) => String(item.year) === year);

    return summary
      ? summary.cohorts.map((cohort) => ({
          year,
          cohort: cohort.cohort,
          population: cohort.population,
        }))
      : [];
  });
  const pyramidRows = buildAgeGenderPyramidRows({
    cohorts: activeSummary?.cohorts ?? [],
    menTotal: activeSummary?.populationMale,
    womenTotal: activeSummary?.populationFemale,
  });
  const dominantCohort = getDominantCohort(activeSummary?.cohorts ?? []);
  const genderTotal = (activeSummary?.populationMale ?? 0) + (activeSummary?.populationFemale ?? 0);
  const insight = generateAgeStructureInsight({
    totalPopulation: activeSummary?.totalPopulation,
    averageAge: activeSummary?.averageAge,
    pct65Plus: activeSummary?.over65Pct,
    pctUnder30: activeSummary?.under30Pct,
    dominantCohort,
    genderBalance: genderTotal > 0 ? (activeSummary?.populationFemale ?? 0) / genderTotal : null,
  });
  const lowerKpiItems = [
    {
      label: "Foreign-born",
      value: activeSummary?.foreignBornPct != null ? `${(activeSummary.foreignBornPct * 100).toFixed(1)}%` : "--",
    },
  ];

  return (
    <Panel className="flex h-full flex-col p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Evolution
          </p>
          <h2 className="font-manrope mt-2 text-left text-[1.35rem] font-semibold text-white">
            Mijas
          </h2>
          <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
            Municipality overview
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
          {selectedYear}
        </span>
      </div>

      <AgeStructureTopStats
        averageAge={activeSummary?.averageAge}
        over65Pct={activeSummary?.over65Pct}
      />

      <AgeCohortBarChart
        cohorts={activeSummary?.cohorts ?? []}
        isLoading={isLoading && !activeSummary}
      />

      <div className="mt-5">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Cohort evolution
        </p>
        <AgeCohortEvolutionChart
          points={points}
          activeYear={selectedYear}
          isLoading={isLoading && summaries.length === 0}
        />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.85fr)]">
        <AgeGenderPyramidChart
          rows={pyramidRows}
          estimated
          isLoading={isLoading && !activeSummary}
        />
        <AgeStructureInsightCard insight={insight} />
      </div>

      <AgeStructureKpiGrid items={lowerKpiItems} />
    </Panel>
  );
}

function MunicipalityIncomeOverview({
  summaries,
  selectedYear,
  isLoading,
}: {
  summaries: MunicipalityIncomeSummary[];
  selectedYear: string;
  isLoading: boolean;
}) {
  const activeSummary = summaries.find((summary) => String(summary.year) === selectedYear);
  const incomeBarPoints = incomeYears.map((year) => {
    const summary = summaries.find((item) => String(item.year) === year);

    return {
      year,
      individualIncome: summary?.individualIncome ?? null,
      householdIncome: summary?.householdIncome ?? null,
    };
  });
  const sourcePoints = incomeYears.flatMap((year) => {
    const summary = summaries.find((item) => String(item.year) === year);

    return summary
      ? INCOME_SOURCES.flatMap((source) => {
          const value = summary.sources[source.key];
          return typeof value === "number" && Number.isFinite(value)
            ? [{ year, source: source.key, value }]
            : [];
        })
      : [];
  });

  return (
    <Panel className="flex h-full flex-col p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Evolution
          </p>
          <h2 className="font-manrope mt-2 text-left text-[1.35rem] font-semibold text-white">
            Mijas
          </h2>
          <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
            Municipality overview
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
          {selectedYear}
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
          <p className="text-xs text-slate-500">Net individual income {selectedYear}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-white">
            {formatEuro(activeSummary?.individualIncome)}
          </p>
        </div>
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3">
          <p className="text-xs text-slate-500">Net household income {selectedYear}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-white">
            {formatEuro(activeSummary?.householdIncome)}
          </p>
        </div>
      </div>

      <IncomeStackedBarChart
        points={incomeBarPoints}
        activeYear={selectedYear}
        isLoading={isLoading && summaries.length === 0}
      />

      <div className="mt-5">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Income source evolution
        </p>
        <IncomeSourcesLineChart
          points={sourcePoints}
          activeYear={selectedYear}
          isLoading={isLoading && summaries.length === 0}
        />
      </div>

      <p className="mt-3 text-xs leading-5 text-slate-500">
        Municipal income values use section means until a complete weighting contract is added to the API.
      </p>
    </Panel>
  );
}

function IncomeStackedBarChart({
  points,
  activeYear,
  isLoading,
}: {
  points: IncomeBarPoint[];
  activeYear: string;
  isLoading: boolean;
}) {
  const values = points.flatMap((point) => [
    point.individualIncome ?? 0,
    point.householdIncome ?? 0,
  ]);
  const maxStack = Math.max(
    ...points.map((point) => (point.individualIncome ?? 0) + (point.householdIncome ?? 0)),
    0,
  );

  if (Math.max(...values, 0) === 0) {
    return (
      <div className="mt-4 flex h-48 items-center justify-center rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 text-sm text-slate-500">
        {isLoading ? "Loading income series..." : "No income series available."}
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 p-3">
      <div className="mb-3 flex flex-wrap gap-3 text-[10px] text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-cyan-300" />
          Individual income
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-violet-300" />
          Household income
        </span>
      </div>
      <div className="flex h-48 items-end gap-2">
        {points.map((point) => {
          const individualHeight = ((point.individualIncome ?? 0) / Math.max(maxStack, 1)) * 132;
          const householdHeight = ((point.householdIncome ?? 0) / Math.max(maxStack, 1)) * 132;
          const isActive = point.year === activeYear;

          return (
            <div key={point.year} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="h-8 text-center text-[10px] font-semibold leading-4 tabular-nums text-slate-300">
                <div>{formatEuro(point.householdIncome)}</div>
                <div className="text-slate-500">{formatEuro(point.individualIncome)}</div>
              </div>
              <div
                className={`flex w-full max-w-10 flex-col justify-end overflow-hidden rounded-t-xl border ${
                  isActive ? "border-cyan-200/40" : "border-white/10"
                } bg-white/[0.03]`}
                title={`${point.year}: individual ${formatEuro(point.individualIncome)}, household ${formatEuro(point.householdIncome)}`}
              >
                <div
                  className="bg-violet-300/85"
                  style={{ height: Math.max(householdHeight, point.householdIncome == null ? 0 : 4) }}
                />
                <div
                  className="bg-cyan-300/85"
                  style={{ height: Math.max(individualHeight, point.individualIncome == null ? 0 : 4) }}
                />
              </div>
              <span className={`text-[10px] tabular-nums ${isActive ? "font-semibold text-cyan-100" : "text-slate-500"}`}>
                {point.year}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function IncomeSourcesLineChart({
  points,
  activeYear,
  isLoading,
}: {
  points: IncomeSourcePoint[];
  activeYear: string;
  isLoading: boolean;
}) {
  const [hoveredPoint, setHoveredPoint] = useState<IncomeSourceSeriesPoint | null>(null);
  const chart = useMemo(() => {
    const width = 330;
    const height = 210;
    const padding = { top: 20, right: 18, bottom: 38, left: 42 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const maxY = Math.max(...points.map((point) => point.value), 10);
    const xStep = incomeYears.length > 1 ? plotWidth / (incomeYears.length - 1) : 0;
    const yearIndex = Object.fromEntries(incomeYears.map((year, index) => [year, index]));
    const series = INCOME_SOURCES.map((source) => {
      const seriesPoints = incomeYears
        .map((year) => {
          const point = points.find((item) => item.year === year && item.source === source.key);
          return point
            ? {
                ...point,
                x: padding.left + yearIndex[year] * xStep,
                y: padding.top + ((maxY - point.value) / Math.max(maxY, 1)) * plotHeight,
              }
            : null;
        })
        .filter((point): point is IncomeSourceSeriesPoint => Boolean(point));

      return {
        ...source,
        points: seriesPoints,
        path: buildSmoothPath(seriesPoints.map((point) => ({ ...point, value: point.value }))),
      };
    });
    const ticks = [Math.ceil(maxY), Math.round(maxY / 2), 0];

    return { width, height, padding, plotWidth, plotHeight, maxY, ticks, series };
  }, [points]);

  const hasSeries = chart.series.some((series) => series.points.length > 0);

  if (!hasSeries) {
    return (
      <div className="mt-4 flex h-48 items-center justify-center rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 text-sm text-slate-500">
        {isLoading ? "Loading income sources..." : "No income source series available."}
      </div>
    );
  }

  return (
    <div className="relative mt-4 rounded-2xl border border-white/[0.06] bg-[#0b1220]/70 px-3 py-3">
      <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1">
        {INCOME_SOURCES.map((source) => (
          <span key={source.key} className="flex items-center gap-1.5 text-[10px] text-slate-400">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: source.color }} />
            {source.label}
          </span>
        ))}
      </div>
      <svg className="h-52 w-full overflow-visible" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Income source evolution">
        {chart.ticks.map((tick) => {
          const y = chart.padding.top + ((chart.maxY - tick) / Math.max(chart.maxY, 1)) * chart.plotHeight;
          return (
            <g key={tick}>
              <line x1={chart.padding.left} x2={chart.padding.left + chart.plotWidth} y1={y} y2={y} stroke="rgba(148,163,184,0.13)" />
              <text x={chart.padding.left - 8} y={y + 4} textAnchor="end" className="fill-slate-500 text-[10px] tabular-nums">
                {tick}%
              </text>
            </g>
          );
        })}
        {chart.series.map((series) => (
          <g key={series.key}>
            <path d={series.path} fill="none" stroke={series.color} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.4" opacity="0.9" />
            {series.points.map((point) => {
              const isActive = point.year === activeYear;
              return (
                <circle
                  key={`${point.source}-${point.year}`}
                  cx={point.x}
                  cy={point.y}
                  r={isActive ? 5 : 3.2}
                  fill={isActive ? series.color : "#0b1220"}
                  stroke={series.color}
                  strokeWidth={isActive ? 2.2 : 1.8}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredPoint(point)}
                  onMouseLeave={() => setHoveredPoint(null)}
                  tabIndex={0}
                >
                  <title>{`${series.label} ${point.year}: ${point.value.toFixed(1)}%`}</title>
                </circle>
              );
            })}
          </g>
        ))}
        {incomeYears.map((year, index) => (
          <text key={year} x={chart.padding.left + index * (chart.plotWidth / (incomeYears.length - 1))} y={chart.height - 10} textAnchor="middle" className="fill-slate-500 text-[10px] tabular-nums">
            {year}
          </text>
        ))}
      </svg>
      {hoveredPoint ? (
        <div
          className="pointer-events-none absolute rounded-xl border border-cyan-200/20 bg-[#08111f]/95 px-3 py-2 text-xs shadow-[0_14px_34px_rgba(0,0,0,0.42)]"
          style={{
            left: `calc(${(hoveredPoint.x / chart.width) * 100}% - 3rem)`,
            top: `calc(${(hoveredPoint.y / chart.height) * 100}% + 1.1rem)`,
          }}
        >
          <p className="font-semibold text-slate-100">{hoveredPoint.value.toFixed(1)}%</p>
          <p className="mt-0.5 text-slate-500">{hoveredPoint.year}</p>
        </div>
      ) : null}
    </div>
  );
}

function VoteShareBarChart({ points }: { points: PartySharePoint[] }) {
  const filtered = points.filter((point) => point.percentage > 3).slice(0, 8);
  const maxValue = Math.max(...filtered.map((point) => point.percentage), 1);

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Porcentaje de voto
      </p>
      {filtered.length > 0 ? (
        <div className="mt-3 space-y-3">
          {filtered.map((point) => (
            <div key={point.party}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="min-w-0 truncate font-medium text-slate-300">{point.party}</span>
                <span className="shrink-0 tabular-nums text-slate-100">
                  {point.percentage.toFixed(1)}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-white/[0.06]">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${Math.max(4, (point.percentage / maxValue) * 100)}%`,
                    backgroundColor: rgbaToCss(getPartyColor(point.party)),
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-500">No candidacies above 3% for this scope.</p>
      )}
    </div>
  );
}

function ElectoralEvolutionLineChart({
  contests,
  points,
  activeContestId,
}: {
  contests: ElectionContest[];
  points: ElectoralHistoryPoint[];
  activeContestId: string;
}) {
  const parties = Array.from(new Set(points.map((point) => point.party))).slice(0, 5);
  const width = 360;
  const height = 176;
  const paddingX = 26;
  const paddingY = 22;
  const xForIndex = (index: number) =>
    contests.length <= 1
      ? width / 2
      : paddingX + (index * (width - paddingX * 2)) / (contests.length - 1);
  const yForValue = (value: number) => height - paddingY - (value / 100) * (height - paddingY * 2);

  const series = parties.map((party) => {
    const seriesPoints = contests
      .map((contest, index) => {
        const point = points.find((candidate) => candidate.contestId === contest.id && candidate.party === party);
        return point?.percentage == null
          ? null
          : { x: xForIndex(index), y: yForValue(point.percentage), value: point.percentage, contest };
      })
      .filter((point): point is { x: number; y: number; value: number; contest: ElectionContest } => Boolean(point));

    return {
      party,
      color: rgbaToCss(getPartyColor(party)),
      points: seriesPoints,
      path: buildSmoothPath(seriesPoints.map((point) => ({ year: point.contest.id, value: point.value, x: point.x, y: point.y }))),
    };
  });

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Vote evolution
      </p>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-3 h-44 w-full overflow-visible">
        {[0, 25, 50, 75].map((tick) => (
          <g key={tick}>
            <line
              x1={paddingX}
              x2={width - paddingX}
              y1={yForValue(tick)}
              y2={yForValue(tick)}
              stroke="rgba(255,255,255,0.06)"
            />
            <text x={0} y={yForValue(tick) + 4} fill="#64748b" fontSize="10">
              {tick}%
            </text>
          </g>
        ))}
        {series.map((item) => (
          <g key={item.party}>
            <path d={item.path} fill="none" stroke={item.color} strokeLinecap="round" strokeWidth="2.4" />
            {item.points.map((point) => (
              <circle
                key={`${item.party}-${point.contest.id}`}
                cx={point.x}
                cy={point.y}
                r={point.contest.id === activeContestId ? 4 : 3}
                fill={item.color}
                stroke="rgba(8,13,24,0.92)"
                strokeWidth="2"
              />
            ))}
          </g>
        ))}
        {contests.map((contest, index) => (
          <text
            key={contest.id}
            x={xForIndex(index)}
            y={height - 2}
            textAnchor="middle"
            fill={contest.id === activeContestId ? "#e2e8f0" : "#64748b"}
            fontSize="10"
            fontWeight={contest.id === activeContestId ? 700 : 500}
          >
            {contest.label}
          </text>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-2">
        {series.map((item) => (
          <span key={item.party} className="inline-flex items-center gap-1.5 text-[0.68rem] text-slate-400">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
            {item.party}
          </span>
        ))}
      </div>
    </div>
  );
}

function ParticipationRadial({ participation }: { participation: number | null }) {
  const value = participation == null ? 0 : Math.max(0, Math.min(100, participation));
  const abstention = 100 - value;
  const radius = 38;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
        Participation
      </p>
      <div className="mt-3 flex items-center gap-5">
        <div className="relative h-28 w-28">
          <svg viewBox="0 0 100 100" className="-rotate-90">
            <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="9" />
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="rgba(103,232,249,0.72)"
              strokeLinecap="round"
              strokeWidth="9"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - value / 100)}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-semibold text-white">{value.toFixed(1)}%</span>
            <span className="text-[0.65rem] uppercase tracking-[0.12em] text-slate-500">Turnout</span>
          </div>
        </div>
        <div className="space-y-3 text-sm">
          <div>
            <p className="text-slate-500">Participation</p>
            <p className="font-semibold text-slate-100">{value.toFixed(1)}%</p>
          </div>
          <div>
            <p className="text-slate-500">Abstention</p>
            <p className="font-semibold text-slate-100">{abstention.toFixed(1)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}

type ElectoralMetricPoint = {
  contestId: string;
  label: string;
  value: number | null;
};

type BlocHistoryPoint = {
  contestId: string;
  label: string;
  left: number | null;
  right: number | null;
  regionalOther: number | null;
};

function getElectoralMetric(section: SectionFeatureProperties | null | undefined, metric: "turnout" | "left" | "right" | "regionalOther" | "fragmentation") {
  if (!section) {
    return null;
  }
  if (metric === "turnout") {
    return getTurnout(section);
  }
  if (metric === "left") {
    return toFiniteNumber(section.left_bloc_pct);
  }
  if (metric === "right") {
    return toFiniteNumber(section.right_bloc_pct);
  }
  if (metric === "fragmentation") {
    const value = toFiniteNumber(section.fragmentation_index);
    return value == null ? null : value * 100;
  }

  const national = toFiniteNumber(section.national_vote_pct);
  const local = toFiniteNumber(section.local_vote_pct);
  if (national == null && local == null) {
    const left = toFiniteNumber(section.left_bloc_pct);
    const right = toFiniteNumber(section.right_bloc_pct);
    return left != null || right != null ? Math.max(0, 100 - (left ?? 0) - (right ?? 0)) : null;
  }
  return Math.max(0, 100 - (national ?? 0) - (local ?? 0));
}

function aggregateElectoralMetric(collection: SectionFeatureCollection | undefined, metric: "turnout" | "left" | "right" | "regionalOther" | "fragmentation") {
  const values = (collection?.features ?? [])
    .map((feature) => getElectoralMetric(feature.properties, metric))
    .filter((value): value is number => value != null && Number.isFinite(value));
  return values.length > 0 ? values.reduce((total, value) => total + value, 0) / values.length : null;
}

function ElectoralMetricLineChart({
  title,
  points,
  activeContestId,
}: {
  title: string;
  points: ElectoralMetricPoint[];
  activeContestId: string;
}) {
  const width = 360;
  const height = 132;
  const paddingX = 28;
  const paddingY = 20;
  const validValues = points.map((point) => point.value).filter((value): value is number => value != null);
  const maxValue = Math.max(10, ...validValues);
  const xForIndex = (index: number) =>
    points.length <= 1 ? width / 2 : paddingX + (index * (width - paddingX * 2)) / (points.length - 1);
  const yForValue = (value: number) => height - paddingY - (value / maxValue) * (height - paddingY * 2);
  const drawable = points
    .map((point, index) => point.value == null ? null : { ...point, x: xForIndex(index), y: yForValue(point.value) })
    .filter((point): point is ElectoralMetricPoint & { x: number; y: number; value: number } => Boolean(point));
  const path = buildSmoothPath(drawable.map((point) => ({ year: point.contestId, value: point.value, x: point.x, y: point.y })));

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">{title}</p>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-2 h-32 w-full overflow-visible">
        {[0, maxValue / 2, maxValue].map((tick) => (
          <g key={tick}>
            <line x1={paddingX} x2={width - paddingX} y1={yForValue(tick)} y2={yForValue(tick)} stroke="rgba(255,255,255,0.06)" />
            <text x={0} y={yForValue(tick) + 4} fill="#64748b" fontSize="10">{tick.toFixed(0)}%</text>
          </g>
        ))}
        <path d={path} fill="none" stroke="#67e8f9" strokeLinecap="round" strokeWidth="2.4" />
        {drawable.map((point) => (
          <circle key={point.contestId} cx={point.x} cy={point.y} r={point.contestId === activeContestId ? 4 : 3} fill="#67e8f9" stroke="#08111f" strokeWidth="2" />
        ))}
        {points.map((point, index) => (
          <text key={point.contestId} x={xForIndex(index)} y={height - 2} textAnchor="middle" fill={point.contestId === activeContestId ? "#e2e8f0" : "#64748b"} fontSize="10" fontWeight={point.contestId === activeContestId ? 700 : 500}>
            {point.label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function BlocEvolutionChart({
  points,
  activeContestId,
}: {
  points: BlocHistoryPoint[];
  activeContestId: string;
}) {
  const series = [
    { key: "left", label: "Left Bloc", color: "#67d4f2" },
    { key: "right", label: "Right Bloc", color: "#f59e63" },
    { key: "regionalOther", label: "Regional / Other", color: "#9fb36a" },
  ] as const;

  return (
    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Bloc evolution</p>
      <div className="mt-3 grid gap-3">
        {points.map((point) => {
          const isActive = point.contestId === activeContestId;
          return (
            <div key={point.contestId}>
              <div className="mb-1.5 flex items-center justify-between text-[0.68rem]">
                <span className={isActive ? "font-semibold text-slate-100" : "text-slate-500"}>{point.label}</span>
              </div>
              <div className={`flex h-3 overflow-hidden rounded-full border ${isActive ? "border-cyan-200/25" : "border-white/[0.06]"} bg-white/[0.04]`}>
                {series.map((item) => {
                  const value = point[item.key] ?? 0;
                  return <div key={item.key} style={{ width: `${Math.max(0, Math.min(100, value))}%`, backgroundColor: item.color }} />;
                })}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {series.map((item) => (
          <span key={item.key} className="inline-flex items-center gap-1.5 text-[0.68rem] text-slate-400">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function ElectoralProfileGrid({ profile }: { profile: SectionFeatureProperties | null | undefined }) {
  const winningParty = normalizePartyName(profile?.winning_party) || "N/A";
  const margin = toFiniteNumber(profile?.victory_margin_pct);
  const left = getElectoralMetric(profile, "left");
  const right = getElectoralMetric(profile, "right");
  const regionalOther = getElectoralMetric(profile, "regionalOther");
  const turnout = getElectoralMetric(profile, "turnout");
  const fragmentation = getElectoralMetric(profile, "fragmentation");
  const items = [
    ["Winning Party", winningParty],
    ["Victory Margin", margin == null ? "N/A" : `${margin.toFixed(1)} pp`],
    ["Left Bloc", left == null ? "N/A" : `${left.toFixed(1)}%`],
    ["Right Bloc", right == null ? "N/A" : `${right.toFixed(1)}%`],
    ["Regional / Other", regionalOther == null ? "N/A" : `${regionalOther.toFixed(1)}%`],
    ["Turnout", turnout == null ? "N/A" : `${turnout.toFixed(1)}%`],
    ["Fragmentation", fragmentation == null ? "N/A" : `${fragmentation.toFixed(1)}%`],
  ];

  return (
    <div className="mt-4 grid grid-cols-2 gap-2">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-2xl border border-white/[0.06] bg-[#0d1423] px-3 py-2.5">
          <p className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
          <p className="mt-1 truncate text-sm font-semibold text-slate-100">{value}</p>
        </div>
      ))}
    </div>
  );
}

function ElectoralOverview({
  title,
  subtitle,
  contest,
  activeCollection,
  historyCollections,
  selectedSectionId,
  selectedSection,
}: {
  title: string;
  subtitle: string;
  contest: ElectionContest;
  activeCollection?: SectionFeatureCollection;
  historyCollections: Partial<Record<string, SectionFeatureCollection>>;
  selectedSectionId?: string;
  selectedSection?: SectionFeatureProperties;
}) {
  const typeStyle = ELECTION_TYPE_STYLES[contest.type];
  const activePartyShare = selectedSection
    ? getFeaturePartyShare(selectedSection)
    : aggregateElectionCollection(activeCollection);
  const fallbackWinningPct = toFiniteNumber(selectedSection?.winning_party_pct);
  const fallbackMargin = toFiniteNumber(selectedSection?.victory_margin_pct);
  const winningParty =
    activePartyShare[0]?.party ?? (normalizePartyName(selectedSection?.winning_party) || "--");
  const winningPct = activePartyShare[0]?.percentage ?? fallbackWinningPct;
  const runnerUpPct = activePartyShare[1]?.percentage ?? null;
  const margin = winningPct != null && runnerUpPct != null ? winningPct - runnerUpPct : fallbackMargin;
  const participation = selectedSection ? getTurnout(selectedSection) : aggregateTurnout(activeCollection);
  const relevantParties = activePartyShare.filter((point) => point.percentage > 3).slice(0, 5).map((point) => point.party);
  const historyContests = electionContests.filter((item) => item.type === contest.type && item.electionId != null);
  const historyPoints = historyContests.flatMap((historyContest) => {
      const collection = historyCollections[historyContest.id];
      const source = selectedSectionId
        ? getSectionFromCollection(collection, selectedSectionId)
        : undefined;
      const shares = selectedSectionId
        ? getFeaturePartyShare(source)
        : aggregateElectionCollection(collection);
      return relevantParties.map((party) => ({
        contestId: historyContest.id,
        label: historyContest.label,
        party,
        percentage: shares.find((share) => share.party === party)?.percentage ?? null,
      }));
    });
  const profile = selectedSection ?? buildMunicipalityCampaignProfile(activeCollection);
  const turnoutPoints = historyContests.map((historyContest) => {
    const collection = historyCollections[historyContest.id];
    const source = selectedSectionId ? getSectionFromCollection(collection, selectedSectionId) : undefined;
    return {
      contestId: historyContest.id,
      label: historyContest.label,
      value: selectedSectionId ? getElectoralMetric(source, "turnout") : aggregateElectoralMetric(collection, "turnout"),
    };
  });
  const blocPoints = historyContests.map((historyContest) => {
    const collection = historyCollections[historyContest.id];
    const source = selectedSectionId ? getSectionFromCollection(collection, selectedSectionId) : undefined;
    return {
      contestId: historyContest.id,
      label: historyContest.label,
      left: selectedSectionId ? getElectoralMetric(source, "left") : aggregateElectoralMetric(collection, "left"),
      right: selectedSectionId ? getElectoralMetric(source, "right") : aggregateElectoralMetric(collection, "right"),
      regionalOther: selectedSectionId
        ? getElectoralMetric(source, "regionalOther")
        : aggregateElectoralMetric(collection, "regionalOther"),
    };
  });

  return (
    <div className="w-full">
      <div className={`rounded-3xl border border-white/8 bg-white/[0.03] p-4 ${typeStyle.glow}`}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Electoral Profile
            </p>
            <h2 className="font-manrope mt-2 truncate text-left text-[1.35rem] font-semibold text-white">
              {title}
            </h2>
            <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
              {subtitle}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1.5">
            <span className={`rounded-full border px-2.5 py-1 text-[0.68rem] font-semibold ${typeStyle.border} ${typeStyle.bg} ${typeStyle.text}`}>
              {contest.label}
            </span>
            <ElectionTypePill type={contest.type} />
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-white/[0.06] bg-[#0d1423] p-4">
          <p className="text-xs text-slate-500">Winning Party</p>
          <div className="mt-2 flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: rgbaToCss(getPartyColor(winningParty)) }}
            />
            <p className="text-xl font-semibold text-white">
              {winningParty} · {winningPct == null ? "N/A" : `${winningPct.toFixed(1)}%`}
            </p>
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-3">
            <span className="text-xs text-slate-500">Victory Margin</span>
            <span className="text-sm font-semibold text-slate-100">
              {margin == null ? "N/A" : `${margin >= 0 ? "+" : ""}${margin.toFixed(1)} pp`}
            </span>
          </div>
        </div>

        <ElectoralProfileGrid profile={profile} />
        <VoteShareBarChart points={activePartyShare} />
        <ElectoralEvolutionLineChart
          contests={historyContests}
          points={historyPoints}
          activeContestId={contest.id}
        />
        <ElectoralMetricLineChart
          title="Participation evolution"
          points={turnoutPoints}
          activeContestId={contest.id}
        />
        <BlocEvolutionChart points={blocPoints} activeContestId={contest.id} />
        <ParticipationRadial participation={participation} />
      </div>
    </div>
  );
}

export function RightSidebar() {
  const selectedSectionId = useDashboardStore((state) => state.selectedSectionId);
  const selectedMunicipalityId = useDashboardStore((state) => state.selectedMunicipalityId);
  const detailTab = useDashboardStore((state) => state.detailTab);
  const setDetailTab = useDashboardStore((state) => state.setDetailTab);
  const sectionFeatureById = useDashboardStore((state) => state.sectionFeatureById);
  const sectionDetailsById = useDashboardStore((state) => state.sectionDetailsById);
  const municipalityPopulationByYear = useDashboardStore((state) => state.municipalityPopulationByYear);
  const municipalityAgeStructureByYear = useDashboardStore((state) => state.municipalityAgeStructureByYear);
  const municipalityIncomeByYear = useDashboardStore((state) => state.municipalityIncomeByYear);
  const sectionCollection = useDashboardStore((state) => state.sectionCollection);
  const electoralCollectionsByContest = useDashboardStore((state) => state.electoralCollectionsByContest);
  const isDetailLoading = useDashboardStore((state) => state.isDetailLoading);
  const isMapLoading = useDashboardStore((state) => state.isMapLoading);
  const dataSource = useDashboardStore((state) => state.dataSource);
  const layers = useDashboardStore((state) => state.layers);
  const activeSubLayer = useDashboardStore((state) => state.activeSubLayer);
  const electionContestId = useDashboardStore((state) => state.filters.electionContestId);
  const populationYear = useDashboardStore((state) => state.filters.populationYear);
  const ageStructureYear = useDashboardStore((state) => state.filters.ageStructureYear);
  const incomeYear = useDashboardStore((state) => state.filters.incomeYear);
  const landBuiltEnvironmentMetric = useDashboardStore((state) => state.landBuiltEnvironmentMetric);
  const territorialMetric = useDashboardStore((state) => state.territorialMetric);
  const socioeconomicMetric = useDashboardStore((state) => state.socioeconomicMetric);
  const campaignForecastMetric = useDashboardStore((state) => state.campaignForecastMetric);
  const productivePotentialVariable = useDashboardStore((state) => state.productivePotentialVariable);
  const rightPanelMode = useDashboardStore((state) => state.rightPanelMode);
  const askChartResponse = useDashboardStore((state) => state.askChartResponse);
  const setRightPanelMode = useDashboardStore((state) => state.setRightPanelMode);
  const setAskChartResponse = useDashboardStore((state) => state.setAskChartResponse);
  const queueAskPrompt = useDashboardStore((state) => state.queueAskPrompt);
  const setProductivePotentialVariable = useDashboardStore((state) => state.setProductivePotentialVariable);
  const setCampaignForecastMetric = useDashboardStore((state) => state.setCampaignForecastMetric);
  const clearSelectedSectionAndShowMunicipality = useDashboardStore(
    (state) => state.clearSelectedSectionAndShowMunicipality,
  );

  const feature = selectedSectionId ? sectionFeatureById[selectedSectionId] : undefined;
  const activeLayer = getActiveLayer(layers);

  if (rightPanelMode === "askTests") {
    return (
      <AskTestsPanel
        onRunTest={(test) => {
          setAskChartResponse(null);
          setRightPanelMode("askChart");
          queueAskPrompt(test.prompt);
        }}
        onClose={() => setRightPanelMode("default")}
      />
    );
  }

  if (rightPanelMode === "askChart") {
    return (
      <AskChartPanel
        response={askChartResponse}
        onBackToTests={() => setRightPanelMode("askTests")}
        onClose={() => setRightPanelMode("default")}
      />
    );
  }

  const selectedElectionContest =
    electionContests.find((contest) => contest.id === electionContestId) ?? electionContests[0];
  const activeElectionCollection = electoralCollectionsByContest[selectedElectionContest.id];
  const dataYear =
    activeLayer === "population"
      ? populationYear
      : activeLayer === "ageStructure"
        ? ageStructureYear
        : activeLayer === "incomeLevel"
          ? incomeYear
          : activeLayer === "socioeconomicIntelligence"
            ? SOCIAL_DEVELOPMENT_UI_YEAR
            : activeLayer === "electoralForecasting"
              ? selectedElectionContest.year
            : activeLayer === "electoralBehavior"
              ? selectedElectionContest.year
              : OPERATIONAL_DATA_YEAR;
  const detail = selectedSectionId ? sectionDetailsById[`${dataYear}:${selectedSectionId}`] : undefined;

  if (!feature) {
    if (activeLayer === "population" && !selectedSectionId) {
      const municipalitySummaries = populationYears
        .map((summaryYear) => municipalityPopulationByYear[summaryYear])
        .filter((summary): summary is MunicipalityPopulationSummary => Boolean(summary));

      return (
        <MunicipalityPopulationOverview
          summaries={municipalitySummaries}
          selectedYear={populationYear}
          isLoading={isMapLoading && municipalitySummaries.length === 0}
        />
      );
    }

    if (activeLayer === "ageStructure" && !selectedSectionId) {
      const municipalityAgeSummaries = ageStructureYears
        .map((summaryYear) => municipalityAgeStructureByYear[summaryYear])
        .filter((summary): summary is MunicipalityAgeStructureSummary => Boolean(summary));

      return (
        <MunicipalityAgeStructureOverview
          summaries={municipalityAgeSummaries}
          selectedYear={ageStructureYear}
          isLoading={isMapLoading && municipalityAgeSummaries.length === 0}
        />
      );
    }

    if (activeLayer === "incomeLevel" && !selectedSectionId) {
      const municipalityIncomeSummaries = incomeYears
        .map((summaryYear) => municipalityIncomeByYear[summaryYear])
        .filter((summary): summary is MunicipalityIncomeSummary => Boolean(summary));

      return (
        <MunicipalityIncomeOverview
          summaries={municipalityIncomeSummaries}
          selectedYear={incomeYear}
          isLoading={isMapLoading && municipalityIncomeSummaries.length === 0}
        />
      );
    }

    if (activeLayer === "electoralBehavior" && !selectedSectionId) {
      return (
        <Panel className="flex h-full min-h-0 flex-col overflow-y-auto p-5">
          <ElectoralOverview
            title="Mijas"
            subtitle="Municipality overview"
            contest={selectedElectionContest}
            activeCollection={activeElectionCollection ?? sectionCollection ?? undefined}
            historyCollections={electoralCollectionsByContest}
          />
        </Panel>
      );
    }

    if (activeLayer === "electoralForecasting" && !selectedSectionId) {
      return (
        <CampaignBuilderPanel
          title="Mijas"
          subtitle="Municipality overview"
          collection={sectionCollection}
          metric={campaignForecastMetric}
          onMetricChange={setCampaignForecastMetric}
          onRoot={clearSelectedSectionAndShowMunicipality}
        />
      );
    }

    if (activeLayer === "landBuiltEnvironment" && !selectedSectionId) {
      return (
        <LandBuiltEnvironmentAnalytics
          title="Mijas"
          subtitle="Municipality overview"
          collection={sectionCollection}
          metric={landBuiltEnvironmentMetric}
        />
      );
    }

    if (activeLayer === "socioeconomicIntelligence" && !selectedSectionId) {
      return (
        <SocioeconomicIntelligencePanel
          title="Mijas"
          subtitle="Municipality overview"
          municipalityId={selectedMunicipalityId}
          currentCollection={sectionCollection}
          year={SOCIAL_DEVELOPMENT_UI_YEAR}
          subLayer={activeSubLayer}
          productiveVariable={productivePotentialVariable}
          onProductiveVariableChange={setProductivePotentialVariable}
          onRoot={clearSelectedSectionAndShowMunicipality}
        />
      );
    }

    if (activeLayer === "housingIntelligence" && !selectedSectionId) {
        const municipalityProfile = buildMunicipalityHousingProfile(sectionCollection);
        if (municipalityProfile) {
          return (
            <HousingQualityPanel
              title="Mijas"
              subtitle="Resumen municipal"
              section={municipalityProfile}
              scope="municipality"
            />
          );
      }

      return (
        <Panel className="flex h-full items-center justify-center p-6 text-center text-sm text-slate-400">
          La inteligencia inmobiliaria se está cargando.
        </Panel>
      );
    }

    return (
      <Panel className="flex h-full items-center justify-center p-6 text-center text-sm text-slate-400">
        Selecciona una sección en el mapa para consultar su perfil.
      </Panel>
    );
  }

  const section = feature.properties;
  const sectionTitle = getSectionDisplayName(detail, section);
  const sectionSubtitle = formatMunicipalitySectionSubtitle(
    detail?.display.municipality ?? section.municipality ?? "Mijas",
    detail?.display.section_number ?? section.section_number,
  );
  const silhouetteColor = getSectionLayerColor(
    section,
    activeLayer,
    landBuiltEnvironmentMetric,
    territorialMetric,
    socioeconomicMetric,
  );
  const densityValue = detail?.geography.population_density ?? section.population_density;
  const individualIncome = detail?.income?.renta_media_persona ?? section.renta_media_persona;
  const householdIncome = detail?.income?.renta_media_hogar ?? section.renta_media_hogar;
  const overviewItems = [
    { label: "Población", value: number(detail?.demography.population_total ?? section.population_total) },
    {
      label: "Densidad",
      value: densityValue != null ? `${Math.round(densityValue).toLocaleString("es-ES")} / km²` : "--",
    },
    ...(activeLayer === "incomeLevel"
      ? [
          { label: "Renta individual", value: formatEuro(individualIncome) },
          { label: "Household Income", value: formatEuro(householdIncome) },
        ]
      : activeLayer === "population"
        ? [
            { label: "Male", value: percentage(section.pct_male) },
            { label: "Female", value: percentage(section.pct_female) },
          ]
      : [
          { label: "Turnout", value: percentage(detail?.electoral.turnout ?? section.turnout) },
          { label: "Winning Party", value: normalizePartyName(detail?.electoral.winning_party ?? section.winning_party) || "--" },
        ]),
  ];
  const populationEvolutionPoints = populationYears.map((populationPointYear) => {
    const yearDetail =
      selectedSectionId != null
        ? sectionDetailsById[`${populationPointYear}:${selectedSectionId}`]
        : undefined;
    const fallbackValue =
      populationPointYear === dataYear ? (detail?.demography.population_total ?? section.population_total) : null;

    return {
      year: populationPointYear,
      value: yearDetail?.demography.population_total ?? fallbackValue ?? null,
    };
  });
  const ageCohorts = buildAgeCohorts(detail, section);
  const selectedAgeTotal =
    detail?.demography.population_total ??
    section.population_total ??
    ageCohorts.reduce((total, cohort) => total + cohort.population, 0);
  const selectedAgeOver65 =
    detail?.demography.pct_65_plus ??
    section.pct_65_plus ??
    (selectedAgeTotal > 0 ? (getCohortPopulation(AGE_COHORTS[4], detail, section) ?? 0) / selectedAgeTotal : null);
  const selectedAgeUnder30 =
    selectedAgeTotal > 0
      ? ((getCohortPopulation(AGE_COHORTS[0], detail, section) ?? 0) +
          (getCohortPopulation(AGE_COHORTS[1], detail, section) ?? 0)) /
        selectedAgeTotal
      : null;
  const selectedPyramidRows = buildAgeGenderPyramidRows({
    cohorts: ageCohorts,
    menTotal: detail?.demography.population_male ?? section.population_male,
    womenTotal: detail?.demography.population_female ?? section.population_female,
  });
  const selectedGenderTotal =
    (detail?.demography.population_male ?? section.population_male ?? 0) +
    (detail?.demography.population_female ?? section.population_female ?? 0);
  const selectedAgeInsight = generateAgeStructureInsight({
    totalPopulation: selectedAgeTotal,
    averageAge: section.average_age,
    pct65Plus: selectedAgeOver65,
    pctUnder30: selectedAgeUnder30,
    dominantCohort: getDominantCohort(ageCohorts),
    genderBalance:
      selectedGenderTotal > 0
        ? (detail?.demography.population_female ?? section.population_female ?? 0) / selectedGenderTotal
        : null,
  });
  const selectedLowerAgeKpis = [
    {
      label: "Foreign-born",
      value:
        (detail?.demography.pct_foreign_born ?? section.pct_foreign_born) != null
          ? `${((detail?.demography.pct_foreign_born ?? section.pct_foreign_born ?? 0) * 100).toFixed(1)}%`
          : "--",
    },
  ];
  const ageEvolutionPoints = ageStructureYears.flatMap((ageYear) => {
    const yearDetail = selectedSectionId
      ? sectionDetailsById[`${ageYear}:${selectedSectionId}`]
      : undefined;
    const sectionFallback = ageYear === dataYear ? section : undefined;

    return AGE_COHORTS.flatMap((definition) => {
      const population = getCohortPopulation(definition, yearDetail, sectionFallback);

      return population == null
        ? []
        : [
            {
              year: ageYear,
              cohort: definition.cohort,
              population,
            },
        ];
    });
  });
  const incomeBarPoints = incomeYears.map((incomePointYear) => {
    const yearDetail = selectedSectionId
      ? sectionDetailsById[`${incomePointYear}:${selectedSectionId}`]
      : undefined;
    const fallbackSection = incomePointYear === dataYear ? section : undefined;

    return {
      year: incomePointYear,
      individualIncome:
        yearDetail?.income?.renta_media_persona ??
        fallbackSection?.renta_media_persona ??
        null,
      householdIncome:
        yearDetail?.income?.renta_media_hogar ??
        fallbackSection?.renta_media_hogar ??
        null,
    };
  });
  const incomeSourcePoints = incomeYears.flatMap((incomePointYear) => {
    const yearDetail = selectedSectionId
      ? sectionDetailsById[`${incomePointYear}:${selectedSectionId}`]
      : undefined;
    const fallbackSection = incomePointYear === dataYear ? section : undefined;

    return INCOME_SOURCES.flatMap((source) => {
      const value = getIncomeSourceValue(source.key, yearDetail, fallbackSection);

      return value == null
        ? []
        : [
            {
              year: incomePointYear,
              source: source.key,
              value,
            },
          ];
    });
  });

  const demographicItems = [
    { label: "0-14", value: percentage(detail?.demography.pct_0_14) },
    { label: "15-29", value: percentage(detail?.demography.pct_15_29) },
    { label: "30-44", value: percentage(detail?.demography.pct_30_44) },
    { label: "45-64", value: percentage(detail?.demography.pct_45_64) },
    { label: "65+", value: percentage(detail?.demography.pct_65_plus) },
    { label: "Dependency Ratio", value: detail?.demography.dependency_ratio?.toFixed(2) ?? "--" },
  ];

  const electoralItems = [
    { label: "Winning Party", value: normalizePartyName(detail?.electoral.winning_party ?? section.winning_party) || "--" },
    { label: "Votes Cast", value: number(detail?.electoral.votes_cast) },
    { label: "Valid Votes", value: number(detail?.electoral.valid_votes) },
    { label: "PP", value: percentage(detail?.electoral.pct_pp) },
    { label: "PSOE", value: percentage(detail?.electoral.pct_psoe) },
    { label: "VOX", value: percentage(detail?.electoral.pct_vox) },
  ];

  const items =
    detailTab === "demographics"
      ? demographicItems
      : detailTab === "electoral"
        ? electoralItems
        : overviewItems;

  if (activeLayer === "landBuiltEnvironment") {
    return (
      <LandBuiltEnvironmentAnalytics
        title={sectionTitle}
        subtitle={sectionSubtitle}
        section={section}
        collection={sectionCollection}
        metric={landBuiltEnvironmentMetric}
      />
    );
  }

  if (activeLayer === "socioeconomicIntelligence") {
    return (
      <SocioeconomicIntelligencePanel
        title={sectionTitle}
        subtitle={sectionSubtitle}
        selectedSectionId={selectedSectionId}
        municipalityId={selectedMunicipalityId}
        currentCollection={sectionCollection}
        currentSection={section}
        year={SOCIAL_DEVELOPMENT_UI_YEAR}
        subLayer={activeSubLayer}
        productiveVariable={productivePotentialVariable}
        onProductiveVariableChange={setProductivePotentialVariable}
        onRoot={clearSelectedSectionAndShowMunicipality}
      />
    );
  }

  if (activeLayer === "electoralForecasting") {
    return (
      <CampaignBuilderPanel
        title={sectionTitle}
        subtitle={sectionSubtitle}
        collection={sectionCollection}
        selectedSection={section}
        metric={campaignForecastMetric}
        onMetricChange={setCampaignForecastMetric}
        onRoot={clearSelectedSectionAndShowMunicipality}
      />
    );
  }

  if (activeLayer === "housingIntelligence") {
    const hasSignal = hasTerritorialSignal(section);

    return (
      hasSignal ? (
        <HousingQualityPanel
          title={sectionTitle}
          subtitle={sectionSubtitle}
          section={section}
          scope="section"
        />
      ) : (
        <Panel className="flex h-full flex-col p-4">
          <Panel className="mt-6 p-4">
            <p className="text-sm text-slate-300">No housing signal available for this section.</p>
          </Panel>
        </Panel>
      )
    );
  }

  return (
    <Panel className="flex h-full flex-col p-4">
      <div className="relative">
        {activeLayer === "population" ? (
          <div className="w-full">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Evolution
                </p>
                <h2 className="font-manrope mt-2 truncate text-left text-[1.35rem] font-semibold text-white">
                  {sectionTitle}
                </h2>
                <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
                  {sectionSubtitle}
                </p>
              </div>
              <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
                2021-2025
              </span>
            </div>
            <PopulationEvolutionChart
              points={populationEvolutionPoints}
              isLoading={isDetailLoading}
              activeYear={populationYear}
            />
          </div>
        ) : activeLayer === "ageStructure" ? (
          <div className="w-full">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Evolution
                </p>
                <h2 className="font-manrope mt-2 truncate text-left text-[1.35rem] font-semibold text-white">
                  {sectionTitle}
                </h2>
                <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
                  {sectionSubtitle}
                </p>
              </div>
              <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
                {ageStructureYear}
              </span>
            </div>
            <AgeStructureTopStats
              averageAge={section.average_age}
              over65Pct={selectedAgeOver65}
            />
            <AgeCohortBarChart cohorts={ageCohorts} isLoading={isDetailLoading} />
            <AgeCohortEvolutionChart
              points={ageEvolutionPoints}
              activeYear={ageStructureYear}
              isLoading={isDetailLoading}
            />
            <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.85fr)]">
              <AgeGenderPyramidChart
                rows={selectedPyramidRows}
                estimated
                isLoading={isDetailLoading}
              />
              <AgeStructureInsightCard insight={selectedAgeInsight} />
            </div>
            <AgeStructureKpiGrid items={selectedLowerAgeKpis} />
          </div>
        ) : activeLayer === "incomeLevel" ? (
          <div className="w-full">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
                  Evolution
                </p>
                <h2 className="font-manrope mt-2 truncate text-left text-[1.35rem] font-semibold text-white">
                  {sectionTitle}
                </h2>
                <p className="font-manrope mt-1 text-left text-sm font-medium text-slate-400">
                  {sectionSubtitle}
                </p>
              </div>
              <span className="shrink-0 rounded-full border border-cyan-200/15 bg-cyan-200/[0.08] px-2.5 py-1 text-[0.68rem] font-semibold text-cyan-100">
                {incomeYear}
              </span>
            </div>
            <IncomeStackedBarChart
              points={incomeBarPoints}
              activeYear={incomeYear}
              isLoading={isDetailLoading}
            />
            <div className="mt-5">
              <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Income source evolution
              </p>
              <IncomeSourcesLineChart
                points={incomeSourcePoints}
                activeYear={incomeYear}
                isLoading={isDetailLoading}
              />
            </div>
          </div>
        ) : activeLayer === "electoralBehavior" ? (
          <ElectoralOverview
            title={sectionTitle}
            subtitle={sectionSubtitle.replace(" - ", " · ")}
            contest={selectedElectionContest}
            activeCollection={activeElectionCollection ?? sectionCollection ?? undefined}
            historyCollections={electoralCollectionsByContest}
            selectedSectionId={selectedSectionId ?? undefined}
            selectedSection={section}
          />
        ) : (
          <div className="flex w-full flex-col pr-16">
            <div className="max-w-[15rem]">
              <p className="text-left text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
                Selected Section
              </p>
              <h2 className="font-manrope mt-2 text-left text-balance text-[1.8rem] font-semibold tracking-[-0.04em] text-white">
                {sectionTitle}
              </h2>
            </div>
            <SectionShapePreview
              geometry={feature.geometry}
              color={silhouetteColor}
              title={sectionTitle}
            />
            <p className="font-manrope mt-2 max-w-[15rem] text-left text-sm font-medium text-slate-400">
              {sectionSubtitle}
            </p>
          </div>
        )}
      </div>

      {activeLayer !== "ageStructure" ? (
      <div className="mt-6 flex gap-2 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setDetailTab(tab.id)}
            className={`rounded-full px-3 py-2 text-[0.75rem] font-semibold uppercase tracking-[0.14em] transition ${
              detailTab === tab.id
                ? "bg-white/[0.08] text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      ) : null}

      {activeLayer !== "ageStructure" ? (
      <div className="mt-5 rounded-3xl border border-white/8 bg-white/[0.03] p-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-500">
          {detail?.display.label ?? section.label ?? selectedSectionId}
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {items.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-white/[0.06] bg-[#0d1423] px-4 py-3"
            >
              <p className="text-xs text-slate-500">{item.label}</p>
              <p className="mt-1 text-lg font-semibold text-white">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
      ) : null}

      <Panel className="mt-4 p-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Status
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          {isDetailLoading
            ? "Loading section profile from the FastAPI backend..."
            : dataSource === "mock"
              ? "You are browsing fallback mock data because the backend is unavailable. Detail cards are built from the map payload only."
              : dataSource === "unavailable"
                ? "The backend is offline, so there is no live section geometry or detail payload available yet."
              : "This panel is backed by the live section-detail endpoint and is ready to grow with more modules."}
        </p>

        <div className="mt-5 space-y-2">
          {[
            { label: "Municipality", value: detail?.display.municipality ?? section.municipality },
            { label: "Neighborhood", value: detail?.display.neighborhood ?? section.neighborhood ?? "--" },
            { label: "Zone", value: detail?.display.zone ?? section.zone ?? "--" },
            { label: "Year", value: detail?.display.year?.toString() ?? "--" },
          ].map((item) => (
            <div
              key={item.label}
              className="flex items-center justify-between rounded-xl border border-white/8 bg-white/[0.03] px-3 py-2"
            >
              <span className="text-xs text-slate-500">{item.label}</span>
              <span className="text-sm text-slate-200">{item.value}</span>
            </div>
          ))}
        </div>
      </Panel>
    </Panel>
  );
}
