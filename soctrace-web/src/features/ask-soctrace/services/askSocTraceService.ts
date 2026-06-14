import { askSocTraceAgent } from "@/lib/api";
import type { AskSocTraceAgentResponse, AskSocTraceContext, AskSocTraceResponse } from "../types";

const SHOW_DEBUG = import.meta.env.DEV && import.meta.env.VITE_ASK_SOCTRACE_DEBUG === "true";

function objectValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function normalizeQuestion(question: string) {
  const cleaned = question.trim().replace(/[.。]+$/, "");
  const withStart = cleaned.startsWith("¿") ? cleaned : `¿${cleaned}`;
  return withStart.endsWith("?") ? withStart : `${withStart}?`;
}

function normalizeSuggestedFollowUps(response: AskSocTraceAgentResponse) {
  const values = response.suggestedFollowUps ?? response.suggested_followups ?? response.suggested_follow_ups ?? [];
  return Array.from(new Set(values.map(normalizeQuestion)));
}

function normalizeCtas(data: Record<string, unknown> | null) {
  const raw = data?.ctas;
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item) => {
    const cta = objectValue(item);
    const label = typeof cta?.label === "string" ? cta.label : null;
    const question = typeof cta?.question === "string" ? cta.question : null;
    return label && question ? [{ label, question }] : [];
  });
}

function normalizeTableRows(rows: unknown[][] | Record<string, unknown>[], columns: string[]) {
  return rows.map((row) => {
    if (Array.isArray(row)) return row.map((cell) => String(cell ?? ""));
    return columns.map((column) => String((row as Record<string, unknown>)[column] ?? ""));
  });
}

function buildTable(data: unknown): AskSocTraceResponse["table"] {
  if (!data || typeof data !== "object") return null;
  const payload = data as Record<string, unknown>;
  const ageRows = payload.rows ?? payload.sections;
  const ageRange = payload.ageRange as Record<string, unknown> | undefined;
  if (Array.isArray(ageRows) && ageRows.some((item) => typeof item === "object" && item && "estimatedAbstainers" in item)) {
    const minAge = ageRange?.minAge ?? "";
    const maxAge = ageRange?.maxAge ?? "";
    const ageLabel = ageRange?.label ?? (maxAge === null || maxAge === undefined ? `${minAge}+` : `${minAge}-${maxAge}`);
    return {
      title: "Ranking por sección",
      columns: [
        "Sección",
        `Personas ${ageLabel}`,
        "Abstención %",
        "Abstención estimada",
        "Votantes estimados",
      ],
      rows: ageRows.map((item) => {
        const row = item as Record<string, unknown>;
        return [
          String(row.sectionName ?? row.sectionId ?? ""),
          String(row.ageRangePopulation ?? ""),
          row.abstentionRatePct !== undefined ? `${Number(row.abstentionRatePct).toFixed(1)}%` : "",
          String(row.estimatedAbstainers ?? ""),
          String(row.estimatedVoters ?? ""),
        ];
      }),
    };
  }
  if (Array.isArray(ageRows) && ageRows.some((item) => typeof item === "object" && item && "winningParty" in item)) {
    return {
      title: "Fuerza más votada por sección",
      columns: ["Sección", "Ganador", "Voto ganador"],
      rows: ageRows.map((item) => {
        const row = item as Record<string, unknown>;
        return [
          String(row.sectionName ?? row.sectionId ?? ""),
          String(row.winningParty ?? row.winningPartyLabel ?? ""),
          row.winningVotePct !== undefined ? `${Number(row.winningVotePct).toFixed(1)}%` : "",
        ];
      }),
    };
  }
  if (Array.isArray(ageRows) && ageRows.some((item) => typeof item === "object" && item && ("individual_income" in item || "average_age" in item))) {
    return {
      title: "Perfil de las secciones recuperadas",
      columns: ["Sección", "Renta individual", "Renta hogar", "Edad media"],
      rows: ageRows.map((item) => {
        const row = item as Record<string, unknown>;
        return [
          String(row.section_name ?? row.sectionName ?? row.section_id ?? ""),
          row.individual_income !== undefined && row.individual_income !== null ? `${Math.round(Number(row.individual_income))} €` : "",
          row.household_income !== undefined && row.household_income !== null ? `${Math.round(Number(row.household_income))} €` : "",
          row.average_age !== undefined && row.average_age !== null ? `${Number(row.average_age).toFixed(1)}` : "",
        ];
      }),
    };
  }
  const topSections = payload.topSections;
  if (Array.isArray(topSections)) {
    return {
      title: "Resultado estructurado",
      columns: ["Seccion", "Valor", "Observaciones"],
      rows: topSections.map((item) => {
        const row = item as Record<string, unknown>;
        return [
          String(row.sectionName ?? row.sectionId ?? ""),
          row.averageVotePct !== undefined ? `${Number(row.averageVotePct).toFixed(1)}%` : "",
          row.electionsIncluded !== undefined ? `${row.electionsIncluded} elecciones` : "",
        ];
      }),
    };
  }
  const results = payload.results;
  if (Array.isArray(results)) {
    return {
      title: "Resultados disponibles",
      columns: ["Eleccion", "Voto valido", "Votos"],
      rows: results.map((item) => {
        const row = item as Record<string, unknown>;
        return [
          String(row.election ?? ""),
          row.votePct !== undefined ? `${Number(row.votePct).toFixed(1)}%` : "",
          row.votes !== undefined ? String(row.votes) : "",
        ];
      }),
    };
  }
  const winningQuotients = payload.winningQuotients;
  if (Array.isArray(winningQuotients)) {
    return {
      title: "Primeros cocientes ganadores",
      columns: ["Partido", "Divisor", "Cociente"],
      rows: winningQuotients.slice(0, 25).map((item) => {
        const row = item as Record<string, unknown>;
        return [String(row.party ?? ""), String(row.divisor ?? ""), Number(row.value ?? 0).toFixed(2)];
      }),
    };
  }
  return null;
}

function adaptAgentResponse(response: AskSocTraceAgentResponse): AskSocTraceResponse {
  const sources = response.sources ?? [];
  const data = objectValue(response.data);
  const responseMetadata = objectValue(response.metadata) ?? objectValue(data?.metadata);
  const totals = data?.totals as Record<string, unknown> | undefined;
  const chartSource = response.chartSpec ?? response.chart_spec;
  const suggestedFollowUps = normalizeSuggestedFollowUps(response);
  const ctas = normalizeCtas(data);
  const rawTable = response.table;
  const tableColumns = rawTable?.columns ?? [];
  const table = response.table ? {
    title: response.table.title ?? "Resultado analítico",
    columns: tableColumns,
    rows: normalizeTableRows(response.table.rows, tableColumns),
  } : buildTable(response.data);
  const chartPayload = objectValue(chartSource);
  const chartRows = Array.isArray(chartPayload?.rows)
    ? chartPayload.rows as Record<string, unknown>[]
    : table
      ? table.rows.map((row) => Object.fromEntries(table.columns.map((column, index) => [column, row[index]])))
      : (response.entities ?? []).map((entity) => ({
          name: entity.name,
          value: entity.value ?? entity.description ?? "",
        }));
  const hasAgeCohortTotals = Boolean(
    totals?.ageRangePopulation || totals?.estimatedAbstainers || totals?.estimatedVoters,
  );
  const metrics = hasAgeCohortTotals && totals ? [
    {
      label: "Cohorte total",
      value: String(totals.ageRangePopulation ?? ""),
      description: "Personas estimadas en el rango de edad.",
    },
    {
      label: "Abstención estimada",
      value: String(totals.estimatedAbstainers ?? ""),
      description: totals.weightedAbstentionRatePct !== undefined ? `${Number(totals.weightedAbstentionRatePct).toFixed(1)}% ponderado` : null,
    },
    {
      label: "Votantes estimados",
      value: String(totals.estimatedVoters ?? ""),
      description: "Cohorte menos abstención estimada.",
    },
  ] : [];
  return {
    answer: response.answer,
    mode: response.mode ?? "simple",
    conversation_id: response.conversationId ?? response.conversation_id ?? null,
    session_id: response.sessionId ?? response.session_id ?? null,
    result_type: response.resultType ?? response.result_type ?? null,
    entities: response.entities ?? [],
    short_caveat: response.shortCaveat ?? response.short_caveat ?? null,
    summary: response.methodology ?? "Respuesta generada desde herramientas internas aprobadas.",
    methodology: response.methodology,
    metrics,
    caveats: response.caveats ?? [],
    suggested_follow_ups: suggestedFollowUps,
    ctas,
    confidence_level: response.caveats?.length ? "medium" : "high",
    used_tools: sources.filter((source) => !source.includes(".")),
    data_origin: sources,
    methodological_notes: response.methodology ? [response.methodology] : [],
    table,
    chart_spec: chartPayload || chartRows.length ? {
      kind: String(chartPayload?.type ?? ((response.resultType ?? response.result_type) === "entity_list" ? "table" : "bar")),
      title: String(chartPayload?.title ?? table?.title ?? "Visualización Ask soctrace"),
      x: chartPayload?.x ? String(chartPayload.x) : undefined,
      y: chartPayload?.y ? String(chartPayload.y) : undefined,
      series: chartPayload?.series ? String(chartPayload.series) : undefined,
      secondaryValue: chartPayload?.secondaryValue ? String(chartPayload.secondaryValue) : undefined,
      value: chartPayload?.value as string | number | undefined,
      data: chartRows,
    } : null,
    debug: SHOW_DEBUG
      ? response.debug ?? responseMetadata ?? (response.sqlDebug ? { sqlDebug: response.sqlDebug, data: response.data } : null)
      : null,
    audit_id: "ask-soctrace-agent",
  };
}

export const askSocTraceService = {
  async ask(question: string, context: AskSocTraceContext): Promise<AskSocTraceResponse> {
    const response = await askSocTraceAgent({
      question,
      sessionId: context.sessionId ?? context.conversationId,
      conversationId: context.conversationId,
      session_id: context.sessionId ?? context.conversationId,
      conversation_id: context.conversationId,
      municipioId: context.municipalityId,
      activeMunicipality: context.municipalityId,
      activeYear: context.activeYear,
      activeLayer: context.activeLayer,
      selectedSectionId: context.selectedSectionId,
      locale: "es-ES",
    });
    return adaptAgentResponse(response);
  },
};
