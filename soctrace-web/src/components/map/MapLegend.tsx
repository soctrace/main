import type { LandBuiltEnvironmentMetricKey, LayerKey, SocioeconomicMetricKey, TerritorialMetricKey } from "@/types/api";
import {
  INCOME_LEVEL_COLOR_STOPS,
  type RealEstateLegend,
  type LandBuiltEnvironmentLegend,
  type SocioeconomicLegend,
  type TerritorialLegend,
  buildLandBuiltEnvironmentLegend,
  buildSocioeconomicLegend,
  buildTerritorialLegend,
  getPartyColor,
  normalizePartyName,
  rgbaToCss,
} from "@/lib/sectionPresentation";

const densityLegendItems = [
  { label: "> 40.000 / km²", tone: "Muy alta", color: "#8B5CF6" },
  { label: "25.001 - 40.000 / km²", tone: "Alta", color: "#F43F5E" },
  { label: "10.001 - 25.000 / km²", tone: "Media", color: "#F4B740" },
  { label: "1.001 - 10.000 / km²", tone: "Baja", color: "#67D4F2" },
  { label: "< 1.000 / km²", tone: "Muy baja", color: "#3B82F6" },
] as const;

const ageLegendItems = [
  { label: "< 36", tone: "Muy joven / joven", color: "#2DD4BF" },
  { label: "36 - 39", tone: "Adulto joven", color: "#74C476" },
  { label: "39 - 42", tone: "Equilibrada", color: "#F2D56B" },
  { label: "42 - 44,5", tone: "Madura", color: "#F59E4B" },
  { label: "> 44,5", tone: "Mayor", color: "#C95C66" },
] as const;

const incomeLegendItems = [
  { label: "Muy baja", tone: "Renta muy baja", color: INCOME_LEVEL_COLOR_STOPS.veryLow },
  { label: "Baja", tone: "Renta baja", color: INCOME_LEVEL_COLOR_STOPS.low },
  { label: "Media", tone: "Renta media", color: INCOME_LEVEL_COLOR_STOPS.medium },
  { label: "Alta", tone: "Renta alta", color: INCOME_LEVEL_COLOR_STOPS.high },
  { label: "Muy alta", tone: "Renta muy alta", color: INCOME_LEVEL_COLOR_STOPS.veryHigh },
] as const;

type MapLegendProps = {
  activeLayer: LayerKey | null;
  minValue?: number | null;
  maxValue?: number | null;
  winningParties?: string[];
  realEstateLegend?: RealEstateLegend | null;
  landBuiltEnvironmentMetric?: LandBuiltEnvironmentMetricKey;
  territorialMetric?: TerritorialMetricKey;
  socioeconomicMetric?: SocioeconomicMetricKey;
  displayYear?: string | null;
  electionLabel?: string | null;
};

export function MapLegend({
  activeLayer,
  minValue: _minValue,
  maxValue: _maxValue,
  winningParties = [],
  realEstateLegend = null,
  landBuiltEnvironmentMetric = "populationDensity",
  territorialMetric = "marketPressure",
  socioeconomicMetric = "humanCapital",
  displayYear = null,
  electionLabel = null,
}: MapLegendProps) {
  const isAgeStructure = activeLayer === "ageStructure";
  const isElectoral = activeLayer === "electoralBehavior";
  const isElectoralForecast = activeLayer === "electoralForecasting";
  const isIncome = activeLayer === "incomeLevel";
  const isLandBuiltEnvironment = activeLayer === "landBuiltEnvironment";
  const isHousingIntelligence = activeLayer === "housingIntelligence";
  const isSocioeconomicIntelligence = activeLayer === "socioeconomicIntelligence";
  const territorialLegend: TerritorialLegend | null = isHousingIntelligence
    ? buildTerritorialLegend(territorialMetric)
    : null;
  const landLegend: LandBuiltEnvironmentLegend | null = isLandBuiltEnvironment
    ? buildLandBuiltEnvironmentLegend(landBuiltEnvironmentMetric)
    : null;
  const socioeconomicLegend: SocioeconomicLegend | null = isSocioeconomicIntelligence
    ? buildSocioeconomicLegend(socioeconomicMetric)
    : null;
  const electoralLegendItems = winningParties.length > 0
    ? winningParties.map((party) => ({
        label: normalizePartyName(party) || party,
        tone: "Partido ganador",
        color: rgbaToCss(getPartyColor(party)),
      }))
    : [{ label: "N/D", tone: "Partido ganador", color: rgbaToCss(getPartyColor(null)) }];
  const items = isSocioeconomicIntelligence && socioeconomicLegend
    ? socioeconomicLegend.items.map((item) => ({ ...item, tone: socioeconomicLegend.subtitle }))
    : isHousingIntelligence && territorialLegend
    ? territorialLegend.items.map((item) => ({ ...item, tone: territorialLegend.subtitle }))
    : isLandBuiltEnvironment && landLegend
      ? landLegend.items.map((item) => ({ ...item, tone: landLegend.subtitle }))
    : isElectoral || isElectoralForecast
    ? electoralLegendItems
    : isIncome
      ? incomeLegendItems
      : isAgeStructure
        ? ageLegendItems
        : [...densityLegendItems].reverse();
  const title = isSocioeconomicIntelligence && socioeconomicLegend
    ? socioeconomicLegend.title
    : isHousingIntelligence && territorialLegend
    ? territorialLegend.title
    : isLandBuiltEnvironment && landLegend
      ? landLegend.title
    : isElectoralForecast
    ? "Previsión de campaña"
    : isElectoral
      ? "Resultados electorales"
    : isIncome
      ? "Nivel de renta"
      : isAgeStructure
        ? "Edad media"
        : "Densidad de población";
  const subtitle = isElectoral && electionLabel
    ? `${electionLabel} · Partido ganador`
    : displayYear
    ? `${isAgeStructure ? "Edad media" : isIncome ? "Renta neta individual" : isSocioeconomicIntelligence && socioeconomicLegend ? socioeconomicLegend.subtitle : "Capa"} · ${displayYear}`
    : isSocioeconomicIntelligence && socioeconomicLegend
    ? socioeconomicLegend.subtitle
    : isHousingIntelligence && territorialLegend
    ? territorialLegend.subtitle
    : isLandBuiltEnvironment && landLegend
      ? landLegend.subtitle
    : isElectoralForecast ? "Liderazgo proyectado · señal forecast" : isElectoral ? "Partido ganador" : isIncome ? "Baja → Alta" : null;
  const lowLabel = isElectoral || isElectoralForecast || isIncome ? null : isSocioeconomicIntelligence ? socioeconomicLegend?.labels[0] : isHousingIntelligence ? territorialLegend?.labels[0] : isLandBuiltEnvironment ? landLegend?.labels[0] : isAgeStructure ? "Joven" : "Baja";
  const highLabel = isElectoral || isElectoralForecast || isIncome ? null : isSocioeconomicIntelligence ? socioeconomicLegend?.labels[2] : isHousingIntelligence ? territorialLegend?.labels[2] : isLandBuiltEnvironment ? landLegend?.labels[2] : isAgeStructure ? "Mayor" : "Alta";

  return (
    <div className="absolute left-4 top-4 z-10 rounded-2xl border border-white/10 bg-[#0b1220]/88 px-4 py-3 shadow-[0_16px_40px_rgba(0,0,0,0.32)] backdrop-blur-xl">
      <div className="mb-2 flex items-center gap-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-slate-400">
        <span>{title}</span>
      </div>
      {subtitle ? <p className="mb-3 text-xs font-medium text-slate-500">{subtitle}</p> : null}
      <div className={isElectoral || isElectoralForecast ? "grid gap-2" : "flex items-center gap-2"}>
        {items.map((item, index) => (
          <div key={item.label} className="flex items-center gap-2">
            {index === 0 && lowLabel ? (
              <span className="text-[0.68rem] text-slate-500">{lowLabel}</span>
            ) : null}
            <span
              className={isElectoral || isElectoralForecast ? "h-3 w-3 rounded-full" : "h-3 w-10 rounded-full"}
              style={{ backgroundColor: item.color }}
              title={`${item.tone} · ${item.label}`}
            />
            {isElectoral || isElectoralForecast || isIncome ? (
              <span className="text-[0.68rem] text-slate-400">{item.label}</span>
            ) : null}
            {index === items.length - 1 && highLabel ? (
              <span className="text-[0.68rem] text-slate-500">{highLabel}</span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
