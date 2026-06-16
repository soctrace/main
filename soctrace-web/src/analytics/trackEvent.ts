import { supabase } from "@/lib/supabaseClient";

export type UserEventType =
  | "dashboard_view"
  | "section_view"
  | "layer_change"
  | "ask_query";

export type UserEventMetadata = Record<string, unknown>;

export type UserEvent = {
  event_type: UserEventType;
  page?: string | null;
  section_id?: string | null;
  section_name?: string | null;
  layer?: string | null;
  year?: string | number | null;
  question?: string | null;
  metadata?: UserEventMetadata | null;
};

function currentPage() {
  if (typeof window === "undefined") return null;
  return `${window.location.pathname}${window.location.search}`;
}

function userAgent() {
  if (typeof window === "undefined") return null;
  return window.navigator.userAgent;
}

function numericYear(year: UserEvent["year"]) {
  if (year === null || year === undefined || year === "") return null;
  const value = typeof year === "number" ? year : Number.parseInt(String(year), 10);
  return Number.isFinite(value) ? value : null;
}

function safeMetadata(metadata: UserEventMetadata | null | undefined): UserEventMetadata {
  if (!metadata) return {};

  try {
    return JSON.parse(JSON.stringify(metadata)) as UserEventMetadata;
  } catch {
    return { serialization_error: true };
  }
}

export async function trackEvent(event: UserEvent) {
  if (!supabase) return;

  try {
    const { data, error: userError } = await supabase.auth.getUser();
    if (userError || !data.user) return;

    const { error } = await supabase.from("user_events").insert({
      user_id: data.user.id,
      email: data.user.email ?? null,
      event_type: event.event_type,
      page: event.page ?? currentPage(),
      section_id: event.section_id ?? null,
      section_name: event.section_name ?? null,
      layer: event.layer ?? null,
      year: numericYear(event.year),
      question: event.question ?? null,
      metadata: safeMetadata(event.metadata),
      user_agent: userAgent(),
    });

    if (error && import.meta.env.DEV) {
      console.debug("[soctrace] user_events insert skipped", error.message);
    }
  } catch (error) {
    if (import.meta.env.DEV) {
      console.debug("[soctrace] user_events tracking skipped", error);
    }
  }
}
