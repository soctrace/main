import {
  Activity,
  BarChart3,
  BriefcaseBusiness,
  ChevronDown,
  ChevronRight,
  Crosshair,
  Crown,
  Database,
  Globe2,
  Layers3,
  LockKeyhole,
  Map,
  MessageSquare,
  Network,
  RadioTower,
  ReceiptText,
  Scaling,
  Sparkles,
  Target,
  Users,
} from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { HoverTooltip } from "@/components/ui/HoverTooltip";
import { useDashboardStore } from "@/store/useDashboardStore";
import {
  ageStructureYears,
  electionContests,
  electionGroups,
  incomeYears,
  populationYears,
  SOCIAL_DEVELOPMENT_UI_YEAR,
  type CampaignForecastMetricKey,
  type ElectionContest,
  type ElectionGroup,
  type ElectionType,
  type LandBuiltEnvironmentMetricKey,
  type LayerCategory,
  type LayerKey,
  type SocioeconomicMetricKey,
  type TerritorialMetricKey,
} from "@/types/api";

const disabledTooltip = {
  comingSoon: "Próximamente",
  geometriesUnavailable: "Geometrías aún no disponibles",
} satisfies Record<NonNullable<ElectionContest["disabledReason"]>, string>;

type CategoryModel = {
  key: LayerCategory;
  title: string;
  description: string;
  icon: typeof Users;
  accent: string;
  accessTier?: "free" | "premium" | "pro";
  layers?: { id: string; label: string; future?: boolean; proFuture?: boolean; accessTier?: "free" | "premium" | "pro" }[];
};

type TerritorialSubItem = {
  id: string;
  layer: LayerKey;
  label: string;
  icon: typeof Users;
};

const categories: CategoryModel[] = [
  {
    key: "territorialData",
    title: "Datos territoriales",
    description: "Datos oficiales, históricos y territoriales por zona y año",
    icon: Globe2,
    accent: "border-cyan-300/18 bg-cyan-300/[0.075] text-emerald-200",
  },
  {
    key: "housingIntelligence",
    title: "Inteligencia inmobiliaria 🔒",
    description: "Señales inmobiliarias estratégicas y comparativas",
    icon: Activity,
    accent: "border-teal-300/16 bg-teal-300/[0.075] text-teal-200",
    accessTier: "premium",
    layers: [
      { id: "qualityLife", label: "Calidad de vida" },
      { id: "perceivedSafetyPotential", label: "Potencial de seguridad percibida", proFuture: true, accessTier: "pro" },
      { id: "noiseExposurePotential", label: "Exposición potencial al ruido", proFuture: true, accessTier: "pro" },
      { id: "airQualityPotential", label: "Potencial de calidad del aire", future: true, accessTier: "pro" },
    ],
  },
  {
    key: "socioeconomicIntelligence",
    title: "Inteligencia socioeconómica",
    description: "Estructura socioeconómica y presión estructural",
    icon: Network,
    accent: "border-orange-300/16 bg-orange-300/[0.075] text-orange-300",
    accessTier: "premium",
    layers: [
      { id: "socialDevelopment", label: "Desarrollo social" },
      { id: "productivePotential", label: "Potencial productivo" },
    ],
  },
  {
    key: "electoralForecasting",
    title: "Previsión electoral",
    description: "Comportamiento electoral y modelización predictiva",
    icon: BriefcaseBusiness,
    accent: "border-blue-300/16 bg-blue-300/[0.075] text-blue-300",
    accessTier: "premium",
    layers: [
      { id: "campaignBuilder", label: "Constructor de campaña 🔒" },
    ],
  },
  {
    key: "oraculum",
    title: "Oraculum ✦",
    description: "Encuestas, seguimiento y validación de modelos",
    icon: Crosshair,
    accent: "border-yellow-300/16 bg-yellow-300/[0.075] text-yellow-300",
    accessTier: "pro",
    layers: [
      { id: "targetedPolling", label: "Encuestas dirigidas", future: true },
      { id: "modelValidation", label: "Validación del modelo", future: true },
    ],
  },
  {
    key: "narrativeIntelligence",
    title: "Inteligencia narrativa ✦",
    description: "Mensajes, ROI e impacto comunicativo",
    icon: MessageSquare,
    accent: "border-pink-300/16 bg-pink-300/[0.075] text-pink-300",
    accessTier: "pro",
    layers: [
      { id: "communicationRoadmap", label: "Hoja de ruta comunicativa", future: true },
      { id: "messageKpis", label: "KPIs de mensaje", future: true },
      { id: "roiMeasurement", label: "Medición de ROI", future: true },
    ],
  },
];

const territorialDataSubItems: TerritorialSubItem[] = [
  { id: "population", layer: "population", label: "Población", icon: Users },
  { id: "ageStructure", layer: "ageStructure", label: "Estructura de edad", icon: Scaling },
  { id: "incomeLevel", layer: "incomeLevel", label: "Nivel de renta", icon: Database },
  { id: "electoralResults", layer: "electoralBehavior", label: "Resultados electorales", icon: ReceiptText },
  { id: "landBuiltEnvironment", layer: "landBuiltEnvironment", label: "Territorio / entorno construido", icon: Map },
];

const landBuiltEnvironmentSubLayers: { id: LandBuiltEnvironmentMetricKey; label: string }[] = [
  { id: "populationDensity", label: "Densidad de población" },
  { id: "parcelDensity", label: "Densidad parcelaria" },
  { id: "builtFootprint", label: "Huella construida" },
  { id: "avgPlotSize", label: "Tamaño medio de parcela" },
  { id: "buildingIntensity", label: "Intensidad edificatoria" },
  { id: "urbanIntensity", label: "Intensidad urbana" },
];

const housingSubLayerIcons: Partial<Record<string, typeof Users>> = {
  qualityLife: Activity,
  perceivedSafetyPotential: Crown,
  noiseExposurePotential: RadioTower,
  airQualityPotential: Globe2,
};

const electionTypeLabels: Record<ElectionType, string> = {
  municipales: "Municipal",
  andaluzas: "Autonómica",
  congreso: "Nacional",
  europeas: "Europea",
};

function getLatestAvailableContest(group: ElectionGroup) {
  for (let index = group.contests.length - 1; index >= 0; index -= 1) {
    const contest = group.contests[index];
    if (contest.available) {
      return contest;
    }
  }

  return null;
}

function getSelectedContest(contestId: ElectionContest["id"]) {
  return electionContests.find((contest) => contest.id === contestId) ?? electionContests[0];
}

function LockedTooltip({ label = "Capa Premium" }: { label?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-[#070b14]/95 px-3 py-2 text-xs font-medium text-slate-200 shadow-[0_16px_40px_rgba(0,0,0,0.36)]">
      {label}
    </div>
  );
}

function AccessTierIcon({ tier, className = "h-[11px] w-[11px]" }: { tier?: CategoryModel["accessTier"]; className?: string }) {
  if (tier === "pro") {
    return <Sparkles className={`${className} text-yellow-300/75`} />;
  }

  if (tier === "premium") {
    return <LockKeyhole className={className} />;
  }

  return null;
}

export function LeftSidebar() {
  const layers = useDashboardStore((state) => state.layers);
  const activeLayer = useDashboardStore((state) => state.activeLayer);
  const activeSubLayer = useDashboardStore((state) => state.activeSubLayer);
  const landBuiltEnvironmentMetric = useDashboardStore((state) => state.landBuiltEnvironmentMetric);
  const territorialMetric = useDashboardStore((state) => state.territorialMetric);
  const socioeconomicMetric = useDashboardStore((state) => state.socioeconomicMetric);
  const campaignForecastMetric = useDashboardStore((state) => state.campaignForecastMetric);
  const expandedCategories = useDashboardStore((state) => state.expandedCategories);
  const toggleCategory = useDashboardStore((state) => state.toggleCategory);
  const selectLayer = useDashboardStore((state) => state.selectLayer);
  const setLandBuiltEnvironmentMetric = useDashboardStore((state) => state.setLandBuiltEnvironmentMetric);
  const setTerritorialMetric = useDashboardStore((state) => state.setTerritorialMetric);
  const setSocioeconomicMetric = useDashboardStore((state) => state.setSocioeconomicMetric);
  const setCampaignForecastMetric = useDashboardStore((state) => state.setCampaignForecastMetric);
  const setProductivePotentialVariable = useDashboardStore((state) => state.setProductivePotentialVariable);
  const setSocioeconomicView = useDashboardStore((state) => state.setSocioeconomicView);
  const filters = useDashboardStore((state) => state.filters);
  const setFilter = useDashboardStore((state) => state.setFilter);
  const setSelectedSection = useDashboardStore((state) => state.setSelectedSection);

  const selectedContest = getSelectedContest(filters.electionContestId);

  return (
    <Panel className="flex h-auto min-h-fit flex-col overflow-visible rounded-[1.45rem] border-white/[0.08] bg-[linear-gradient(180deg,rgba(8,15,26,0.97),rgba(5,10,18,0.97))] p-2.5 shadow-[0_28px_90px_rgba(0,0,0,0.32)]">
      <div className="pb-2.5">
        <p className="text-[0.64rem] font-semibold uppercase tracking-[0.32em] text-slate-500">
          Inteligencia
        </p>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <p className="text-[0.64rem] font-semibold uppercase tracking-[0.32em] text-slate-500">
          Capas
        </p>
        <span className="text-[0.7rem] text-slate-500">Métrica activa única</span>
      </div>

      <div className="space-y-1.5 pr-0">
        {categories.map((category) =>
          category.key === "territorialData" ? (
            <TerritorialDataCard
              key={category.key}
              category={category}
              expanded={expandedCategories.territorialData}
              layers={layers}
              activeLayer={activeLayer}
              activeSubLayer={activeSubLayer}
              populationYear={filters.populationYear}
              ageStructureYear={filters.ageStructureYear}
              incomeYear={filters.incomeYear}
              selectedContest={selectedContest}
              landBuiltEnvironmentMetric={landBuiltEnvironmentMetric}
              onToggle={() => toggleCategory("territorialData")}
              onSelectLayer={(layer, subLayer) => {
                const landMetric =
                  layer === "landBuiltEnvironment" && subLayer !== "landBuiltEnvironment"
                    ? (subLayer as LandBuiltEnvironmentMetricKey | undefined) ?? "populationDensity"
                    : "populationDensity";
                selectLayer(layer, subLayer);
                if (layer === "landBuiltEnvironment") {
                  setLandBuiltEnvironmentMetric(landMetric);
                }
              }}
              onSetFilter={setFilter}
              onSelectContest={(contest) => {
                setSelectedSection("");
                setFilter("electionContestId", contest.id);
                setFilter("year", contest.year);
              }}
            />
          ) : (
            <PremiumCategoryCard
              key={category.key}
              category={category}
              expanded={expandedCategories[category.key]}
              activeLayer={activeLayer}
              activeSubLayer={activeSubLayer}
              activeMetric={
                category.key === "socioeconomicIntelligence"
                  ? socioeconomicMetric
                  : category.key === "electoralForecasting"
                    ? campaignForecastMetric
                    : territorialMetric
              }
              onToggle={() => {
                if (category.key === "socioeconomicIntelligence") {
                  setSocioeconomicView(SOCIAL_DEVELOPMENT_UI_YEAR);
                  setSocioeconomicMetric("humanCapital");
                  selectLayer("socioeconomicIntelligence", "socialDevelopment");
                  return;
                }
                if (category.key === "electoralForecasting") {
                  setCampaignForecastMetric("swingSections");
                  selectLayer("electoralForecasting", "campaignBuilder");
                  return;
                }
                toggleCategory(category.key);
              }}
              onSelectLayer={(metric) => {
                if (category.key === "socioeconomicIntelligence") {
                  if (metric === "productivePotential") {
                    setProductivePotentialVariable("educationLevel");
                  }
                  setSocioeconomicMetric(metric === "productivePotential" ? "inequalityPressure" : "humanCapital");
                  selectLayer("socioeconomicIntelligence", metric);
                  return;
                }
                if (category.key === "electoralForecasting") {
                  setCampaignForecastMetric("swingSections");
                  selectLayer("electoralForecasting", metric);
                  return;
                }

                setTerritorialMetric(metric as TerritorialMetricKey);
                selectLayer("housingIntelligence", metric);
              }}
            />
          ),
        )}
      </div>

      <div className="mt-2.5 border-t border-white/[0.07] pt-2">
        <HoverTooltip
          content={
            <div className="rounded-2xl border border-white/10 bg-[#070b14]/95 p-4 text-left shadow-[0_22px_60px_rgba(0,0,0,0.42)] backdrop-blur-xl">
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-cyan-200">
                Próximas capas
              </p>
              <p className="mt-2 max-w-[14rem] text-xs leading-5 text-slate-400">
                Nuevos módulos de datos aparecerán aquí a medida que crezca el catálogo Freemium.
              </p>
            </div>
          }
        >
          <button
            type="button"
            className="flex h-8.5 w-full items-center justify-center gap-1.5 rounded-2xl border border-white/[0.11] bg-white/[0.045] text-[0.78rem] font-semibold text-slate-100 transition hover:border-cyan-300/20 hover:bg-white/[0.07]"
          >
            <Layers3 className="h-3.5 w-3.5" />
            <span>+ Añadir capa</span>
          </button>
        </HoverTooltip>

        <div className="mt-2 flex items-center justify-center gap-9 text-[0.68rem] text-slate-500">
          <span className="inline-flex items-center gap-2">
            <LockKeyhole className="h-3 w-3" />
            Premium
          </span>
          <span className="inline-flex items-center gap-2">
            <Sparkles className="h-3 w-3" />
            Pro
          </span>
        </div>
      </div>
    </Panel>
  );
}

function TerritorialDataCard({
  category,
  expanded,
  layers,
  activeLayer,
  activeSubLayer,
  populationYear,
  ageStructureYear,
  incomeYear,
  selectedContest,
  landBuiltEnvironmentMetric,
  onToggle,
  onSelectLayer,
  onSetFilter,
  onSelectContest,
}: {
  category: CategoryModel;
  expanded: boolean;
  layers: Record<LayerKey, boolean>;
  activeLayer: LayerKey;
  activeSubLayer: string | null;
  populationYear: string;
  ageStructureYear: string;
  incomeYear: string;
  selectedContest: ElectionContest;
  landBuiltEnvironmentMetric: LandBuiltEnvironmentMetricKey;
  onToggle: () => void;
  onSelectLayer: (layer: LayerKey, subLayer?: string) => void;
  onSetFilter: (
    key: "year" | "electionContestId" | "populationYear" | "ageStructureYear" | "incomeYear" | "ageGroup" | "compare",
    value: string,
  ) => void;
  onSelectContest: (contest: ElectionContest) => void;
}) {
  const Icon = category.icon;

  return (
    <article
      className={`rounded-[1.15rem] border p-2 transition duration-200 ${
        expanded
          ? "border-cyan-300/15 bg-[linear-gradient(145deg,rgba(13,32,42,0.72),rgba(13,20,32,0.92))] shadow-[0_0_34px_rgba(45,212,191,0.045)]"
          : "border-white/[0.08] bg-white/[0.035] hover:border-cyan-300/14"
      }`}
    >
      <CategoryHeader category={category} expanded={expanded} onToggle={onToggle} />

      {expanded ? (
        <div className="mt-2 space-y-1.5">
          {territorialDataSubItems.map((item) => {
            const selected = layers[item.layer] || activeLayer === item.layer;
            const submenuOpen =
              activeSubLayer === item.id ||
              (item.layer === "landBuiltEnvironment" && activeLayer === "landBuiltEnvironment");

            return (
              <TerritorialSubItemRow
                key={item.id}
                item={item}
                selected={selected}
                submenuOpen={submenuOpen}
                onClick={() => onSelectLayer(item.layer, item.id)}
              >
                {item.layer === "population" && submenuOpen ? (
                  <YearChipGroup
                    years={populationYears}
                    activeYear={populationYear}
                    onSelect={(year) => onSetFilter("populationYear", year)}
                  />
                ) : null}
                {item.layer === "ageStructure" && submenuOpen ? (
                  <YearChipGroup
                    years={ageStructureYears}
                    activeYear={ageStructureYear}
                    onSelect={(year) => onSetFilter("ageStructureYear", year)}
                  />
                ) : null}
                {item.layer === "incomeLevel" && submenuOpen ? (
                  <YearChipGroup
                    years={incomeYears}
                    activeYear={incomeYear}
                    onSelect={(year) => onSetFilter("incomeYear", year)}
                  />
                ) : null}
                {item.layer === "electoralBehavior" && submenuOpen ? (
                  <ElectoralResultsSubmenu selectedContest={selectedContest} onSelectContest={onSelectContest} />
                ) : null}
                {item.layer === "landBuiltEnvironment" && submenuOpen ? (
                  <MetricChipGroup
                    items={landBuiltEnvironmentSubLayers}
                    activeId={landBuiltEnvironmentMetric}
                    onSelect={(metric) => onSelectLayer("landBuiltEnvironment", metric)}
                  />
                ) : null}
              </TerritorialSubItemRow>
            );
          })}
        </div>
      ) : null}
    </article>
  );
}

function CategoryHeader({
  category,
  expanded,
  onToggle,
}: {
  category: CategoryModel;
  expanded: boolean;
  onToggle: () => void;
}) {
  const Icon = category.icon;

  return (
    <button type="button" onClick={onToggle} className="flex min-h-[3.35rem] w-full items-center gap-2 text-left">
      <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-[0.85rem] border ${category.accent}`}>
        <Icon className="h-[15px] w-[15px]" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[0.8rem] font-semibold leading-4 text-slate-50">{category.title}</p>
        <p className="mt-0.5 text-[0.66rem] leading-[0.95rem] text-slate-500">{category.description}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2 text-slate-500">
        <AccessTierIcon tier={category.accessTier} />
        <ChevronDown className={`h-3.5 w-3.5 transition ${expanded ? "rotate-180 text-cyan-200" : ""}`} />
      </div>
    </button>
  );
}

function PremiumCategoryCard({
  category,
  expanded,
  activeLayer,
  activeSubLayer,
  activeMetric,
  onToggle,
  onSelectLayer,
}: {
  category: CategoryModel;
  expanded: boolean;
  activeLayer: LayerKey;
  activeSubLayer: string | null;
  activeMetric: TerritorialMetricKey | SocioeconomicMetricKey | CampaignForecastMetricKey;
  onToggle: () => void;
  onSelectLayer: (metric: TerritorialMetricKey | SocioeconomicMetricKey | CampaignForecastMetricKey | string) => void;
}) {
  const layerKey =
    category.key === "socioeconomicIntelligence"
      ? "socioeconomicIntelligence"
      : category.key === "electoralForecasting"
        ? "electoralForecasting"
        : "housingIntelligence";
  return (
    <article className="rounded-[1.15rem] border border-white/[0.08] bg-white/[0.035] p-2 transition duration-200 hover:border-white/[0.12] hover:bg-white/[0.045]">
      <CategoryHeader category={category} expanded={expanded} onToggle={onToggle} />

      {expanded ? (
        <div className="mt-3 space-y-1.5 rounded-2xl border border-white/[0.05] bg-[#08111d]/72 p-1.5">
          {(category.layers ?? []).map((layer) => {
            const layerAccessTier = layer.accessTier ?? category.accessTier;
            const isDisabled = Boolean(layer.future || layer.proFuture || category.accessTier === "pro");
            const isProFuture = layerAccessTier === "pro";
            const LayerIcon =
              category.key === "housingIntelligence"
                ? housingSubLayerIcons[layer.id] ?? BarChart3
                : category.key === "electoralForecasting"
                  ? Target
                  : Network;
            const isActive = activeLayer === layerKey && (activeSubLayer === layer.id || activeMetric === layer.id);

            return (
              <HoverTooltip
                key={layer.id}
                content={<LockedTooltip label={isProFuture ? "Capa Pro" : isDisabled ? "Próximamente" : "Capa Premium"} />}
                tooltipClassName="w-max min-w-[7rem]"
              >
                <button
                  type="button"
                  aria-disabled={isDisabled ? "true" : undefined}
                  disabled={isDisabled}
                  onClick={() => onSelectLayer(layer.id)}
                  className={`flex min-h-11 w-full items-center justify-between gap-3 rounded-[0.95rem] border px-3 py-2 text-left text-xs font-semibold transition ${
                    isActive
                      ? category.key === "socioeconomicIntelligence"
                        ? "border-cyan-300/18 bg-cyan-300/[0.085] text-cyan-100 shadow-[0_0_24px_rgba(34,211,238,0.045)]"
                        : "border-violet-300/20 bg-violet-300/[0.095] text-violet-100 shadow-[0_0_24px_rgba(167,139,250,0.055)]"
                      : isDisabled
                        ? isProFuture
                          ? "cursor-not-allowed border-yellow-300/[0.08] bg-yellow-300/[0.035] text-slate-500 opacity-70"
                          : "cursor-not-allowed border-white/[0.045] bg-white/[0.025] text-slate-500 opacity-75"
                        : "border-white/[0.055] bg-white/[0.025] text-slate-300 hover:border-violet-300/14 hover:bg-violet-300/[0.045] hover:text-slate-100"
                  }`}
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    <span
                      className={`grid h-7 w-7 shrink-0 place-items-center rounded-[0.75rem] border ${
                        category.key === "socioeconomicIntelligence"
                          ? "border-cyan-300/12 bg-cyan-300/[0.055] text-cyan-200"
                          : "border-violet-300/14 bg-violet-300/[0.065] text-violet-200"
                      }`}
                    >
                      <LayerIcon className="h-3.5 w-3.5" strokeWidth={1.8} />
                    </span>
                    <span className="truncate">{layer.label}</span>
                  </span>
                  <AccessTierIcon
                    tier={layerAccessTier}
                    className={`h-3.5 w-3.5 shrink-0 ${isProFuture ? "text-yellow-300/70" : "text-slate-600"}`}
                  />
                </button>
              </HoverTooltip>
            );
          })}
        </div>
      ) : null}
    </article>
  );
}

function TerritorialSubItemRow({
  item,
  selected,
  submenuOpen,
  onClick,
  children,
}: {
  item: TerritorialSubItem;
  selected: boolean;
  submenuOpen: boolean;
  onClick: () => void;
  children?: React.ReactNode;
}) {
  const Icon = item.icon;
  const hasSubmenu = true;

  return (
    <div
      className={`overflow-visible rounded-2xl border transition duration-200 ${
        selected
          ? "border-cyan-300/16 bg-[linear-gradient(135deg,rgba(26,54,64,0.72),rgba(15,28,40,0.78))]"
          : "border-white/[0.055] bg-white/[0.045] hover:border-cyan-300/12 hover:bg-white/[0.06]"
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        className="flex h-[2.65rem] w-full items-center gap-2 px-2 text-left"
      >
        <Icon className={`h-[15px] w-[15px] shrink-0 ${selected ? "text-cyan-200" : "text-cyan-300"}`} />
        <span className="min-w-0 flex-1 truncate text-[0.76rem] font-semibold text-slate-100">
          {item.label}
        </span>
        {hasSubmenu && submenuOpen ? (
          <ChevronDown className="h-3 w-3 shrink-0 text-cyan-300" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0 text-slate-400" />
        )}
      </button>
      {submenuOpen && children ? (
        <div className="border-t border-white/[0.045] bg-[#07111d]/38 pb-2.5 pl-2.5 pr-1.5 pt-1.5">
          {children}
        </div>
      ) : null}
    </div>
  );
}

function YearChipGroup({
  years,
  activeYear,
  onSelect,
}: {
  years: readonly string[];
  activeYear: string;
  onSelect: (year: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {years.map((year) => (
        <button
          key={year}
          type="button"
          onClick={() => onSelect(year)}
          className={`h-6.5 rounded-[0.6rem] border px-1.5 text-[0.64rem] font-semibold transition ${
            activeYear === year
              ? "border-cyan-300/70 bg-cyan-300/[0.12] text-cyan-50 shadow-[0_0_18px_rgba(45,212,191,0.12)]"
              : "border-white/[0.08] bg-white/[0.025] text-slate-400 hover:border-white/[0.14] hover:bg-white/[0.045] hover:text-slate-200"
          }`}
        >
          {year}
        </button>
      ))}
    </div>
  );
}

function MetricChipGroup<T extends string>({
  items,
  activeId,
  onSelect,
}: {
  items: { id: T; label: string }[];
  activeId: T;
  onSelect: (id: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onSelect(item.id)}
          className={`h-6.5 rounded-[0.6rem] border px-1.5 text-[0.64rem] font-semibold transition ${
            activeId === item.id
              ? "border-cyan-300/70 bg-cyan-300/[0.12] text-cyan-50 shadow-[0_0_18px_rgba(45,212,191,0.12)]"
              : "border-white/[0.08] bg-white/[0.025] text-slate-400 hover:border-white/[0.14] hover:bg-white/[0.045] hover:text-slate-200"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function ElectoralResultsSubmenu({
  selectedContest,
  onSelectContest,
}: {
  selectedContest: ElectionContest;
  onSelectContest: (contest: ElectionContest) => void;
}) {
  const selectedGroup =
    electionGroups.find((group) => group.type === selectedContest.type) ?? electionGroups[0];

  return (
    <div className="space-y-2.5">
      <div>
        <p className="mb-1.5 text-[0.68rem] font-medium text-cyan-300">Type of election</p>
        <div className="flex flex-wrap gap-1.5">
          {electionGroups.map((group) => {
            const latestContest = getLatestAvailableContest(group);
            const selected = group.type === selectedContest.type;

            return (
              <button
                key={group.type}
                type="button"
                disabled={!latestContest}
                onClick={() => latestContest && onSelectContest(latestContest)}
                className={`h-6.5 rounded-[0.6rem] border px-1.5 text-[0.64rem] font-semibold transition ${
                  selected
                    ? "border-cyan-300/70 bg-cyan-300/[0.12] text-cyan-50 shadow-[0_0_18px_rgba(45,212,191,0.12)]"
                    : latestContest
                      ? "border-white/[0.08] bg-white/[0.025] text-slate-400 hover:border-white/[0.14] hover:bg-white/[0.045] hover:text-slate-200"
                      : "cursor-not-allowed border-white/[0.05] bg-white/[0.02] text-slate-600"
                }`}
              >
                {electionTypeLabels[group.type]}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <p className="mb-1.5 text-[0.68rem] font-medium text-cyan-300">Year</p>
        <div className="flex flex-wrap gap-1.5">
          {selectedGroup.contests.map((contest) => {
            const selected = selectedContest.id === contest.id;
            const button = (
              <button
                key={contest.id}
                type="button"
                disabled={!contest.available}
                onClick={() => contest.available && onSelectContest(contest)}
                className={`h-6.5 rounded-[0.6rem] border px-1.5 text-[0.64rem] font-semibold transition ${
                  selected
                    ? "border-cyan-300/70 bg-cyan-300/[0.12] text-cyan-50 shadow-[0_0_18px_rgba(45,212,191,0.12)]"
                    : contest.available
                      ? "border-white/[0.08] bg-white/[0.025] text-slate-400 hover:border-white/[0.14] hover:bg-white/[0.045] hover:text-slate-200"
                      : "cursor-not-allowed border-white/[0.05] bg-white/[0.02] text-slate-600 opacity-60"
                }`}
              >
                {contest.label}
              </button>
            );

            if (contest.available || !contest.disabledReason) {
              return button;
            }

            return (
              <HoverTooltip
                key={contest.id}
                content={<LockedTooltip label={disabledTooltip[contest.disabledReason]} />}
                tooltipClassName="w-max min-w-[8rem]"
              >
                {button}
              </HoverTooltip>
            );
          })}
        </div>
      </div>
    </div>
  );
}
