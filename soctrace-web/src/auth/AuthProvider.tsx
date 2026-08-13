import type { Session } from "@supabase/supabase-js";
import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import type { SocTraceAccess } from "@/auth/accessControl";
import { getAuthorizedUser, mockUser, normalizeDemoAccessEmail } from "@/auth/accessControl";
import { clearDemoSessionId, trackDemoEvent } from "@/lib/demoAnalytics";
import { shouldBypassAuth } from "@/lib/authConfig";
import { supabase } from "@/lib/supabaseClient";

type AuthContextValue = {
  session: Session | null;
  user: SocTraceAccess | Session["user"] | null;
  email: string | null;
  authorizedUser: SocTraceAccess | null;
  role: SocTraceAccess["role"] | null;
  access: SocTraceAccess["access"] | null;
  loading: boolean;
  bypassAuth: boolean;
  signIn: (email: string, password: string) => Promise<{ session: Session | null; error: string | null }>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const testSessionEnabled = import.meta.env.DEV && import.meta.env.VITE_CAMPAIGN_TEST_MODE === "true";
    const testSessionRequested = testSessionEnabled && new URLSearchParams(window.location.search).get("auditSession") === "member";
    if (testSessionRequested) {
      setSession({ user: { id: "00000000-0000-4000-8000-000000000001", email: "browser-test@soctrace.invalid", app_metadata: {}, user_metadata: {}, aud: "authenticated", created_at: new Date(0).toISOString() }, access_token: "development-test-token", refresh_token: "development-test-refresh", expires_in: 3600, token_type: "bearer" } as Session);
      setLoading(false);
      return undefined;
    }

    if (shouldBypassAuth) {
      setLoading(false);
      return undefined;
    }

    if (!supabase) {
      setLoading(false);
      return undefined;
    }

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      setLoading(false);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
    });

    return () => {
      mounted = false;
      data.subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => {
      const email = shouldBypassAuth ? mockUser.email : normalizeDemoAccessEmail(session?.user);
      const authorizedUser = shouldBypassAuth ? mockUser : getAuthorizedUser(session?.user);
      return {
        session,
        user: shouldBypassAuth ? mockUser : session?.user ?? null,
        email,
        authorizedUser,
        role: authorizedUser?.role ?? null,
        access: authorizedUser?.access ?? null,
        loading,
        bypassAuth: shouldBypassAuth,
        signIn: async (loginEmail: string, password: string) => {
          if (!supabase) {
            return { session: null, error: "Supabase Auth no está configurado todavía." };
          }
          const { data, error } = await supabase.auth.signInWithPassword({
            email: loginEmail,
            password,
          });
          setSession(data.session);
          return { session: data.session, error: error?.message ?? null };
        },
        signOut: async () => {
          await trackDemoEvent("dashboard_exit", email);
          clearDemoSessionId();
          if (!shouldBypassAuth) {
            await supabase?.auth.signOut();
          }
          setSession(null);
        },
      };
    },
    [loading, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
