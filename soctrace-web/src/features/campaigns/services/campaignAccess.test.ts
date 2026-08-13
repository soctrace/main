import { beforeEach, describe, expect, it, vi } from "vitest";

const from = vi.hoisted(() => vi.fn());
vi.mock("@/lib/supabaseClient", () => ({ supabase: { from }, isSupabaseConfigured: true }));
import { getCampaignAccess, listAccessibleCampaigns } from "@/features/campaigns/services/campaignAccess";

function query(result: unknown) {
  const builder: Record<string, unknown> = {};
  for (const method of ["select", "eq", "is", "in"]) builder[method] = vi.fn(() => builder);
  builder.maybeSingle = vi.fn().mockResolvedValue(result);
  builder.returns = vi.fn().mockResolvedValue(result);
  return builder;
}

describe("Supabase campaign access service", () => {
  beforeEach(() => from.mockReset());
  it("authorizes an active viewer only for a published campaign", async () => {
    from.mockReturnValueOnce(query({ data: { id: "c1", slug: "mijas-2027", name: "Mijas 2027", municipality: "Mijas", election_label: null, status: "published", published_at: "2026-01-01" }, error: null })).mockReturnValueOnce(query({ data: { campaign_id: "c1", role: "viewer" }, error: null }));
    await expect(getCampaignAccess("mijas-2027", "u1")).resolves.toMatchObject({ state: "authorized", canEdit: false });
  });
  it("denies a viewer when the client publication is still draft", async () => {
    from.mockReturnValueOnce(query({ data: { id: "c1", slug: "mijas-2027", name: "Mijas 2027", municipality: "Mijas", election_label: null, status: "draft", published_at: null }, error: null })).mockReturnValueOnce(query({ data: { campaign_id: "c1", role: "viewer" }, error: null }));
    await expect(getCampaignAccess("mijas-2027", "u1")).resolves.toEqual({ state: "denied", reason: "not-published" });
  });
  it("treats RLS-hidden and revoked memberships as denied", async () => {
    from.mockReturnValueOnce(query({ data: null, error: null }));
    await expect(getCampaignAccess("mijas-2027", "u1")).resolves.toEqual({ state: "denied", reason: "not-member" });
  });
  it("does not grant access on a Supabase error", async () => {
    from.mockReturnValueOnce(query({ data: null, error: { message: "offline" } }));
    await expect(getCampaignAccess("mijas-2027", "u1")).resolves.toMatchObject({ state: "error" });
  });
  it("omits a membership when RLS hides its revoked, expired, or archived campaign", async () => {
    from.mockReturnValueOnce(query({ data: [{ campaign_id: "c1", role: "viewer" }], error: null })).mockReturnValueOnce(query({ data: [], error: null }));
    await expect(listAccessibleCampaigns("u1")).resolves.toEqual({ campaigns: [], error: null });
  });
});
