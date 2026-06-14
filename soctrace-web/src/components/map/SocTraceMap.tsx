import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import Map, {
  Layer,
  Source,
  type LayerProps,
  type MapLayerMouseEvent,
  type ViewStateChangeEvent,
  type MapRef,
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { Panel } from "@/components/ui/Panel";
import { MapControls } from "@/components/map/MapControls";
import { MapLegend } from "@/components/map/MapLegend";
import { SectionTooltip } from "@/components/map/SectionTooltip";
import {
  buildLandBuiltEnvironmentPresentation,
  getActiveLayer,
  getCampaignForecastLeader,
  getLayerFillExpression,
  normalizePartyName,
} from "@/lib/sectionPresentation";
import { normalizeSectionId } from "@/lib/sectionIdentity";
import { useDashboardStore } from "@/store/useDashboardStore";
import { electionContests } from "@/types/api";
import type { SectionFeature, SectionFeatureCollection } from "@/types/api";

const INITIAL_VIEW_STATE = {
  longitude: -4.6376,
  latitude: 36.5428,
  zoom: 12.25,
  bearing: 8,
  pitch: 26,
};

const BASEMAP_STYLES = {
  map: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  satellite: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
} as const;

const SOC_TRACE_BASEMAP_LAYER_IDS = {
  buildings: "soctrace-building-mass",
  roadsPrimary: "soctrace-road-primary",
  roadsSecondary: "soctrace-road-secondary",
  roadLabels: "soctrace-road-labels",
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const SCALE_BAR_MAX_WIDTH_PX = 80;
const EARTH_CIRCUMFERENCE_METERS = 40075016.686;
const NICE_SCALE_METERS = [50, 100, 200, 500, 1000, 2000, 5000, 10000];
const MUNICIPALITY_FIT_PADDING = {
  top: 18,
  bottom: 18,
  left: 18,
  right: 18,
};

const formatScaleLabel = (meters: number) =>
  meters >= 1000 ? `${meters / 1000} km` : `${meters} m`;

const getScaleFromView = (zoom: number, latitude: number) => {
  const worldSize = 512 * 2 ** zoom;
  const metersPerPixel =
    (Math.cos((latitude * Math.PI) / 180) * EARTH_CIRCUMFERENCE_METERS) / worldSize;
  const maxMeters = metersPerPixel * SCALE_BAR_MAX_WIDTH_PX;
  const niceMeters =
    [...NICE_SCALE_METERS].reverse().find((value) => value <= maxMeters) ?? NICE_SCALE_METERS[0];

  return {
    label: formatScaleLabel(niceMeters),
    widthPx: clamp(niceMeters / Math.max(metersPerPixel, 1), 28, SCALE_BAR_MAX_WIDTH_PX),
  };
};

const getBoundsFromCollection = (collection: SectionFeatureCollection) => {
  if (collection.bbox) {
    const bbox = collection.bbox as unknown as [number, number, number, number];
    const minLon = bbox[0];
    const minLat = bbox[1];
    const maxLon = bbox[2];
    const maxLat = bbox[3];
    if ([minLon, minLat, maxLon, maxLat].every(Number.isFinite)) {
      return [
        [minLon, minLat],
        [maxLon, maxLat],
      ] as [[number, number], [number, number]];
    }
  }

  const coordinates: [number, number][] = [];
  const collectCoordinates = (value: unknown) => {
    if (!Array.isArray(value)) {
      return;
    }

    if (
      value.length >= 2 &&
      typeof value[0] === "number" &&
      typeof value[1] === "number" &&
      Number.isFinite(value[0]) &&
      Number.isFinite(value[1])
    ) {
      coordinates.push([value[0], value[1]]);
      return;
    }

    value.forEach(collectCoordinates);
  };

  collection.features.forEach((feature) => {
    if ("coordinates" in feature.geometry) {
      collectCoordinates(feature.geometry.coordinates);
    }
  });

  if (coordinates.length === 0) {
    return null;
  }

  const longitudes = coordinates.map(([longitude]) => longitude);
  const latitudes = coordinates.map(([, latitude]) => latitude);

  return [
    [Math.min(...longitudes), Math.min(...latitudes)],
    [Math.max(...longitudes), Math.max(...latitudes)],
  ] as [[number, number], [number, number]];
};

const getFeatureCenter = (feature: SectionFeature): [number, number] | null => {
  const coordinates: [number, number][] = [];
  const collectCoordinates = (value: unknown) => {
    if (!Array.isArray(value)) {
      return;
    }
    if (
      value.length >= 2 &&
      typeof value[0] === "number" &&
      typeof value[1] === "number" &&
      Number.isFinite(value[0]) &&
      Number.isFinite(value[1])
    ) {
      coordinates.push([value[0], value[1]]);
      return;
    }
    value.forEach(collectCoordinates);
  };

  if ("coordinates" in feature.geometry) {
    collectCoordinates(feature.geometry.coordinates);
  }

  if (coordinates.length === 0) {
    return null;
  }

  const longitude = coordinates.reduce((total, coordinate) => total + coordinate[0], 0) / coordinates.length;
  const latitude = coordinates.reduce((total, coordinate) => total + coordinate[1], 0) / coordinates.length;
  return [longitude, latitude];
};

const buildHousingHeatCollection = (
  collection: SectionFeatureCollection,
  metric: "perceivedSafetyPotential" | "noiseExposurePotential",
): GeoJSON.FeatureCollection<GeoJSON.Point, GeoJSON.GeoJsonProperties> => ({
  type: "FeatureCollection",
  features: collection.features.flatMap((feature) => {
    const center = getFeatureCenter(feature);
    if (!center) {
      return [];
    }
    const value =
      metric === "perceivedSafetyPotential"
        ? 100 - (feature.properties.safety_potential_score ?? 50)
        : feature.properties.noise_exposure_potential ?? 50;

    return [
      {
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: center,
        },
        properties: {
          ...feature.properties,
          heat_value: Math.min(100, Math.max(0, value)),
        },
      },
    ];
  }),
});

const getVectorBasemapSourceId = (map: maplibregl.Map) => {
  const sources = map.getStyle().sources;
  return (
    Object.entries(sources).find(([, source]) => source.type === "vector")?.[0] ?? null
  );
};

const getFirstSymbolLayerId = (map: maplibregl.Map) =>
  map
    .getStyle()
    .layers?.find((layer) => layer.type === "symbol" && !layer.id.startsWith("soctrace-"))?.id;

const tuneBasemapStyle = (map: maplibregl.Map, mode: "map" | "satellite") => {
  const layers = map.getStyle().layers ?? [];

  layers.forEach((layer) => {
    if (layer.id.startsWith("soctrace-")) {
      return;
    }

    try {
      if (layer.type === "background") {
        map.setPaintProperty(
          layer.id,
          "background-color",
          mode === "map" ? "#060b14" : "#f2f5f8",
        );
      }

      if (layer.type === "fill" && /water/i.test(layer.id)) {
        map.setPaintProperty(
          layer.id,
          "fill-color",
          mode === "map" ? "#0b1727" : "#d8e8f7",
        );
        map.setPaintProperty(layer.id, "fill-opacity", mode === "map" ? 0.94 : 0.9);
      }

      if (layer.type === "fill" && /landcover|park|vegetation/i.test(layer.id)) {
        map.setPaintProperty(
          layer.id,
          "fill-color",
          mode === "map" ? "#0c1511" : "#dfeadc",
        );
        map.setPaintProperty(layer.id, "fill-opacity", mode === "map" ? 0.34 : 0.32);
      }

      if (layer.type === "symbol" && /place|settlement|state_label|water_name/i.test(layer.id)) {
        map.setPaintProperty(
          layer.id,
          "text-color",
          mode === "map" ? "#a8b6c7" : "#425466",
        );
        map.setPaintProperty(
          layer.id,
          "text-halo-color",
          mode === "map" ? "rgba(6, 11, 20, 0.88)" : "rgba(255, 255, 255, 0.86)",
        );
        map.setPaintProperty(layer.id, "text-halo-width", 1);
      }
    } catch {
      // Some third-party layers don't expose every property consistently. Skip quietly.
    }
  });
};

const ensurePremiumBasemapLayers = (map: maplibregl.Map, mode: "map" | "satellite") => {
  const source = getVectorBasemapSourceId(map);
  const beforeId = getFirstSymbolLayerId(map);

  if (!source) {
    return;
  }

  try {
    if (!map.getLayer(SOC_TRACE_BASEMAP_LAYER_IDS.buildings)) {
      map.addLayer(
        {
          id: SOC_TRACE_BASEMAP_LAYER_IDS.buildings,
          type: "fill",
          source,
          "source-layer": "building",
          minzoom: 12.25,
          paint: {
            "fill-color": mode === "map" ? "#16202d" : "#dbe4ee",
            "fill-opacity": mode === "map" ? 0.3 : 0.24,
          },
        },
        beforeId,
      );
    }
  } catch {
    // Building layer is optional depending on provider/version.
  }

  try {
    if (!map.getLayer(SOC_TRACE_BASEMAP_LAYER_IDS.roadsPrimary)) {
      map.addLayer(
        {
          id: SOC_TRACE_BASEMAP_LAYER_IDS.roadsPrimary,
          type: "line",
          source,
          "source-layer": "transportation",
          minzoom: 10.5,
          filter: [
            "match",
            ["get", "class"],
            ["motorway", "trunk", "primary", "secondary", "tertiary"],
            true,
            false,
          ],
          paint: {
            "line-color": mode === "map" ? "#9fb7d8" : "#667a8f",
            "line-opacity": mode === "map" ? 0.34 : 0.26,
            "line-width": [
              "interpolate",
              ["linear"],
              ["zoom"],
              10.5,
              0.7,
              13,
              1.8,
              16,
              3.8,
            ],
          },
        },
        beforeId,
      );
    }
  } catch {
    // Transportation source-layer can vary by provider.
  }

  try {
    if (!map.getLayer(SOC_TRACE_BASEMAP_LAYER_IDS.roadsSecondary)) {
      map.addLayer(
        {
          id: SOC_TRACE_BASEMAP_LAYER_IDS.roadsSecondary,
          type: "line",
          source,
          "source-layer": "transportation",
          minzoom: 12.2,
          filter: [
            "match",
            ["get", "class"],
            ["minor", "service", "street", "street_limited", "residential", "living_street"],
            true,
            false,
          ],
          paint: {
            "line-color": mode === "map" ? "#7f94ad" : "#8a99aa",
            "line-opacity": mode === "map" ? 0.2 : 0.14,
            "line-width": [
              "interpolate",
              ["linear"],
              ["zoom"],
              12.2,
              0.4,
              14.2,
              1.1,
              17,
              2.2,
            ],
          },
        },
        beforeId,
      );
    }
  } catch {
    // Transportation source-layer can vary by provider.
  }

  try {
    if (!map.getLayer(SOC_TRACE_BASEMAP_LAYER_IDS.roadLabels)) {
      map.addLayer(
        {
          id: SOC_TRACE_BASEMAP_LAYER_IDS.roadLabels,
          type: "symbol",
          source,
          "source-layer": "transportation_name",
          minzoom: 14,
          layout: {
            "symbol-placement": "line",
            "text-field": ["coalesce", ["get", "name:es"], ["get", "name"]],
            "text-font": ["Noto Sans Regular"],
            "text-size": ["interpolate", ["linear"], ["zoom"], 14, 10, 17, 13],
            "symbol-spacing": 350,
          },
          paint: {
            "text-color": mode === "map" ? "#d8e1ea" : "#334155",
            "text-halo-color": mode === "map" ? "rgba(6, 11, 20, 0.9)" : "rgba(255, 255, 255, 0.92)",
            "text-halo-width": 1.1,
            "text-opacity": mode === "map" ? 0.78 : 0.66,
          },
        },
        beforeId,
      );
    }
  } catch {
    // Road labels are optional if the provider omits transportation_name.
  }
};

export function SocTraceMap() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapRef | null>(null);
  const fittedBoundsKeyRef = useRef<string | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);
  const [mapScale, setMapScale] = useState(() =>
    getScaleFromView(INITIAL_VIEW_STATE.zoom, INITIAL_VIEW_STATE.latitude),
  );
  const [mapDiagnostics, setMapDiagnostics] = useState<{
    sourceFeatures: number;
    renderedFeatures: number;
  }>({
    sourceFeatures: 0,
    renderedFeatures: 0,
  });
  const sectionCollection = useDashboardStore((state) => state.sectionCollection);
  const selectedSectionId = useDashboardStore((state) => state.selectedSectionId);
  const mapMode = useDashboardStore((state) => state.mapMode);
  const layersState = useDashboardStore((state) => state.layers);
  const populationYear = useDashboardStore((state) => state.filters.populationYear);
  const ageStructureYear = useDashboardStore((state) => state.filters.ageStructureYear);
  const incomeYear = useDashboardStore((state) => state.filters.incomeYear);
  const socioeconomicYear = useDashboardStore((state) => state.filters.socioeconomicYear);
  const electionContestId = useDashboardStore((state) => state.filters.electionContestId);
  const realEstateMetric = useDashboardStore((state) => state.realEstateMetric);
  const landBuiltEnvironmentMetric = useDashboardStore((state) => state.landBuiltEnvironmentMetric);
  const territorialMetric = useDashboardStore((state) => state.territorialMetric);
  const socioeconomicMetric = useDashboardStore((state) => state.socioeconomicMetric);
  const setHoveredSection = useDashboardStore((state) => state.setHoveredSection);
  const setSelectedSection = useDashboardStore((state) => state.setSelectedSection);
  const setMapMode = useDashboardStore((state) => state.setMapMode);
  const isMapLoading = useDashboardStore((state) => state.isMapLoading);
  const statusMessage = useDashboardStore((state) => state.statusMessage);
  const statusTone = useDashboardStore((state) => state.statusTone);
  const error = useDashboardStore((state) => state.error);
  const activeLayer = getActiveLayer(layersState);
  const selectedElectionContest = electionContests.find((contest) => contest.id === electionContestId);
  const isHousingHeatLayer =
    activeLayer === "housingIntelligence" &&
    (territorialMetric === "perceivedSafetyPotential" || territorialMetric === "noiseExposurePotential");
  const isThematicLayerVisible =
    layersState.population ||
    layersState.ageStructure ||
    layersState.electoralBehavior ||
    layersState.incomeLevel ||
    layersState.landBuiltEnvironment ||
    layersState.housingIntelligence ||
    layersState.socioeconomicIntelligence ||
    layersState.electoralForecasting;
  const mapStyle = useMemo(() => BASEMAP_STYLES[mapMode], [mapMode]);
  const interactiveLayerIds = useMemo(
    () =>
      isHousingHeatLayer
        ? ["housing-heat-circles"]
        : isThematicLayerVisible
          ? ["sections-fill", "sections-line"]
          : [],
    [isHousingHeatLayer, isThematicLayerVisible],
  );

  const densityRange = useMemo(() => {
    const densities =
      sectionCollection?.features
        .map((feature) => feature.properties.population_density)
        .filter((value): value is number => typeof value === "number") ?? [];

    if (densities.length === 0) {
      return { min: 0, max: 1 };
    }

    return {
      min: Math.min(...densities),
      max: Math.max(...densities),
    };
  }, [sectionCollection]);

  const winningParties = useMemo(() => {
    const parties =
      sectionCollection?.features
        .map((feature) =>
          activeLayer === "electoralForecasting"
            ? getCampaignForecastLeader(feature.properties)
            : normalizePartyName(feature.properties.winning_party),
        )
        .filter((party): party is string => typeof party === "string" && party.trim().length > 0) ??
      [];

    return Array.from(new Set(parties)).sort((a, b) => a.localeCompare(b));
  }, [activeLayer, sectionCollection]);

  const debugSnapshot = useMemo(() => {
    const firstFeature = sectionCollection?.features[0];
    return {
      featureCount: sectionCollection?.features.length ?? 0,
      geometryType: firstFeature?.geometry?.type ?? "n/a",
      firstSectionId: firstFeature?.properties.section_id ?? "n/a",
      firstDensity: firstFeature?.properties.population_density ?? null,
    };
  }, [sectionCollection]);

  const styledSectionCollection = useMemo<SectionFeatureCollection | null>(() => {
    if (!sectionCollection) {
      return sectionCollection;
    }

    if (activeLayer === "landBuiltEnvironment") {
      return buildLandBuiltEnvironmentPresentation(sectionCollection, landBuiltEnvironmentMetric).collection;
    }

    if (activeLayer !== "incomeLevel") {
      return sectionCollection;
    }

    const incomeValues = sectionCollection.features
      .map((feature) => feature.properties.renta_media_persona)
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value))
      .sort((a, b) => a - b);

    if (incomeValues.length === 0) {
      return sectionCollection;
    }

    const withIncomeQuintiles = sectionCollection.features.map((feature): SectionFeature => {
      if (typeof feature.properties.income_quintile === "number") {
        return feature;
      }

      const income = feature.properties.renta_media_persona;
      if (typeof income !== "number" || !Number.isFinite(income)) {
        return feature;
      }

      const rank = incomeValues.findIndex((value) => value >= income);
      const quintile = Math.min(5, Math.max(1, Math.floor((rank / incomeValues.length) * 5) + 1));

      return {
        ...feature,
        properties: {
          ...feature.properties,
          income_quintile: quintile,
        },
      };
    });

    return {
      ...sectionCollection,
      features: withIncomeQuintiles,
    };
  }, [activeLayer, landBuiltEnvironmentMetric, sectionCollection]);

  const housingHeatCollection = useMemo(
    () => {
      if (!sectionCollection || !isHousingHeatLayer) {
        return null;
      }
      const heatMetric =
        territorialMetric === "noiseExposurePotential"
          ? "noiseExposurePotential"
          : "perceivedSafetyPotential";
      return buildHousingHeatCollection(sectionCollection, heatMetric);
    },
    [isHousingHeatLayer, sectionCollection, territorialMetric],
  );

  const fillColorExpression = useMemo(
    () =>
      getLayerFillExpression(
        activeLayer,
        realEstateMetric,
        territorialMetric,
        landBuiltEnvironmentMetric,
        socioeconomicMetric,
      ),
    [activeLayer, landBuiltEnvironmentMetric, realEstateMetric, socioeconomicMetric, territorialMetric],
  );

  const baseFillUnderlayLayer = useMemo<LayerProps>(
    () => ({
      id: "sections-fill-underlay",
      type: "fill",
      paint: {
        "fill-color": "#142131",
        "fill-opacity": 0.18,
      },
    }),
    [],
  );

  const baseFillLayer = useMemo<LayerProps>(
    () => ({
      id: "sections-fill",
      type: "fill",
      paint: {
        "fill-color": fillColorExpression as never,
        "fill-opacity": 0.8,
      },
    }),
    [fillColorExpression],
  );

  const baseLineLayer = useMemo<LayerProps>(
    () => ({
      id: "sections-line",
      type: "line",
      paint: {
        "line-color": "#dbe4f0",
        "line-width": 1.5,
        "line-opacity": 0.7,
      },
    }),
    [],
  );

  const selectedFillLayer = useMemo<LayerProps>(
    () => ({
      id: "sections-fill-selected",
      type: "fill",
      filter: ["==", ["get", "section_id"], selectedSectionId || "__none__"],
      paint: {
        "fill-color": "#f8fafc",
        "fill-opacity": 0.12,
      },
    }),
    [selectedSectionId],
  );

  const selectedLineLayer = useMemo<LayerProps>(
    () => ({
      id: "sections-line-selected",
      type: "line",
      filter: ["==", ["get", "section_id"], selectedSectionId || "__none__"],
      paint: {
        "line-color": "#f8fafc",
        "line-width": 2.3,
        "line-opacity": 1,
      },
    }),
    [selectedSectionId],
  );

  const housingHeatLayer = useMemo<LayerProps>(
    () => ({
      id: "housing-heat",
      type: "heatmap",
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["to-number", ["get", "heat_value"]], 0, 0.12, 100, 1],
        "heatmap-intensity": 1.25,
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 10, 28, 13, 56, 16, 88],
        "heatmap-opacity": 0.72,
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(15,23,42,0)",
          0.2,
          "rgba(52,211,153,0.30)",
          0.45,
          "rgba(94,234,212,0.32)",
          0.7,
          "rgba(124,58,237,0.46)",
          1,
          "rgba(168,85,247,0.68)",
        ],
      },
    }),
    [],
  );

  const housingHeatCircleLayer = useMemo<LayerProps>(
    () => ({
      id: "housing-heat-circles",
      type: "circle",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "heat_value"]], 0, 10, 100, 30],
        "circle-color": [
          "interpolate",
          ["linear"],
          ["to-number", ["get", "heat_value"]],
          0,
          "#74d99f",
          50,
          "#38bdf8",
          100,
          "#a855f7",
        ],
        "circle-opacity": 0.22,
        "circle-blur": 0.78,
        "circle-stroke-color": "#f8fafc",
        "circle-stroke-opacity": ["case", ["==", ["get", "section_id"], selectedSectionId || "__none__"], 0.65, 0],
        "circle-stroke-width": ["case", ["==", ["get", "section_id"], selectedSectionId || "__none__"], 1.6, 0],
      },
    }),
    [selectedSectionId],
  );

  useEffect(() => {
    if (!isMapReady || !mapRef.current) {
      return;
    }

    const map = mapRef.current.getMap();
    const applyPremiumBasemap = () => {
      tuneBasemapStyle(map, mapMode);
      ensurePremiumBasemapLayers(map, mapMode);
    };

    applyPremiumBasemap();
    map.on("styledata", applyPremiumBasemap);

    return () => {
      map.off("styledata", applyPremiumBasemap);
    };
  }, [isMapReady, mapMode]);

  useEffect(() => {
    if (!styledSectionCollection) {
      return;
    }
    console.debug("[SocTrace] map state", {
      features: styledSectionCollection.features.length,
      firstGeometryType: styledSectionCollection.features[0]?.geometry?.type,
      firstSectionId: styledSectionCollection.features[0]?.properties.section_id,
      firstDensity: styledSectionCollection.features[0]?.properties.population_density,
      bbox: styledSectionCollection.bbox,
    });
  }, [styledSectionCollection]);

  useEffect(() => {
    if (isThematicLayerVisible) {
      return;
    }

    setHoveredSection(null);
  }, [isThematicLayerVisible, setHoveredSection]);

  useEffect(() => {
    if (!isMapReady || !mapRef.current || !styledSectionCollection) {
      return;
    }

    const map = mapRef.current.getMap();
    const updateDiagnostics = () => {
      const sourceId = isHousingHeatLayer ? "housing-heat-source" : "sections-source";
      if (!map.getSource(sourceId)) {
        return;
      }
      const sourceFeatures = map.querySourceFeatures(sourceId).length;
      const renderedFeatures = map.queryRenderedFeatures(undefined, {
        layers: [isHousingHeatLayer ? "housing-heat-circles" : "sections-fill"],
      }).length;
      setMapDiagnostics({ sourceFeatures, renderedFeatures });
      console.debug("[SocTrace] render diagnostics", {
        sourceFeatures,
        renderedFeatures,
      });
    };

    updateDiagnostics();
    map.on("idle", updateDiagnostics);
    return () => {
      map.off("idle", updateDiagnostics);
    };
  }, [isHousingHeatLayer, isMapReady, styledSectionCollection]);

  useEffect(() => {
    if (!isMapReady || !mapRef.current || !sectionCollection) {
      return;
    }

    const bounds = getBoundsFromCollection(sectionCollection);
    if (!bounds) {
      return;
    }

    const boundsKey = bounds.flat().map((value) => value.toFixed(6)).join(":");
    if (fittedBoundsKeyRef.current === boundsKey) {
      return;
    }

    fittedBoundsKeyRef.current = boundsKey;
    mapRef.current.fitBounds(bounds, {
      padding: MUNICIPALITY_FIT_PADDING,
      duration: 0,
      bearing: INITIAL_VIEW_STATE.bearing,
      pitch: INITIAL_VIEW_STATE.pitch,
    });
  }, [isMapReady, sectionCollection]);

  const handleFocus = () => {
    const bounds = sectionCollection ? getBoundsFromCollection(sectionCollection) : null;
    if (bounds && mapRef.current) {
      mapRef.current.fitBounds(bounds, {
        padding: MUNICIPALITY_FIT_PADDING,
        duration: 900,
        bearing: INITIAL_VIEW_STATE.bearing,
        pitch: INITIAL_VIEW_STATE.pitch,
      });
    } else {
      mapRef.current?.flyTo({
        center: [INITIAL_VIEW_STATE.longitude, INITIAL_VIEW_STATE.latitude],
        zoom: INITIAL_VIEW_STATE.zoom,
        bearing: INITIAL_VIEW_STATE.bearing,
        pitch: INITIAL_VIEW_STATE.pitch,
        duration: 900,
      });
    }

    if (document.fullscreenElement || !containerRef.current) {
      return;
    }
    containerRef.current.requestFullscreen?.().catch(() => undefined);
  };

  const handleMove = (event: ViewStateChangeEvent) => {
    setMapScale(getScaleFromView(event.viewState.zoom, event.viewState.latitude));
  };

  const handleMouseMove = (event: MapLayerMouseEvent) => {
    if (!isThematicLayerVisible) {
      setHoveredSection(null);
      return;
    }

    const feature = event.features?.[0];
    const sectionId = feature?.properties?.section_id;
    if (typeof sectionId === "string") {
      setHoveredSection(sectionId, { x: event.point.x, y: event.point.y });
      return;
    }
    setHoveredSection(null);
  };

  const handleClick = (event: MapLayerMouseEvent) => {
    if (!isThematicLayerVisible) {
      return;
    }

    const clickedProperties = event.features?.[0]?.properties;
    if (!clickedProperties) {
      return;
    }

    const sectionId = clickedProperties?.section_id;
    if (typeof sectionId === "string") {
      if (import.meta.env.DEV && activeLayer === "population") {
        console.debug("[PopulationClick]", {
          selectedYear: populationYear,
          clickedProperties,
          rawSectionId: clickedProperties.section_id,
          normalizedSectionId: normalizeSectionId(clickedProperties.section_id),
          sectionName: clickedProperties.section_name ?? clickedProperties.name,
        });
      }
      setSelectedSection(sectionId);
    }
  };

  return (
    <Panel tone="elevated" className="relative h-full overflow-hidden p-0">
      <div ref={containerRef} className="dashboard-map-shell relative h-full min-h-[460px]">
        {isThematicLayerVisible ? (
          <MapLegend
            activeLayer={activeLayer}
            minValue={densityRange.min}
            maxValue={densityRange.max}
            winningParties={winningParties}
            landBuiltEnvironmentMetric={landBuiltEnvironmentMetric}
            territorialMetric={territorialMetric}
            socioeconomicMetric={socioeconomicMetric}
            displayYear={
              activeLayer === "ageStructure"
                ? ageStructureYear
                : activeLayer === "incomeLevel"
                  ? incomeYear
                  : activeLayer === "socioeconomicIntelligence"
                    ? socioeconomicYear
                  : null
            }
            electionLabel={
              activeLayer === "electoralBehavior" && selectedElectionContest
                ? `${selectedElectionContest.type === "andaluzas" ? "Regional" : selectedElectionContest.type} ${selectedElectionContest.label}`
                : null
            }
          />
        ) : null}
        <MapControls
          mode={mapMode}
          scale={mapScale}
          onZoomIn={() => mapRef.current?.zoomIn({ duration: 250 })}
          onZoomOut={() => mapRef.current?.zoomOut({ duration: 250 })}
          onFocus={handleFocus}
          onToggleMode={() => setMapMode(mapMode === "map" ? "satellite" : "map")}
        />

        <div className="pointer-events-none absolute inset-x-0 top-0 z-[1] h-24 bg-[linear-gradient(180deg,rgba(8,10,18,0.72),transparent)]" />
        <div className="pointer-events-none absolute inset-0 z-[1] bg-[radial-gradient(circle_at_50%_35%,transparent_0%,transparent_46%,rgba(5,7,11,0.34)_100%)]" />

        {isMapLoading ? (
          <div className="absolute inset-0 z-[3] flex items-center justify-center bg-[#05070ccc] backdrop-blur-sm">
            <div className="rounded-2xl border border-white/10 bg-[#0c1322]/94 px-5 py-4 text-sm text-slate-300 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
              Loading Mijas sections from PostGIS...
            </div>
          </div>
        ) : null}

        {!isMapLoading && !styledSectionCollection ? (
          <div className="absolute inset-0 z-[3] flex items-center justify-center bg-[#05070c99] backdrop-blur-[2px]">
            <div className="max-w-md rounded-2xl border border-white/10 bg-[#0c1322]/94 px-5 py-4 text-center text-sm text-slate-300 shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
              Mijas is selected, but section geometries are not available because the backend is offline.
            </div>
          </div>
        ) : null}

        {statusMessage ? (
          <div
            className={`absolute bottom-4 left-4 z-[3] max-w-md rounded-2xl px-4 py-3 text-sm shadow-[0_20px_50px_rgba(0,0,0,0.35)] ${
              statusTone === "warning"
                ? "border border-amber-400/25 bg-[#1b160d]/95 text-amber-100"
                : statusTone === "error"
                  ? "border border-rose-500/20 bg-[#1a1116]/95 text-rose-100"
                  : "border border-cyan-400/20 bg-[#0c1322]/95 text-cyan-50"
            }`}
          >
            {statusMessage}
          </div>
        ) : null}

        {error ? (
          <div className="absolute bottom-4 left-4 z-[3] max-w-md rounded-2xl border border-rose-500/20 bg-[#1a1116]/95 px-4 py-3 text-sm text-rose-100 shadow-[0_20px_50px_rgba(0,0,0,0.35)]">
            {error}
          </div>
        ) : null}

        <Map
          ref={mapRef}
          reuseMaps
          mapLib={maplibregl}
          mapStyle={mapStyle}
          attributionControl={false}
          initialViewState={INITIAL_VIEW_STATE}
          minZoom={10.4}
          maxZoom={18.4}
          style={{ width: "100%", height: "100%" }}
          interactiveLayerIds={interactiveLayerIds}
          onLoad={() => setIsMapReady(true)}
          onMove={handleMove}
          onMouseMove={handleMouseMove}
          onClick={handleClick}
          onMouseLeave={() => setHoveredSection(null)}
        >
          {styledSectionCollection && !isHousingHeatLayer ? (
            <Source id="sections-source" type="geojson" data={styledSectionCollection}>
              {isThematicLayerVisible ? <Layer {...baseFillUnderlayLayer} /> : null}
              {isThematicLayerVisible ? <Layer {...baseFillLayer} /> : null}
              {isThematicLayerVisible ? <Layer {...baseLineLayer} /> : null}
              {isThematicLayerVisible ? <Layer {...selectedFillLayer} /> : null}
              {isThematicLayerVisible ? <Layer {...selectedLineLayer} /> : null}
            </Source>
          ) : null}
          {housingHeatCollection ? (
            <Source id="housing-heat-source" type="geojson" data={housingHeatCollection}>
              <Layer {...housingHeatLayer} />
              <Layer {...housingHeatCircleLayer} />
            </Source>
          ) : null}
        </Map>

        {isThematicLayerVisible ? (
          <div className="pointer-events-none absolute inset-0 z-[2]">
            <SectionTooltip />
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
