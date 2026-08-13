import { supabase } from "@/lib/supabaseClient";

export type CampaignRole = "owner" | "editor" | "viewer";
export type CampaignStatus = "draft" | "review" | "published" | "archived";

export type AccessibleCampaign = {
  id: string;
  slug: string;
  name: string;
  municipality: string;
  electionLabel: string | null;
  status: CampaignStatus;
  publishedAt: string | null;
  role: CampaignRole;
};

export type CampaignAccessResult =
  | { state: "authorized"; campaign: AccessibleCampaign; canView: true; canEdit: boolean }
  | { state: "denied"; reason: "not-member" | "not-published" | "revoked-or-expired" }
  | { state: "error"; message: string };

type CampaignRow = {
  id: string; slug: string; name: string; municipality: string;
  election_label: string | null; status: CampaignStatus; published_at: string | null;
};

type MembershipRow = { campaign_id: string; role: CampaignRole };

function mapCampaign(row: CampaignRow, role: CampaignRole): AccessibleCampaign {
  return { id: row.id, slug: row.slug, name: row.name, municipality: row.municipality, electionLabel: row.election_label, status: row.status, publishedAt: row.published_at, role };
}

export async function getCampaignAccess(slug: string, userId: string): Promise<CampaignAccessResult> {
  if (!supabase || !userId) return { state: "error", message: "El servicio de acceso a campañas no está configurado." };
  const { data: campaign, error: campaignError } = await supabase.from("campaigns").select("id,slug,name,municipality,election_label,status,published_at").eq("slug", slug).maybeSingle<CampaignRow>();
  if (campaignError) return { state: "error", message: "No se pudo verificar el acceso a la campaña." };
  // RLS intentionally makes absent, unrelated, revoked, expired and archived campaigns indistinguishable.
  if (!campaign) return { state: "denied", reason: "not-member" };
  const { data: membership, error: membershipError } = await supabase.from("campaign_memberships").select("campaign_id,role").eq("campaign_id", campaign.id).eq("user_id", userId).is("revoked_at", null).maybeSingle<MembershipRow>();
  if (membershipError) return { state: "error", message: "No se pudo verificar la membresía de campaña." };
  if (!membership) return { state: "denied", reason: "revoked-or-expired" };
  const canEdit = membership.role === "owner" || membership.role === "editor";
  if (!canEdit && campaign.status !== "published") return { state: "denied", reason: "not-published" };
  return { state: "authorized", campaign: mapCampaign(campaign, membership.role), canView: true, canEdit };
}

export async function listAccessibleCampaigns(userId: string): Promise<{ campaigns: AccessibleCampaign[]; error: string | null }> {
  if (!supabase || !userId) return { campaigns: [], error: "El servicio de campañas no está configurado." };
  const { data: memberships, error: membershipError } = await supabase.from("campaign_memberships").select("campaign_id,role").eq("user_id", userId).is("revoked_at", null).returns<MembershipRow[]>();
  if (membershipError) return { campaigns: [], error: "No se pudieron cargar las campañas asignadas." };
  if (!memberships?.length) return { campaigns: [], error: null };
  const roles = new Map(memberships.map((membership) => [membership.campaign_id, membership.role]));
  const { data, error } = await supabase.from("campaigns").select("id,slug,name,municipality,election_label,status,published_at").in("id", [...roles.keys()]).returns<CampaignRow[]>();
  if (error) return { campaigns: [], error: "No se pudieron cargar las campañas asignadas." };
  return { campaigns: (data ?? []).map((campaign) => mapCampaign(campaign, roles.get(campaign.id) ?? "viewer")), error: null };
}

export function canViewCampaign(access: CampaignAccessResult): boolean { return access.state === "authorized" && access.canView; }
export function canEditCampaign(access: CampaignAccessResult): boolean { return access.state === "authorized" && access.canEdit; }
