export type LayerKey =
  | "population"
  | "ageStructure"
  | "foreignBorn"
  | "incomeLevel"
  | "electoralBehavior"
  | "landBuiltEnvironment"
  | "housingIntelligence";

export type DashboardSection = {
  id: string;
  district: string;
  neighborhood: string;
  label: string;
  centroid: [number, number];
  intensity: number;
  population: number;
  medianAge: number;
  foreignBorn: number;
  turnout: number;
  incomeIndex: number;
  housingPressure: number;
  dominantParty: string;
};

export type DashboardFeature = GeoJSON.Feature<
  GeoJSON.Polygon,
  DashboardSection & { layerValues: Record<LayerKey, number> }
>;

const districtPool = [
  ["Chamartin", "El Viso"],
  ["Salamanca", "Goya"],
  ["Centro", "Justicia"],
  ["Retiro", "Pacífico"],
  ["Arganzuela", "Delicias"],
  ["Tetuan", "Cuatro Caminos"],
  ["Moncloa", "Arguelles"],
  ["Chamberi", "Almagro"],
  ["Puente de Vallecas", "Numancia"],
  ["Carabanchel", "Oporto"],
  ["Usera", "Moscardó"],
  ["Ciudad Lineal", "Ventas"],
  ["Hortaleza", "Canillas"],
  ["Latina", "Aluche"],
  ["San Blas", "Canillejas"],
] as const;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

const seededNoise = (seed: number) => {
  const x = Math.sin(seed * 91.173) * 43758.5453123;
  return x - Math.floor(x);
};

function createFeature(
  col: number,
  row: number,
  index: number,
  centerLon: number,
  centerLat: number,
  lonStep: number,
  latStep: number,
): DashboardFeature {
  const jitterA = seededNoise(index + 1);
  const jitterB = seededNoise(index + 11);
  const jitterC = seededNoise(index + 31);
  const jitterD = seededNoise(index + 49);
  const jitterE = seededNoise(index + 67);
  const dx = (col - 11.5) / 11.5;
  const dy = (row - 8.5) / 8.5;
  const radius = Math.sqrt(dx * dx + dy * dy);
  const heatCore = Math.sin((col + 1) * 0.62) * 0.24 + Math.cos((row + 1) * 0.85) * 0.2;
  const corridor = Math.max(0, 1 - Math.abs(dx + dy * 0.6) * 1.35) * 0.24;
  const intensity = clamp(0.18 + (1 - radius) * 0.55 + heatCore + corridor + jitterA * 0.28, 0, 1);
  const population = Math.round(1700 + intensity * 2800 + jitterB * 520);
  const medianAge = Number((33 + dy * 7 + (1 - intensity) * 8 + jitterC * 3.8).toFixed(1));
  const foreignBorn = Number((8 + intensity * 18 + Math.max(0, dx) * 9 + jitterD * 5).toFixed(1));
  const turnout = Number((55 + (1 - intensity) * 8 + Math.max(0, -dy) * 6 + jitterE * 7).toFixed(1));
  const incomeIndex = Math.round(76 + (1 - radius) * 44 + Math.max(0, -dx) * 18 + jitterB * 10);
  const housingPressure = Number((41 + intensity * 28 + Math.max(0, dx) * 10 + jitterC * 11).toFixed(1));
  const districtTuple = districtPool[index % districtPool.length];
  const dominantParty = incomeIndex > 110 ? "PP" : foreignBorn > 24 ? "Más Madrid" : turnout > 67 ? "PSOE" : "PP";
  const id = `28079${String(100000 + index).slice(1)}`;
  const centroidLon = centerLon + (col - 11.5) * lonStep;
  const centroidLat = centerLat + (row - 8.5) * latStep;
  const west = centroidLon - lonStep * (0.44 + jitterA * 0.08);
  const east = centroidLon + lonStep * (0.42 + jitterB * 0.1);
  const south = centroidLat - latStep * (0.42 + jitterC * 0.08);
  const north = centroidLat + latStep * (0.43 + jitterD * 0.08);

  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [west, south],
          [centroidLon - lonStep * 0.04, south - latStep * 0.04],
          [east, south + latStep * 0.05],
          [east + lonStep * 0.04, north - latStep * 0.02],
          [centroidLon + lonStep * 0.02, north],
          [west - lonStep * 0.03, north - latStep * 0.05],
          [west, south],
        ],
      ],
    },
    properties: {
      id,
      district: districtTuple[0],
      neighborhood: districtTuple[1],
      label: `Section ${id}`,
      centroid: [centroidLon, centroidLat],
      intensity,
      population,
      medianAge,
      foreignBorn,
      turnout,
      incomeIndex,
      housingPressure,
      dominantParty,
      layerValues: {
        population: intensity,
        ageStructure: clamp((medianAge - 30) / 24, 0, 1),
        foreignBorn: clamp(foreignBorn / 36, 0, 1),
        incomeLevel: clamp((incomeIndex - 70) / 60, 0, 1),
        electoralBehavior: clamp((turnout - 52) / 28, 0, 1),
        landBuiltEnvironment: clamp((intensity - 0.12) / 0.76, 0, 1),
        housingIntelligence: clamp((housingPressure - 35) / 45, 0, 1),
      },
    },
  };
}

function buildSections(): DashboardFeature[] {
  const features: DashboardFeature[] = [];
  const centerLon = -3.7038;
  const centerLat = 40.4168;
  const lonStep = 0.0072;
  const latStep = 0.00555;
  let index = 0;

  for (let row = 0; row < 17; row += 1) {
    for (let col = 0; col < 23; col += 1) {
      const dx = (col - 11) / 11;
      const dy = (row - 8) / 8;
      const ellipse = dx * dx + dy * dy * 1.25;
      const cutout = col > 18 && row < 3;
      if (ellipse > 1.02 || cutout) {
        continue;
      }

      features.push(createFeature(col, row, index, centerLon, centerLat, lonStep, latStep));
      index += 1;
    }
  }

  return features;
}

export const mockSectionFeatures = buildSections();

export const mockSectionsGeoJson: GeoJSON.FeatureCollection<
  GeoJSON.Polygon,
  DashboardSection & { layerValues: Record<LayerKey, number> }
> = {
  type: "FeatureCollection",
  features: mockSectionFeatures,
};

export const defaultSelectedSectionId =
  mockSectionFeatures[Math.floor(mockSectionFeatures.length * 0.56)]?.properties.id ??
  mockSectionFeatures[0]?.properties.id ??
  "";

const walkCoordinates = (coordinates: unknown, points: [number, number][]) => {
  if (!Array.isArray(coordinates)) {
    return;
  }

  if (
    coordinates.length >= 2 &&
    typeof coordinates[0] === "number" &&
    typeof coordinates[1] === "number"
  ) {
    points.push([coordinates[0], coordinates[1]]);
    return;
  }

  coordinates.forEach((entry) => walkCoordinates(entry, points));
};

export const mockSectionsBbox = (() => {
  const points: [number, number][] = [];
  mockSectionFeatures.forEach((feature) => walkCoordinates(feature.geometry.coordinates, points));

  if (points.length === 0) {
    return undefined;
  }

  const longitudes = points.map(([lon]) => lon);
  const latitudes = points.map(([, lat]) => lat);

  return [
    Math.min(...longitudes),
    Math.min(...latitudes),
    Math.max(...longitudes),
    Math.max(...latitudes),
  ] as [number, number, number, number];
})();
