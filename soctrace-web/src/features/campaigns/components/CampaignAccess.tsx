import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, LockKeyhole, LogOut, RefreshCw } from "lucide-react";
import { Navigate, useLocation, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { getCampaign, isPublicCampaign } from "@/features/campaigns/data";
import { getCampaignAccess, type CampaignAccessResult } from "@/features/campaigns/services/campaignAccess";

function AccessState({ kind, retry }: { kind: "denied" | "error"; retry?: () => void }) {
  const navigate = useNavigate();
  const { signOut } = useAuth();
  const denied = kind === "denied";
  return <main className="campaign-shell grid min-h-screen place-items-center px-6"><section className="max-w-xl rounded-[2rem] border border-white/10 bg-white/[0.035] p-8 text-center sm:p-12" role={denied ? "status" : "alert"}>
    {denied ? <LockKeyhole className="mx-auto h-9 w-9 text-orange-300" /> : <AlertTriangle className="mx-auto h-9 w-9 text-amber-300" />}
    <p className="mt-6 text-xs font-semibold uppercase tracking-[0.25em] text-orange-200">{denied ? "Acceso restringido" : "Verificación no disponible"}</p>
    <h1 className="mt-3 text-4xl text-white">{denied ? "Esta campaña no está asignada a tu cuenta" : "No hemos podido comprobar tu acceso"}</h1>
    <p className="mt-5 leading-7 text-slate-300">{denied ? "Tu sesión es válida, pero no incluye permiso activo para consultar este informe, o el informe todavía no está publicado para clientes." : "No se ha concedido acceso por defecto. Vuelve a intentarlo cuando se restablezca el servicio."}</p>
    <div className="mt-8 flex flex-wrap justify-center gap-3">
      {retry ? <button className="campaign-button-secondary" onClick={retry}><RefreshCw className="h-4 w-4" /> Reintentar</button> : null}
      <button className="campaign-button-secondary" onClick={() => navigate("/dashboard/campaigns")}>Volver a campañas</button>
      <button className="campaign-button-secondary" onClick={async () => { await signOut(); navigate("/login", { replace: true }); }}><LogOut className="h-4 w-4" /> Cerrar sesión</button>
    </div>
  </section></main>;
}

function developmentFixture(slug: string, fixture: string | null): CampaignAccessResult | null {
  if (!import.meta.env.DEV) return null;
  if (["denied", "revoked"].includes(fixture ?? "")) return { state: "denied", reason: fixture === "revoked" ? "revoked-or-expired" : "not-member" };
  if (fixture === "error") return { state: "error", message: "Controlled campaign access error." };
  if (fixture === "member") return { state: "authorized", canView: true, canEdit: false, campaign: { id: "development-fixture", slug, name: "Mijas 2027", municipality: "Mijas", electionLabel: "Municipales 2027", status: "published", publishedAt: new Date(0).toISOString(), role: "viewer" } };
  return null;
}

export function CampaignRoute({ children }: { children: ReactNode }) {
  const { slug = "" } = useParams();
  const location = useLocation();
  const { session, loading, bypassAuth } = useAuth();
  const [access, setAccess] = useState<CampaignAccessResult | null>(null);
  const [attempt, setAttempt] = useState(0);
  const fixture = import.meta.env.DEV ? new URLSearchParams(location.search).get("auditAccess") : null;
  const knownCampaign = Boolean(getCampaign(slug));
  const publicCampaign = isPublicCampaign(slug);

  useEffect(() => {
    let active = true;
    setAccess(null);
    if (publicCampaign) return () => { active = false; };
    if (loading || !knownCampaign || (!session && !bypassAuth) || fixture === "loading") return () => { active = false; };
    const controlled = developmentFixture(slug, fixture);
    if (controlled) { setAccess(controlled); return () => { active = false; }; }
    if (bypassAuth) { setAccess(developmentFixture(slug, "member")); return () => { active = false; }; }
    getCampaignAccess(slug, session?.user.id ?? "").then((result) => { if (active) setAccess(result); });
    return () => { active = false; };
  }, [attempt, bypassAuth, fixture, knownCampaign, loading, publicCampaign, session, slug]);

  if (publicCampaign && knownCampaign) return <>{children}</>;
  if (loading) return <div className="min-h-screen bg-[#05070c]" aria-label="Comprobando sesión" />;
  if (!bypassAuth && !session) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!knownCampaign) return <AccessState kind="denied" />;
  if (!access) return <div className="campaign-shell grid min-h-screen place-items-center text-sm text-slate-400" role="status">Comprobando acceso a la campaña…</div>;
  if (access.state === "error") return <AccessState kind="error" retry={() => setAttempt((value) => value + 1)} />;
  if (access.state === "denied") return <AccessState kind="denied" />;
  return <>{children}</>;
}
