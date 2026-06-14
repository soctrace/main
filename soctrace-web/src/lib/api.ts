import type {
  MunicipalityListResponse,
  ElectoralScenarioListResponse,
  SectionDetail,
  SectionFeatureCollection,
} from "@/types/api";
import { mockSectionFeatures, mockSectionsBbox } from "@/data/mockSections";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

async function fetchJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`);
  } catch {
    throw new Error(`Cannot reach API at ${API_BASE_URL}`);
  }

  if (!response.ok) {
    throw new Error(`API request failed (${response.status}) at ${API_BASE_URL}${path}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot reach API at ${API_BASE_URL}`);
  }

  if (!response.ok) {
    let detail = `API request failed (${response.status}) at ${API_BASE_URL}${path}`;
    try {
      const payload = (await response.json()) as { detail?: string | Array<{ msg?: string }> };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        detail = payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
      }
    } catch {
      // Keep the generic message when the API does not return JSON.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function fetchMunicipalities() {
  return fetchJson<MunicipalityListResponse>("/api/v1/municipalities");
}

export function fetchApiHealth() {
  return fetchJson<{ status: string }>("/health");
}

export function askLocalAnalyst(question: string, municipalityId: string) {
  return postJson<import("@/features/ask-soctrace/types").AskSocTraceResponse>(
    "/api/v1/analyst/ask",
    { question, municipality_id: municipalityId },
  );
}

export function askSocTraceAgent(body: {
  question: string;
  sessionId?: string;
  conversationId?: string;
  session_id?: string;
  conversation_id?: string;
  municipioId?: string;
  activeMunicipality?: string;
  activeYear?: number | null;
  activeLayer?: string | null;
  selectedSectionId?: string | null;
  locale?: "es-ES";
}) {
  return postJson<import("@/features/ask-soctrace/types").AskSocTraceAgentResponse>(
    "/api/v1/ask",
    body,
  );
}

export type DemoRequestPayload = {
  organization: string;
  firstName: string;
  lastName: string;
  email: string;
  phone?: string | null;
  sector: string;
  reasons: string;
};

export function submitDemoRequest(body: DemoRequestPayload) {
  return postJson<{ ok: boolean; message: string }>("/api/request-demo", body);
}

export function fetchMijasElectoralScenarios() {
  return fetchJson<ElectoralScenarioListResponse>("/api/v1/forecasts/mijas/2027/scenarios");
}

export function fetchSectionsGeoJson(
  municipalityId: string,
  year: string,
  layer?: string | null,
  electionId?: number | null,
) {
  const searchParams = new URLSearchParams({
    municipality_id: municipalityId,
    year,
  });
  if (layer) {
    searchParams.set("layer", layer);
  }
  if (electionId) {
    searchParams.set("election_id", String(electionId));
  }

  return fetchJson<SectionFeatureCollection>(`/api/v1/geo/sections?${searchParams.toString()}`);
}

export function fetchSectionDetail(sectionId: string, year: string) {
  const searchParams = new URLSearchParams({ year });
  return fetchJson<SectionDetail>(`/api/v1/sections/${sectionId}?${searchParams.toString()}`);
}

export function buildMockSectionCollection(): SectionFeatureCollection {
  return {
    type: "FeatureCollection",
    bbox: mockSectionsBbox,
    features: mockSectionFeatures.map((feature, index) => {
      const incomeQuintile = Math.min(
        5,
        Math.max(1, Math.ceil(feature.properties.layerValues.incomeLevel * 5)),
      );
      const individualIncome = Math.round(9000 + feature.properties.incomeIndex * 54);
      const householdIncome = Math.round(
        individualIncome * (2.35 + feature.properties.intensity * 0.55),
      );

      return {
        type: "Feature",
        geometry: feature.geometry,
        properties: {
          section_id: feature.properties.id,
          municipality_id: "mock",
          municipality: "Mijas (Mock)",
          district: feature.properties.district,
          section_number: String(index + 1).padStart(2, "0"),
          label_cliente: feature.properties.label,
          section_name: feature.properties.label,
          display_name: feature.properties.label,
          neighborhood: feature.properties.neighborhood,
          nombre_barrio: feature.properties.neighborhood,
          zone: "Fallback demo",
          label: feature.properties.label,
          population_total: feature.properties.population,
          population_density: Math.round(120 + feature.properties.intensity * 520),
          pct_65_plus: Number(((18 + feature.properties.medianAge * 0.6) / 100).toFixed(3)),
          average_age: feature.properties.medianAge,
          age_group:
            feature.properties.medianAge < 36
              ? 1
              : feature.properties.medianAge < 39
                ? 2
                : feature.properties.medianAge < 42
                  ? 3
                  : feature.properties.medianAge <= 44.5
                    ? 4
                    : 5,
          age_group_label:
            feature.properties.medianAge < 36
              ? "Very Young / Young"
              : feature.properties.medianAge < 39
                ? "Young Adult"
                : feature.properties.medianAge < 42
                  ? "Balanced"
                  : feature.properties.medianAge <= 44.5
                    ? "Mature"
                    : "Senior",
          age_color_key:
            feature.properties.medianAge < 36
              ? "very_young"
              : feature.properties.medianAge < 39
                ? "young_adult"
                : feature.properties.medianAge < 42
                  ? "balanced"
                  : feature.properties.medianAge <= 44.5
                    ? "mature"
                    : "senior",
          over_65_pct: Number(((18 + feature.properties.medianAge * 0.6) / 100).toFixed(3)),
          under_30_pct: Number(
            (Math.max(18, 44 - feature.properties.medianAge * 0.35) / 100).toFixed(3),
          ),
          density_level:
            feature.properties.intensity < 0.2
              ? "Very Low Density"
              : feature.properties.intensity < 0.4
                ? "Low Density"
                : feature.properties.intensity < 0.6
                  ? "Moderate / Medium Density"
                  : feature.properties.intensity < 0.8
                    ? "High Density"
                    : "Very High / Ultra-High Density",
          pct_foreign_born: feature.properties.foreignBorn,
          turnout: feature.properties.turnout,
          renta_media_persona: individualIncome,
          renta_media_hogar: householdIncome,
          income_quintile: incomeQuintile,
          income_level:
            incomeQuintile === 1
              ? "Very Low Income"
              : incomeQuintile === 2
                ? "Low Income"
                : incomeQuintile === 3
                  ? "Medium Income"
                  : incomeQuintile === 4
                    ? "High Income"
                    : "Very High Income",
          income_rank_municipal: index + 1,
          income_index: feature.properties.incomeIndex,
          winning_party: feature.properties.dominantParty,
        },
      };
    }),
  };
}
