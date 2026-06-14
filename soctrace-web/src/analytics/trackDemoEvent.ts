import type { SocTraceRole } from "@/auth/accessControl";
import { getAuthorizedUser } from "@/auth/accessControl";
import { supabase } from "@/lib/supabaseClient";

const SESSION_KEY = "soctrace_demo_session_id";

export type DemoEventType =
  | "login_success"
  | "login_denied"
  | "dashboard_enter"
  | "dashboard_exit"
  | "heartbeat";

export function getOrCreateDemoSessionId() {
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const next = crypto.randomUUID();
  window.sessionStorage.setItem(SESSION_KEY, next);
  return next;
}

export function clearDemoSessionId() {
  window.sessionStorage.removeItem(SESSION_KEY);
}

export async function trackDemoEvent(
  eventType: DemoEventType,
  email?: string | null,
  metadata: Record<string, unknown> = {},
) {
  if (!supabase || !email) return;

  const access = getAuthorizedUser(email);
  const role: SocTraceRole | "unauthorized" = access?.role ?? "unauthorized";

  const { error } = await supabase.from("demo_access_logs").insert({
    email,
    role,
    event_type: eventType,
    session_id: getOrCreateDemoSessionId(),
    pathname: window.location.pathname,
    user_agent: window.navigator.userAgent,
    metadata,
  });

  if (error) {
    console.debug("[soctrace] demo_access_logs insert skipped", error.message);
  }
}
