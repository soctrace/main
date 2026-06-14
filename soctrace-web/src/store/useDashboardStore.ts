import { create } from "zustand";
import { normalizeSectionId } from "@/lib/sectionIdentity";
import { defaultElectionContestId, SOCIAL_DEVELOPMENT_UI_YEAR } from "@/types/api";
import type { AskSocTraceResponse } from "@/features/ask-soctrace/types";
import type {
  DataSourceMode,
  ActiveSubLayer,
  LayerCategory,
  LayerKey,
  MunicipalitySummary,
  MunicipalityAgeStructureSummary,
  MunicipalityIncomeSummary,
  MunicipalityPopulationSummary,
  SectionDetail,
  SectionFeature,
  SectionFeatureCollection,
  StatusTone,
  CampaignForecastMetricKey,
  LandBuiltEnvironmentMetricKey,
  RealEstateMetricKey,
  SocioeconomicMetricKey,
  SocioeconomicYear,
  ProductivePotentialVariableKey,
  TerritorialMetricKey,
  ElectionContestId,
} from "@/types/api";

type DetailTab = "overview" | "demographics" | "electoral";
type MapMode = "map" | "satellite";
type SocioeconomicView = SocioeconomicYear;
type RightPanelMode = "default" | "askTests" | "askChart";

type HoverState = {
  id: string;
  x: number;
  y: number;
};

const latestAvailablePopulationYear = "2025";

const absoluteDashboardState = {
  selectedSectionId: "",
  hoveredSectionId: null,
  hoverState: null,
  detailTab: "overview" as DetailTab,
  layers: {
    population: true,
    ageStructure: false,
    foreignBorn: false,
    incomeLevel: false,
    electoralBehavior: false,
    landBuiltEnvironment: false,
    housingIntelligence: false,
    socioeconomicIntelligence: false,
    electoralForecasting: false,
  },
  activeCategory: "territorialData" as LayerCategory,
  expandedCategories: {
    territorialData: true,
    housingIntelligence: false,
    socioeconomicIntelligence: false,
    electoralForecasting: false,
    oraculum: false,
    narrativeIntelligence: false,
  },
  activeLayer: "population" as LayerKey,
  activeSubLayer: "population" as ActiveSubLayer,
  landBuiltEnvironmentMetric: "populationDensity" as LandBuiltEnvironmentMetricKey,
  socioeconomicView: SOCIAL_DEVELOPMENT_UI_YEAR as SocioeconomicView,
  campaignForecastMetric: "swingSections" as CampaignForecastMetricKey,
  productivePotentialVariable: "educationLevel" as ProductivePotentialVariableKey,
  filters: {
    year: latestAvailablePopulationYear,
    electionContestId: defaultElectionContestId,
    populationYear: latestAvailablePopulationYear,
    ageStructureYear: "2025",
    incomeYear: "2023",
    socioeconomicYear: SOCIAL_DEVELOPMENT_UI_YEAR,
    ageGroup: "All",
    compare: "",
  },
};

function clearSelectedSectionAndShowMunicipality() {
  return {
    selectedSectionId: "",
    hoveredSectionId: null,
    hoverState: null,
    detailTab: "overview" as DetailTab,
  };
}

type DashboardStore = {
  selectedMunicipality: string;
  selectedMunicipalityId: string;
  selectedSectionId: string;
  hoveredSectionId: string | null;
  hoverState: HoverState | null;
  mapMode: MapMode;
  detailTab: DetailTab;
  aiInput: string;
  queuedAskPrompt: string | null;
  rightPanelMode: RightPanelMode;
  askChartResponse: AskSocTraceResponse | null;
  municipalities: MunicipalitySummary[];
  sectionCollection: SectionFeatureCollection | null;
  sectionFeatureById: Record<string, SectionFeature>;
  sectionDetailsById: Record<string, SectionDetail>;
  municipalityPopulationByYear: Record<string, MunicipalityPopulationSummary>;
  municipalityAgeStructureByYear: Record<string, MunicipalityAgeStructureSummary>;
  municipalityIncomeByYear: Record<string, MunicipalityIncomeSummary>;
  electoralCollectionsByContest: Partial<Record<ElectionContestId, SectionFeatureCollection>>;
  isMapLoading: boolean;
  isDetailLoading: boolean;
  dataSource: DataSourceMode;
  statusMessage: string | null;
  statusTone: StatusTone | null;
  error: string | null;
  layers: Record<LayerKey, boolean>;
  activeCategory: LayerCategory;
  expandedCategories: Record<LayerCategory, boolean>;
  activeLayer: LayerKey;
  activeSubLayer: ActiveSubLayer;
  realEstateMetric: RealEstateMetricKey;
  landBuiltEnvironmentMetric: LandBuiltEnvironmentMetricKey;
  territorialMetric: TerritorialMetricKey;
  socioeconomicMetric: SocioeconomicMetricKey;
  socioeconomicView: SocioeconomicView;
  campaignForecastMetric: CampaignForecastMetricKey;
  productivePotentialVariable: ProductivePotentialVariableKey;
  filters: {
    year: string;
    electionContestId: ElectionContestId;
    populationYear: string;
    ageStructureYear: string;
    incomeYear: string;
    socioeconomicYear: string;
    ageGroup: string;
    compare: string;
  };
  setMunicipality: (value: { id: string; name: string }) => void;
  setMunicipalities: (items: MunicipalitySummary[]) => void;
  setSectionCollection: (collection: SectionFeatureCollection | null) => void;
  setSelectedSection: (sectionId: string | null) => void;
  setSectionDetail: (sectionId: string, detail: SectionDetail) => void;
  setMunicipalityPopulationSummaries: (items: MunicipalityPopulationSummary[]) => void;
  setMunicipalityAgeStructureSummaries: (items: MunicipalityAgeStructureSummary[]) => void;
  setMunicipalityIncomeSummaries: (items: MunicipalityIncomeSummary[]) => void;
  setElectoralContestCollection: (
    contestId: ElectionContestId,
    collection: SectionFeatureCollection,
  ) => void;
  setHoveredSection: (sectionId: string | null, point?: { x: number; y: number }) => void;
  clearSelectedSectionAndShowMunicipality: () => void;
  resetDashboardToAbsolutePosition: () => void;
  toggleLayer: (layer: LayerKey) => void;
  selectLayer: (layer: LayerKey, subLayer?: ActiveSubLayer) => void;
  toggleCategory: (category: LayerCategory) => void;
  setExpandedCategory: (category: LayerCategory, expanded: boolean) => void;
  setRealEstateMetric: (metric: RealEstateMetricKey) => void;
  setLandBuiltEnvironmentMetric: (metric: LandBuiltEnvironmentMetricKey) => void;
  setTerritorialMetric: (metric: TerritorialMetricKey) => void;
  setSocioeconomicMetric: (metric: SocioeconomicMetricKey) => void;
  setSocioeconomicView: (view: SocioeconomicView) => void;
  setCampaignForecastMetric: (metric: CampaignForecastMetricKey) => void;
  setProductivePotentialVariable: (variable: ProductivePotentialVariableKey) => void;
  setFilter: (key: "year" | "electionContestId" | "populationYear" | "ageStructureYear" | "incomeYear" | "socioeconomicYear" | "ageGroup" | "compare", value: string) => void;
  setAiInput: (value: string) => void;
  queueAskPrompt: (prompt: string) => void;
  clearQueuedAskPrompt: () => void;
  setRightPanelMode: (mode: RightPanelMode) => void;
  setAskChartResponse: (response: AskSocTraceResponse | null) => void;
  setDetailTab: (tab: DetailTab) => void;
  setMapMode: (mode: MapMode) => void;
  setMapLoading: (value: boolean) => void;
  setDetailLoading: (value: boolean) => void;
  setDataSource: (value: DataSourceMode) => void;
  setStatus: (message: string | null, tone?: StatusTone | null) => void;
  setError: (value: string | null) => void;
};

export const useDashboardStore = create<DashboardStore>((set) => ({
  selectedMunicipality: "Mijas",
  selectedMunicipalityId: "29070",
  selectedSectionId: absoluteDashboardState.selectedSectionId,
  hoveredSectionId: absoluteDashboardState.hoveredSectionId,
  hoverState: absoluteDashboardState.hoverState,
  mapMode: "map",
  detailTab: absoluteDashboardState.detailTab,
  aiInput: "",
  queuedAskPrompt: null,
  rightPanelMode: "default",
  askChartResponse: null,
  municipalities: [],
  sectionCollection: null,
  sectionFeatureById: {},
  sectionDetailsById: {},
  municipalityPopulationByYear: {},
  municipalityAgeStructureByYear: {},
  municipalityIncomeByYear: {},
  electoralCollectionsByContest: {},
  isMapLoading: false,
  isDetailLoading: false,
  dataSource: "api",
  statusMessage: null,
  statusTone: null,
  error: null,
  layers: absoluteDashboardState.layers,
  activeCategory: absoluteDashboardState.activeCategory,
  expandedCategories: absoluteDashboardState.expandedCategories,
  activeLayer: absoluteDashboardState.activeLayer,
  activeSubLayer: absoluteDashboardState.activeSubLayer,
  realEstateMetric: "marketCadastreRatio",
  landBuiltEnvironmentMetric: absoluteDashboardState.landBuiltEnvironmentMetric,
  territorialMetric: "qualityLife",
  socioeconomicMetric: "humanCapital",
  socioeconomicView: absoluteDashboardState.socioeconomicView,
  campaignForecastMetric: absoluteDashboardState.campaignForecastMetric,
  productivePotentialVariable: "educationLevel",
  filters: absoluteDashboardState.filters,
  setMunicipality: (value) =>
    set({
      selectedMunicipality: value.name,
      selectedMunicipalityId: value.id,
      selectedSectionId: "",
      sectionDetailsById: {},
    }),
  setMunicipalities: (items) =>
    set((state) => {
      if (state.selectedMunicipalityId || items.length === 0) {
        return { municipalities: items };
      }

      return {
        municipalities: items,
        selectedMunicipalityId: items[0].municipality_id,
        selectedMunicipality: items[0].name,
      };
    }),
  setSectionCollection: (collection) =>
    set((state) => {
      if (!collection) {
        return {
          sectionCollection: null,
          sectionFeatureById: {},
          selectedSectionId: "",
        };
      }

      const sectionFeatureById = Object.fromEntries(
        collection.features.map((feature) => [
          normalizeSectionId(feature.properties.section_id),
          feature,
        ]),
      );
      const normalizedSelectedSectionId = state.selectedSectionId
        ? normalizeSectionId(state.selectedSectionId)
        : "";
      const nextSelectedSectionId =
        normalizedSelectedSectionId && sectionFeatureById[normalizedSelectedSectionId]
          ? normalizedSelectedSectionId
          : "";
      const municipalityName =
        collection.features[0]?.properties.municipality ?? state.selectedMunicipality;

      return {
        sectionCollection: collection,
        sectionFeatureById,
        selectedSectionId: nextSelectedSectionId,
        selectedMunicipality: municipalityName,
      };
    }),
  setSelectedSection: (sectionId) => set({ selectedSectionId: sectionId ? normalizeSectionId(sectionId) : "" }),
  setSectionDetail: (sectionId, detail) =>
    set((state) => ({
      sectionDetailsById: {
        ...state.sectionDetailsById,
        [sectionId]: detail,
      },
    })),
  setMunicipalityPopulationSummaries: (items) =>
    set((state) => ({
      municipalityPopulationByYear: {
        ...state.municipalityPopulationByYear,
        ...Object.fromEntries(items.map((item) => [String(item.year), item])),
      },
    })),
  setMunicipalityAgeStructureSummaries: (items) =>
    set((state) => ({
      municipalityAgeStructureByYear: {
        ...state.municipalityAgeStructureByYear,
        ...Object.fromEntries(items.map((item) => [String(item.year), item])),
      },
    })),
  setMunicipalityIncomeSummaries: (items) =>
    set((state) => ({
      municipalityIncomeByYear: {
        ...state.municipalityIncomeByYear,
        ...Object.fromEntries(items.map((item) => [String(item.year), item])),
      },
    })),
  setElectoralContestCollection: (contestId, collection) =>
    set((state) => ({
      electoralCollectionsByContest: {
        ...state.electoralCollectionsByContest,
        [contestId]: collection,
      },
    })),
  setHoveredSection: (sectionId, point) =>
    set({
      hoveredSectionId: sectionId,
      hoverState:
        sectionId && point
          ? {
              id: sectionId,
              x: point.x,
              y: point.y,
            }
          : null,
    }),
  clearSelectedSectionAndShowMunicipality: () => set(clearSelectedSectionAndShowMunicipality()),
  resetDashboardToAbsolutePosition: () =>
    set(() => ({
      ...absoluteDashboardState,
      rightPanelMode: "default",
      askChartResponse: null,
      layers: { ...absoluteDashboardState.layers },
      expandedCategories: { ...absoluteDashboardState.expandedCategories },
      filters: { ...absoluteDashboardState.filters },
      productivePotentialVariable: absoluteDashboardState.productivePotentialVariable,
    })),
  toggleLayer: (layer) =>
    set((state) => {
      const nextEnabled = !state.layers[layer];
      return {
        ...clearSelectedSectionAndShowMunicipality(),
        layers: {
          population: false,
          ageStructure: false,
          foreignBorn: false,
          incomeLevel: false,
          electoralBehavior: false,
          landBuiltEnvironment: false,
          housingIntelligence: false,
          socioeconomicIntelligence: false,
          electoralForecasting: false,
          [layer]: nextEnabled,
        },
        activeCategory: nextEnabled
          ? layer === "housingIntelligence"
            ? "housingIntelligence"
            : layer === "socioeconomicIntelligence"
              ? "socioeconomicIntelligence"
              : layer === "electoralForecasting"
                ? "electoralForecasting"
              : "territorialData"
          : state.activeCategory,
        expandedCategories: {
          ...state.expandedCategories,
          territorialData: true,
          ...(layer === "socioeconomicIntelligence" ? { socioeconomicIntelligence: true } : {}),
          ...(layer === "housingIntelligence" ? { housingIntelligence: true } : {}),
          ...(layer === "electoralForecasting" ? { electoralForecasting: true } : {}),
        },
        activeLayer: nextEnabled ? layer : state.activeLayer,
        activeSubLayer: nextEnabled
          ? layer === "socioeconomicIntelligence"
            ? "socialDevelopment"
            : layer === "electoralForecasting"
              ? "campaignBuilder"
            : layer
          : state.activeSubLayer,
        rightPanelMode: "default",
        askChartResponse: null,
        filters: {
          ...state.filters,
          year: layer === "electoralBehavior" && nextEnabled ? "2023" : state.filters.year,
          electionContestId:
            layer === "electoralBehavior" && nextEnabled
              ? defaultElectionContestId
              : state.filters.electionContestId,
          ageStructureYear: layer === "ageStructure" && nextEnabled ? "2025" : state.filters.ageStructureYear,
          incomeYear: layer === "incomeLevel" && nextEnabled ? "2023" : state.filters.incomeYear,
          socioeconomicYear:
            layer === "socioeconomicIntelligence" && nextEnabled
              ? SOCIAL_DEVELOPMENT_UI_YEAR
              : state.filters.socioeconomicYear,
        },
        socioeconomicView:
          layer === "socioeconomicIntelligence" && nextEnabled
            ? SOCIAL_DEVELOPMENT_UI_YEAR
            : state.socioeconomicView,
      };
    }),
  selectLayer: (layer, subLayer) =>
    set((state) => {
      const nextSubLayer =
        subLayer ??
        (layer === "socioeconomicIntelligence"
          ? "socialDevelopment"
          : layer === "electoralForecasting"
            ? "campaignBuilder"
            : layer);
      const sameActiveSubLayer = state.activeLayer === layer && state.activeSubLayer === nextSubLayer;
      const switchingLayer = state.activeLayer !== layer;

      return {
        ...clearSelectedSectionAndShowMunicipality(),
        layers: {
          population: false,
          ageStructure: false,
          foreignBorn: false,
          incomeLevel: false,
          electoralBehavior: false,
          landBuiltEnvironment: false,
          housingIntelligence: false,
          socioeconomicIntelligence: false,
          electoralForecasting: false,
          [layer]: true,
        },
        activeCategory:
          layer === "housingIntelligence"
            ? "housingIntelligence"
            : layer === "socioeconomicIntelligence"
              ? "socioeconomicIntelligence"
              : layer === "electoralForecasting"
                ? "electoralForecasting"
              : "territorialData",
        expandedCategories: {
          ...state.expandedCategories,
          ...(layer === "housingIntelligence"
            ? { housingIntelligence: true }
            : layer === "socioeconomicIntelligence"
              ? { socioeconomicIntelligence: true }
              : layer === "electoralForecasting"
                ? { electoralForecasting: true }
              : { territorialData: true }),
        },
        activeLayer: layer,
        activeSubLayer:
          layer === "socioeconomicIntelligence" || layer === "electoralForecasting"
            ? nextSubLayer
            : sameActiveSubLayer
              ? null
              : nextSubLayer,
        rightPanelMode: "default",
        askChartResponse: null,
        filters: {
          ...state.filters,
          year: layer === "electoralBehavior" && switchingLayer ? "2023" : state.filters.year,
          electionContestId:
            layer === "electoralBehavior" && switchingLayer
              ? defaultElectionContestId
              : state.filters.electionContestId,
          ageStructureYear:
            layer === "ageStructure" && switchingLayer ? "2025" : state.filters.ageStructureYear,
          incomeYear: layer === "incomeLevel" && switchingLayer ? "2023" : state.filters.incomeYear,
          socioeconomicYear:
            layer === "socioeconomicIntelligence" && switchingLayer
              ? SOCIAL_DEVELOPMENT_UI_YEAR
              : state.filters.socioeconomicYear,
        },
        socioeconomicView:
          layer === "socioeconomicIntelligence" && switchingLayer
            ? SOCIAL_DEVELOPMENT_UI_YEAR
            : state.socioeconomicView,
      };
    }),
  toggleCategory: (category) =>
    set((state) => ({
      ...clearSelectedSectionAndShowMunicipality(),
      expandedCategories: {
        ...state.expandedCategories,
        [category]: !state.expandedCategories[category],
      },
    })),
  setExpandedCategory: (category, expanded) =>
    set((state) => ({
      ...clearSelectedSectionAndShowMunicipality(),
      expandedCategories: {
        ...state.expandedCategories,
        [category]: expanded,
      },
    })),
  setRealEstateMetric: (metric) => set({ ...clearSelectedSectionAndShowMunicipality(), realEstateMetric: metric }),
  setLandBuiltEnvironmentMetric: (metric) =>
    set({ ...clearSelectedSectionAndShowMunicipality(), landBuiltEnvironmentMetric: metric }),
  setTerritorialMetric: (metric) => set({ ...clearSelectedSectionAndShowMunicipality(), territorialMetric: metric }),
  setSocioeconomicMetric: (metric) =>
    set({ ...clearSelectedSectionAndShowMunicipality(), socioeconomicMetric: metric }),
  setSocioeconomicView: () =>
    set((state) => ({
      ...clearSelectedSectionAndShowMunicipality(),
      socioeconomicView: SOCIAL_DEVELOPMENT_UI_YEAR as SocioeconomicView,
      filters: {
        ...state.filters,
        socioeconomicYear: SOCIAL_DEVELOPMENT_UI_YEAR,
      },
    })),
  setCampaignForecastMetric: (metric) =>
    set({ campaignForecastMetric: metric }),
  setProductivePotentialVariable: (variable) =>
    set({ productivePotentialVariable: variable }),
  setFilter: (key, value) =>
    set((state) => ({
      ...clearSelectedSectionAndShowMunicipality(),
      filters: {
        ...state.filters,
        [key]: key === "socioeconomicYear" ? SOCIAL_DEVELOPMENT_UI_YEAR : value,
      },
    })),
  setAiInput: (value) => set({ aiInput: value }),
  queueAskPrompt: (prompt) => set({ queuedAskPrompt: prompt }),
  clearQueuedAskPrompt: () => set({ queuedAskPrompt: null }),
  setRightPanelMode: (mode) => set({ rightPanelMode: mode }),
  setAskChartResponse: (response) =>
    set({ askChartResponse: response, rightPanelMode: response ? "askChart" : "default" }),
  setDetailTab: (tab) => set({ detailTab: tab }),
  setMapMode: (mode) => set({ mapMode: mode }),
  setMapLoading: (value) => set({ isMapLoading: value }),
  setDetailLoading: (value) => set({ isDetailLoading: value }),
  setDataSource: (value) => set({ dataSource: value }),
  setStatus: (message, tone = null) => set({ statusMessage: message, statusTone: tone }),
  setError: (value) => set({ error: value }),
}));
