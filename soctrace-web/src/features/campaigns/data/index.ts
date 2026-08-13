import { mijas2027Campaign } from "@/features/campaigns/data/mijas-2027";
import type { CampaignReport } from "@/features/campaigns/types";

const campaigns: Record<string, CampaignReport> = { [mijas2027Campaign.slug]: mijas2027Campaign };

export function getCampaign(slug: string): CampaignReport | null {
  return campaigns[slug] ?? null;
}

export function getCampaigns(): CampaignReport[] {
  return Object.values(campaigns);
}
