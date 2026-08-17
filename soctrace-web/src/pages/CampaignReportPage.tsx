import { Navigate, useParams } from "react-router-dom";
import { useEffect } from "react";
import { CampaignFooter } from "@/features/campaigns/components/CampaignStory";
import { ReadingProgress } from "@/features/campaigns/components/CampaignNavigation";
import { ExecutiveCampaign, ExecutiveHeader } from "@/features/campaigns/components/ExecutiveCampaign";
import { getCampaign } from "@/features/campaigns/data";

export function CampaignReportPage() {
  const { slug = "" } = useParams();
  const campaign = getCampaign(slug);
  useEffect(() => {
    document.title = "Mijas 2027 · Campaign Intelligence · soctrace";
    const description = "Una lectura territorial, demográfica y electoral de Mijas para entender el municipio antes de decidir la campaña.";
    const upsert = (selector: string, attributes: Record<string, string>) => { let node = document.head.querySelector<HTMLMetaElement>(selector); if (!node) { node = document.createElement("meta"); document.head.appendChild(node); } Object.entries(attributes).forEach(([key, value]) => node!.setAttribute(key, value)); };
    upsert('meta[name="description"]', { name: "description", content: description });
    upsert('meta[property="og:title"]', { property: "og:title", content: document.title });
    upsert('meta[property="og:description"]', { property: "og:description", content: description });
    upsert('meta[property="og:type"]', { property: "og:type", content: "website" });
    upsert('meta[name="robots"]', { name: "robots", content: "noindex, nofollow" });
    return () => {
      document.title = "soctrace";
      document.head.querySelector('meta[name="robots"]')?.remove();
    };
  }, []);
  useEffect(() => {
    if (!campaign || !window.location.hash) return;
    const target = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    // Initial/deferred hash restoration must be immediate: animated restoration can
    // leave browser history and assistive technology between chapters.
    target?.scrollIntoView({ behavior: "auto", block: "start" });
  }, [campaign]);
  if (!campaign) return <Navigate to="/dashboard/campaigns" replace />;
  return <div className="campaign-shell"><ReadingProgress/><ExecutiveHeader/><main><ExecutiveCampaign/></main><CampaignFooter campaign={campaign}/></div>;
}
