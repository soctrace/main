import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { canAccessDashboard } from "@/auth/accessControl";
import { isSupabaseConfigured } from "@/lib/supabaseClient";

export function ProtectedRoute({ children }: { children: JSX.Element }) {
  const location = useLocation();
  const { session, loading, email, bypassAuth } = useAuth();

  if (loading) {
    return <div className="min-h-screen bg-[#05070c]" />;
  }

  if (bypassAuth) {
    return children;
  }

  if (!isSupabaseConfigured || !session || !canAccessDashboard(email)) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
