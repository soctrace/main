import { useDashboardStore } from "@/store/useDashboardStore";
import {
  formatPercentPoint,
  formatEuroPerM2,
  formatEuro,
  formatSignedPointMargin,
  formatScorePercent,
  formatLandBuiltEnvironmentMetricValue,
  getActiveLayer,
  getCampaignForecastLeader,
  getCampaignForecastMetricValue,
  getIncomeLevelLabel,
  getLandBuiltEnvironmentMetricValue,
  getPartyVoteShare,
  getSocioeconomicCompleteness,
  getSocioeconomicMetricLabel,
  getSocioeconomicMetricValue,
  getTerritorialMetricLabel,
  getTerritorialMetricValue,
  LAND_BUILT_ENVIRONMENT_METRICS,
  SOCIOECONOMIC_METRICS,
  TERRITORIAL_METRICS,
  normalizePartyName,
  hasLandBuiltEnvironment,
  hasSocioeconomicSignal,
  hasTerritorialSignal,
} from "@/lib/sectionPresentation";
import { electionContests } from "@/types/api";

const electionTypeLabels = {
  municipales: "Municipales",
  andaluzas: "Andaluzas",
  congreso: "Congreso",
  europeas: "Europeas",
} as const;

const pct = (value?: number | null) =>
  value == null ? "--" : `${(value * 100).toFixed(1)}%`;

const density = (value?: number | null) =>
  value == null ? "--" : `${Math.round(value).toLocaleString("es-ES")} / km²`;

const votePct = (value?: number | null) => (value == null ? "N/A" : `${value.toFixed(1)}%`);
const rank = (value?: number | null) => (value == null ? "N/A" : `${value} / 37`);

const score = (value?: number | null) => (value == null ? "N/A" : `${Math.round(value)} / 100`);
const plainPct = (value?: number | null) => (value == null ? "N/A" : `${value.toFixed(1)}%`);
const housingScore = (value?: number | null) => (value == null ? "N/A" : `${Math.round(value)}/100`);
const clampScore = (value?: number | null) =>
  typeof value === "number" && Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : null;

const incomeSourceLabels = {
  income_salary: "Wages",
  income_pension: "Pensions",
  income_unemployment: "Unemployment",
  income_social_benefits: "Other benefits",
  income_other: "Other income",
} as const;

function getMainIncomeSource(section: Record<string, unknown>) {
  const entries = Object.entries(incomeSourceLabels).flatMap(([key, label]) => {
    const value = section[key];
    return typeof value === "number" && Number.isFinite(value) ? [{ label, value }] : [];
  });

  return entries.sort((a, b) => b.value - a.value)[0] ?? null;
}

const sectionReference = (section: {
  label_cliente?: string | null;
  label?: string | null;
  display_name?: string | null;
  section_name?: string | null;
  section_number?: string | null;
  section_id: string;
}) =>
  section.label_cliente ??
  section.label ??
  section.display_name ??
  section.section_name ??
  section.section_number ??
  section.section_id;

export function SectionTooltip() {
  const hoverState = useDashboardStore((state) => state.hoverState);
  const sectionFeatureById = useDashboardStore((state) => state.sectionFeatureById);
  const layers = useDashboardStore((state) => state.layers);
  const landBuiltEnvironmentMetric = useDashboardStore((state) => state.landBuiltEnvironmentMetric);
  const territorialMetric = useDashboardStore((state) => state.territorialMetric);
  const socioeconomicMetric = useDashboardStore((state) => state.socioeconomicMetric);
  const electionContestId = useDashboardStore((state) => state.filters.electionContestId);
  const populationYear = useDashboardStore((state) => state.filters.populationYear);
  const ageStructureYear = useDashboardStore((state) => state.filters.ageStructureYear);
  const incomeYear = useDashboardStore((state) => state.filters.incomeYear);
  const socioeconomicYear = useDashboardStore((state) => state.filters.socioeconomicYear);

  if (!hoverState) {
    return null;
  }

  const feature = sectionFeatureById[hoverState.id];
  if (!feature) {
    return null;
  }

  const section = feature.properties;
  const activeLayer = getActiveLayer(layers);
  const selectedElectionContest =
    electionContests.find((contest) => contest.id === electionContestId) ?? electionContests[0];
  const tooltipPosition = {
    left: hoverState.x + 18,
    top: hoverState.y,
    transform: "translateY(-50%)",
  };

  if (activeLayer === "electoralBehavior") {
    const minVoteShareForTooltip = selectedElectionContest.type === "andaluzas" ? 1 : 0;
    const partyVotes = getPartyVoteShare(section).filter(
      (entry) => minVoteShareForTooltip === 0 || entry.percentage > minVoteShareForTooltip,
    );

    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[280px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas: {section.section_number ?? section.section_id}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Election: {electionTypeLabels[selectedElectionContest.type]} {selectedElectionContest.label}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Winning Party:{" "}
          <span className="font-semibold text-slate-100">
            {normalizePartyName(section.winning_party) || "N/A"} · {formatPercentPoint(section.winning_party_pct)}
          </span>
        </p>
        <p className="mt-1 text-xs text-slate-400">
          Margin:{" "}
          <span className="font-semibold text-slate-100">
            {formatSignedPointMargin(section.victory_margin_pct)}
          </span>
        </p>
        <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          Porcentaje de voto:
        </p>
        <div className="mt-3 space-y-1.5 text-sm">
          {partyVotes.length > 0 ? (
            partyVotes.map((entry, index) => (
              <div key={entry.party} className="flex items-center justify-between gap-8">
                <span className="font-medium text-slate-300">
                  {index + 1}. {entry.party}
                </span>
                <span className="tabular-nums text-slate-100">
                  {votePct(entry.percentage)}
                </span>
              </div>
            ))
          ) : (
            <p className="text-slate-400">No hay porcentajes de voto disponibles</p>
          )}
        </div>
      </div>
    );
  }

  if (activeLayer === "electoralForecasting") {
    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[286px] max-w-[330px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas · Section {section.section_number ?? section.section_id}
        </p>
        <p className="mt-1 text-xs text-slate-500">Señal de previsión de campaña</p>
        <div className="mt-3 grid gap-2 text-sm">
          {[
            ["Liderazgo previsto", getCampaignForecastLeader(section)],
            ["Confianza de previsión", plainPct(getCampaignForecastMetricValue(section, "forecastConfidence"))],
            ["Potencial de cambio", plainPct(getCampaignForecastMetricValue(section, "swingSections"))],
            ["Riesgo de abstención", plainPct(getCampaignForecastMetricValue(section, "abstentionRisk"))],
            ["Volatilidad", plainPct(getCampaignForecastMetricValue(section, "volatility"))],
          ].map(([label, value]) => (
            <div key={label} className="flex items-center justify-between gap-6">
              <p className="text-slate-500">{label}</p>
              <p className="font-semibold tabular-nums text-slate-100">{value}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 border-t border-white/[0.06] pt-3 text-[0.68rem] leading-4 text-slate-500">
          Estimación estratégica, no resultado oficial.
        </p>
      </div>
    );
  }

  if (activeLayer === "population") {
    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[270px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas: {sectionReference(section)}
        </p>
        <p className="mt-1 text-xs text-slate-500">Año: {populationYear}</p>
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-slate-500">Población</p>
            <p className="text-slate-100">
              {(section.population_total ?? 0).toLocaleString("es-ES")}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Densidad</p>
            <p className="text-slate-100">{density(section.population_density)}</p>
          </div>
          <div>
            <p className="text-slate-500">Hombres</p>
            <p className="text-slate-100">{pct(section.pct_male)}</p>
          </div>
          <div>
            <p className="text-slate-500">Mujeres</p>
            <p className="text-slate-100">{pct(section.pct_female)}</p>
          </div>
        </div>
      </div>
    );
  }

  if (activeLayer === "ageStructure") {
    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[250px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          {section.label ?? `Sección ${section.section_id}`}
        </p>
        <p className="mt-1 text-xs text-slate-400">Mijas: {sectionReference(section)}</p>
        <p className="mt-1 text-xs text-slate-500">Año: {ageStructureYear}</p>
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-slate-500">Edad media</p>
            <p className="text-slate-100">
              {section.average_age == null ? "--" : `${section.average_age.toFixed(1)} años`}
            </p>
          </div>
          <div>
            <p className="text-slate-500">&gt; 65</p>
            <p className="text-slate-100">{formatPercentPoint(section.over_65_pct ?? section.pct_65_plus)}</p>
          </div>
          <div>
            <p className="text-slate-500">&lt; 30</p>
            <p className="text-slate-100">{formatPercentPoint(section.under_30_pct)}</p>
          </div>
          <div>
            <p className="text-slate-500">Densidad de población</p>
            <p className="text-slate-100">
              {section.density_level ?? density(section.population_density)}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (activeLayer === "incomeLevel") {
    const incomeLevel =
      section.income_level ?? getIncomeLevelLabel(section.income_quintile);
    const mainIncomeSource = getMainIncomeSource(section);

    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[280px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas: {section.section_number ?? section.section_id}
        </p>
        <p className="mt-1 text-xs text-slate-500">Nivel de renta · {incomeYear}</p>
        <div className="mt-3 grid gap-2 text-sm">
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Renta neta individual</p>
            <p className="font-semibold tabular-nums text-slate-100">
              {formatEuro(section.renta_media_persona)}
            </p>
          </div>
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Renta neta del hogar</p>
            <p className="font-semibold tabular-nums text-slate-100">
              {formatEuro(section.renta_media_hogar)}
            </p>
          </div>
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Fuente principal de renta</p>
            <p className="font-semibold text-slate-100">
              {mainIncomeSource ? `${mainIncomeSource.label} · ${mainIncomeSource.value.toFixed(1)}%` : "N/D"}
            </p>
          </div>
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Nivel de renta</p>
            <p className="font-semibold text-slate-100">{incomeLevel}</p>
          </div>
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Ranking municipal</p>
            <p className="font-semibold tabular-nums text-slate-100">
              {rank(section.income_rank_municipal)}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (activeLayer === "landBuiltEnvironment") {
    const hasMetrics = hasLandBuiltEnvironment(section);
    const activeValue = getLandBuiltEnvironmentMetricValue(section, landBuiltEnvironmentMetric);
    const metricRows = [
      "populationDensity",
      "parcelDensity",
      "builtFootprint",
      "avgPlotSize",
      "buildingIntensity",
      "urbanIntensity",
    ] as const;

    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[286px] max-w-[320px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas · Section {section.section_number ?? section.section_id}
        </p>
        <div className="mt-3 grid gap-2 text-sm">
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Layer</p>
            <p className="font-semibold text-slate-100">Land / Built Environment</p>
          </div>
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Metric</p>
            <p className="font-semibold text-slate-100">
              {(LAND_BUILT_ENVIRONMENT_METRICS[landBuiltEnvironmentMetric] ?? LAND_BUILT_ENVIRONMENT_METRICS.populationDensity).title}
            </p>
          </div>
          <div className="flex items-center justify-between gap-6">
            <p className="text-slate-500">Value</p>
            <p className="font-semibold tabular-nums text-slate-100">
              {formatLandBuiltEnvironmentMetricValue(activeValue, landBuiltEnvironmentMetric)}
            </p>
          </div>
          {landBuiltEnvironmentMetric === "urbanIntensity" ? (
            <div className="flex items-center justify-between gap-6">
              <p className="text-slate-500">Level</p>
              <p className="font-semibold text-slate-100">{section.urban_intensity_label ?? "N/A"}</p>
            </div>
          ) : null}
        </div>
        {hasMetrics ? (
          <div className="mt-3 grid gap-1.5 border-t border-white/[0.06] pt-3 text-xs">
            {metricRows.map((metric) => (
              <div key={metric} className="flex items-center justify-between gap-5">
                <p className="text-slate-500">{LAND_BUILT_ENVIRONMENT_METRICS[metric].title}</p>
                <p className="font-semibold tabular-nums text-slate-100">
                  {formatLandBuiltEnvironmentMetricValue(getLandBuiltEnvironmentMetricValue(section, metric), metric)}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  if (activeLayer === "housingIntelligence") {
    const hasSignal = hasTerritorialSignal(section);
    const activeScore = getTerritorialMetricValue(section, territorialMetric);
    const residentialBalance =
      clampScore(section.residential_balance_score) ??
      (clampScore(section.residential_saturation_index) == null
        ? null
        : 100 - (clampScore(section.residential_saturation_index) ?? 0));
    const internationalAppeal =
      clampScore(section.international_appeal_score) ?? clampScore(section.foreign_demand_exposure);
    const signalRows = [
      ["Market Pressure", clampScore(section.market_pressure_index)],
      ["Prestigio urbano", clampScore(section.urban_prestige_signal)],
      ["Zonas de oportunidad", clampScore(section.opportunity_zone_score ?? section.opportunity_signal_score)],
      ["Equilibrio residencial", residentialBalance],
      ["Señal inmobiliaria", clampScore(section.housing_signal_score ?? section.territorial_signal_score)],
      ["Atracción internacional", internationalAppeal],
    ] as const;

    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[286px] max-w-[320px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas · Sección {section.section_number ?? section.section_id}
        </p>
        {hasSignal ? (
          <>
            <div className="mt-3 grid gap-2 text-sm">
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Capa</p>
                <p className="font-semibold text-slate-100">Inteligencia inmobiliaria</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Señal</p>
                <p className="font-semibold text-slate-100">{TERRITORIAL_METRICS[territorialMetric].title}</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Puntuación</p>
                <p className="font-semibold tabular-nums text-slate-100">
                  {formatScorePercent(activeScore)}
                </p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Nivel</p>
                <p className="font-semibold text-slate-100">{getTerritorialMetricLabel(section, territorialMetric)}</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Confianza</p>
                <p className="font-semibold text-slate-100">{section.confidence_level ?? "Media"}</p>
              </div>
            </div>
            <div className="mt-3 grid gap-1.5 border-t border-white/[0.06] pt-3 text-xs">
              {signalRows.map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-5">
                  <p className="text-slate-500">{label}</p>
                  <p className="font-semibold tabular-nums text-slate-100">
                    {housingScore(value)}
                  </p>
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between gap-6 border-t border-white/[0.06] pt-3 text-xs">
              <p className="text-slate-500">Referencia de mercado</p>
              <p className="font-semibold tabular-nums text-slate-100">
                {formatEuroPerM2(section.market_reference_m2)}
              </p>
            </div>
            <p className="mt-3 border-t border-white/[0.06] pt-3 text-[0.68rem] leading-4 text-slate-500">
              Señal comparativa, no una valoración formal.
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm text-slate-400">
            No hay señal inmobiliaria disponible para {getTerritorialMetricLabel(section, territorialMetric)}.
          </p>
        )}
      </div>
    );
  }

  if (activeLayer === "socioeconomicIntelligence") {
    const hasSignal = hasSocioeconomicSignal(section);
    const activeScore = getSocioeconomicMetricValue(section, socioeconomicMetric);
    const activeConfig = SOCIOECONOMIC_METRICS[socioeconomicMetric];
    const activeRows = {
      humanCapital: [
        ["Estudios superiores", plainPct(section.pct_higher_studies)],
        ["Empleo", plainPct(section.pct_employed)],
        ["Renta individual", formatEuro(section.renta_media_persona)],
      ],
      vulnerability: [
        ["Desempleo", plainPct(section.pct_unemployed)],
        ["Baja educación", plainPct(section.pct_no_studies)],
        ["Prestaciones sociales", plainPct(section.income_social_benefits)],
      ],
      resilience: [
        ["Empleo", plainPct(section.pct_employed)],
        ["Diversidad de renta", score(section.income_diversity_norm)],
        ["Menor desigualdad", score(section.lower_gini_norm)],
      ],
      productiveComplexity: [
        ["Ocupaciones cualificadas", plainPct(section.pct_qualified_occupations)],
        ["Diversidad sectorial", score(section.sector_diversity_norm)],
        ["Autónomos", plainPct(section.pct_self_employed)],
      ],
      inequalityPressure: [
        ["Gini", section.gini_index == null ? "N/D" : section.gini_index.toFixed(2)],
        ["P80/P20", section.p80_p20_ratio == null ? "N/D" : section.p80_p20_ratio.toFixed(2)],
        ["Índice de renta", score(section.income_index)],
      ],
    }[socioeconomicMetric];

    return (
      <div
        className="pointer-events-none absolute z-20 min-w-[286px] max-w-[330px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        style={tooltipPosition}
      >
        <p className="text-sm font-semibold text-white">
          Mijas: {sectionReference(section)}
        </p>
        {hasSignal ? (
          <>
            <div className="mt-3 grid gap-2 text-sm">
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Capa</p>
                <p className="font-semibold text-slate-100">Inteligencia socioeconómica</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Señal</p>
                <p className="font-semibold text-slate-100">{activeConfig.title}</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Puntuación</p>
                <p className="font-semibold tabular-nums text-slate-100">{score(activeScore)}</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Nivel</p>
                <p className="font-semibold text-slate-100">{getSocioeconomicMetricLabel(section, socioeconomicMetric)}</p>
              </div>
              <div className="flex items-center justify-between gap-6">
                <p className="text-slate-500">Cobertura de datos</p>
                <p className="font-semibold tabular-nums text-slate-100">
                  {plainPct(getSocioeconomicCompleteness(section, socioeconomicMetric))}
                </p>
              </div>
            </div>
            <div className="mt-3 grid gap-1.5 border-t border-white/[0.06] pt-3 text-xs">
              {activeRows.map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-5">
                  <p className="text-slate-500">{label}</p>
                  <p className="font-semibold tabular-nums text-slate-100">{value}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 border-t border-white/[0.06] pt-3 text-[0.68rem] leading-4 text-slate-500">
              Señal comparativa, no medida absoluta. Año: {socioeconomicYear}.
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm text-slate-400">No hay señal socioeconómica disponible.</p>
        )}
      </div>
    );
  }

  return (
    <div
      className="pointer-events-none absolute z-20 min-w-[220px] rounded-2xl border border-white/10 bg-[#0c1322]/94 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl"
      style={tooltipPosition}
    >
      <p className="text-sm font-semibold text-white">{section.label ?? section.section_id}</p>
      <p className="mt-1 text-xs text-slate-400">
        {section.municipality} · {section.district}
      </p>
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-slate-500">Población</p>
          <p className="text-slate-100">
            {(section.population_total ?? 0).toLocaleString("es-ES")}
          </p>
        </div>
        <div>
          <p className="text-slate-500">Densidad</p>
          <p className="text-slate-100">{density(section.population_density)}</p>
        </div>
        <div>
          <p className="text-slate-500">Participación</p>
          <p className="text-slate-100">{pct(section.turnout)}</p>
        </div>
        <div>
          <p className="text-slate-500">Partido ganador</p>
          <p className="text-slate-100">{normalizePartyName(section.winning_party) || "--"}</p>
        </div>
      </div>
    </div>
  );
}
