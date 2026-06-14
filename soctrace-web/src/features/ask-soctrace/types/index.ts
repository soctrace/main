import type { SectionFeatureCollection } from "@/types/api";

export type AskSocTraceIntent =
  | "simple_electoral_ranking"
  | "party_performance_by_section_across_elections"
  | "historical_party_average"
  | "cross_variable_similarity"
  | "multi_step_electoral_socioeconomic_analysis"
  | "demographic_analysis"
  | "income_analysis"
  | "data_lookup"
  | "section_comparison"
  | "electoral_calculation"
  | "forecast_question"
  | "methodology_explanation"
  | "strategic_interpretation"
  | "unknown_or_unsupported";

export type AskSocTraceTable = {
  title: string;
  columns: string[];
  rows: string[][];
};

export type AskSocTraceChartSpec = {
  kind: "bar" | "line" | "scatter" | "map" | "table" | "none" | string;
  title: string;
  x?: string;
  y?: string;
  series?: string;
  secondaryValue?: string;
  value?: string | number;
  data: Record<string, unknown>[];
};

export type AskResponseMode = "simple" | "detailed" | "debug";

export type AskSocTraceEntity = {
  name: string;
  description?: string | null;
  value?: string | number | null;
};

export type AskSocTraceResponse = {
  answer: string;
  mode: AskResponseMode;
  conversation_id?: string | null;
  session_id?: string | null;
  result_type?: string | null;
  entities?: AskSocTraceEntity[];
  short_caveat?: string | null;
  summary: string;
  title?: string | null;
  methodology?: string | null;
  metrics?: Array<{
    label: string;
    value: string | number;
    description?: string | null;
  }>;
  findings?: Array<{
    label: string;
    description: string;
    evidence?: string | null;
  }>;
  caveats?: string[];
  suggested_follow_ups?: string[];
  ctas?: Array<{ label: string; question: string }>;
  confidence_level: "high" | "medium" | "low";
  used_tools: string[];
  data_origin: string[];
  methodological_notes: string[];
  table?: AskSocTraceTable | null;
  chart_spec?: AskSocTraceChartSpec | null;
  debug?: unknown;
  audit_id: string;
};

export type AskSocTraceAgentResponse = {
  answer: string;
  mode?: AskResponseMode;
  conversationId?: string | null;
  sessionId?: string | null;
  resultType?: string | null;
  result_type?: string | null;
  entities?: AskSocTraceEntity[];
  shortCaveat?: string | null;
  short_caveat?: string | null;
  data?: unknown;
  metadata?: unknown;
  methodology?: string | null;
  caveats?: string[];
  sources?: string[];
  suggestedFollowUps?: string[];
  suggested_followups?: string[];
  suggested_follow_ups?: string[];
  table?: {
    title?: string;
    columns: string[];
    rows: unknown[][] | Record<string, unknown>[];
  } | null;
  chartSpec?: Record<string, unknown> | null;
  chart_spec?: Record<string, unknown> | null;
  sqlDebug?: string | null;
  debug?: unknown;
  conversation_id?: string | null;
  session_id?: string | null;
};

export type AskSocTraceMessage =
  | {
      id: string;
      role: "user";
      content: string;
      createdAt: string;
      loading?: boolean;
      error?: string;
    }
  | {
      id: string;
      role: "assistant";
      content: string;
      createdAt: string;
      response: AskSocTraceResponse;
      loading?: boolean;
      error?: string;
    };

export type AskSocTraceContext = {
  municipalityId: string;
  currentCollection: SectionFeatureCollection | null;
  conversationId?: string;
  sessionId?: string;
  activeYear?: number | null;
  activeLayer?: string | null;
  selectedSectionId?: string | null;
};
