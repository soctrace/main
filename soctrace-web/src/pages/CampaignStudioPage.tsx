import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, ArrowUpRight, Clock3, Construction, LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { getCampaigns } from "@/features/campaigns/data";
import { listAccessibleCampaigns, type AccessibleCampaign } from "@/features/campaigns/services/campaignAccess";

function developmentCampaigns(): AccessibleCampaign[] {
  return getCampaigns().map((campaign) => ({ id: `development-${campaign.id}`, slug: campaign.slug, name: campaign.title, municipality: campaign.municipality, electionLabel: "Municipales 2027", status: "draft", publishedAt: null, role: "owner" }));
}

export function CampaignStudioPage() {
  const navigate = useNavigate();
  const { session, bypassAuth, signOut } = useAuth();
  const [campaigns, setCampaigns] = useState<AccessibleCampaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true; setLoading(true); setError(null);
    if (bypassAuth) { setCampaigns(developmentCampaigns()); setLoading(false); return () => { active = false; }; }
    listAccessibleCampaigns(session?.user.id ?? "").then((result) => { if (!active) return; setCampaigns(result.campaigns); setError(result.error); setLoading(false); });
    return () => { active = false; };
  }, [bypassAuth, session?.user.id]);
  return <div className="campaign-studio-shell"><header className="campaign-studio-header"><Link to="/dashboard"><ArrowLeft className="h-4 w-4" /> Panel territorial</Link><a href="/" className="brand-mark">soctrace</a><button onClick={async () => { await signOut(); navigate("/login", { replace: true }); }}><LogOut className="h-4 w-4" /> Salir</button></header><main className="campaign-studio-main"><p className="campaign-kicker">Campaign Studio</p><h1>Campañas</h1><p className="campaign-studio-lead">Solo aparecen las campañas asignadas a tu cuenta. La edición estará disponible en una próxima versión.</p>
    {loading ? <p className="mt-12 text-slate-400" role="status">Cargando campañas asignadas…</p> : null}
    {error ? <div className="mt-12 flex items-center gap-3 text-amber-200" role="alert"><AlertTriangle className="h-5 w-5" />{error}</div> : null}
    {!loading && !error && campaigns.length === 0 ? <p className="mt-12 text-slate-400">No tienes campañas activas asignadas.</p> : null}
    <div className="campaign-studio-list">{campaigns.map((campaign) => <article key={campaign.id} className="campaign-studio-card"><div className="campaign-card-art"><span>{campaign.municipality}</span><i /><b>{campaign.electionLabel?.match(/\d{4}/)?.[0] ?? "—"}</b></div><div className="campaign-studio-copy"><div><span className="campaign-placeholder-badge">{campaign.status}</span><span className="campaign-card-status"><Clock3 className="h-3.5 w-3.5" /> {campaign.status === "published" ? "Publicado" : "En construcción"}</span></div><h2>{campaign.name}</h2><p>{campaign.electionLabel ?? campaign.municipality} · acceso {campaign.role}</p><div className="campaign-completion"><span><i style={{ width: campaign.status === "published" ? "100%" : "18%" }} /></span><small>{campaign.status === "published" ? "Informe publicado" : "Progreso de ejemplo · 18%"}</small></div><div className="campaign-card-actions"><Link to={`/campaigns/${campaign.slug}`}>Abrir informe <ArrowUpRight className="h-4 w-4" /></Link><button disabled><Construction className="h-4 w-4" /> Gestionar campaña · próximamente</button></div></div></article>)}</div></main></div>;
}
