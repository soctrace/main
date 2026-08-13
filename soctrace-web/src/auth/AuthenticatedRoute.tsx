import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { isSupabaseConfigured } from "@/lib/supabaseClient";

// Session-only boundary for products whose authorization is enforced by their
// own RLS-backed domain service. The analytical dashboard keeps ProtectedRoute.
export function AuthenticatedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { session, loading, bypassAuth } = useAuth();
  if (loading) return <div className="min-h-screen bg-[#05070c]" aria-label="Comprobando sesión" />;
  if (bypassAuth) return <>{children}</>;
  if (!isSupabaseConfigured || !session) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}
