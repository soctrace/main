import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CampaignAccessResult } from "@/features/campaigns/services/campaignAccess";

const auth = vi.hoisted(() => ({ session: null as { user: { id: string } } | null, loading: false, bypassAuth: false, signOut: vi.fn() }));
const publication = vi.hoisted(() => ({ public: true }));
const accessMock = vi.hoisted(() => vi.fn<() => Promise<CampaignAccessResult>>());
vi.mock("@/auth/AuthProvider", () => ({ useAuth: () => auth }));
vi.mock("@/features/campaigns/data", async (original) => ({ ...(await original()), isPublicCampaign: () => publication.public }));
vi.mock("@/features/campaigns/services/campaignAccess", async (original) => ({ ...(await original()), getCampaignAccess: accessMock }));
import { CampaignRoute } from "@/features/campaigns/components/CampaignAccess";

function LoginProbe() { const location = useLocation(); return <pre data-testid="return-location">{JSON.stringify(location.state)}</pre>; }
function renderRoute(initial = "/campaigns/mijas-2027?edition=client#opportunity-map") {
  return render(<MemoryRouter initialEntries={[initial]}><Routes><Route path="/login" element={<LoginProbe />} /><Route path="/campaigns/:slug" element={<CampaignRoute><div>REPORT CONTENT</div></CampaignRoute>} /></Routes></MemoryRouter>);
}

describe("CampaignRoute", () => {
  beforeEach(() => { auth.session = null; auth.loading = false; auth.bypassAuth = false; auth.signOut.mockReset(); publication.public = true; accessMock.mockReset(); });
  it("renders Mijas 2027 for a logged-out visitor without checking membership", () => {
    renderRoute();
    expect(screen.getByText("REPORT CONTENT")).toBeVisible();
    expect(accessMock).not.toHaveBeenCalled();
  });
  it("renders for an authorized published member", async () => {
    publication.public = false;
    auth.session = { user: { id: "member-id" } };
    accessMock.mockResolvedValue({ state: "authorized", canView: true, canEdit: false, campaign: { id: "campaign-id", slug: "mijas-2027", name: "Mijas 2027", municipality: "Mijas", electionLabel: null, status: "published", publishedAt: "2026-01-01", role: "viewer" } });
    renderRoute("/campaigns/mijas-2027");
    expect(await screen.findByText("REPORT CONTENT")).toBeVisible();
  });
  it.each(["not-member", "revoked-or-expired", "not-published"] as const)("denies %s without fallback", async (reason) => {
    publication.public = false;
    auth.session = { user: { id: "member-id" } }; accessMock.mockResolvedValue({ state: "denied", reason }); renderRoute("/campaigns/mijas-2027");
    expect(await screen.findByText("Acceso restringido")).toBeVisible(); expect(screen.queryByText("REPORT CONTENT")).not.toBeInTheDocument();
  });
  it("shows understandable loading and service-error states", async () => {
    publication.public = false;
    auth.session = { user: { id: "member-id" } }; let resolveAccess!: (value: CampaignAccessResult) => void;
    accessMock.mockReturnValue(new Promise((resolve) => { resolveAccess = resolve; })); renderRoute("/campaigns/mijas-2027");
    expect(screen.getByRole("status")).toHaveTextContent("Comprobando acceso");
    resolveAccess({ state: "error", message: "service unavailable" });
    expect(await screen.findByText("No hemos podido comprobar tu acceso")).toBeVisible();
  });
  it("does not expose an unknown campaign configuration", async () => {
    publication.public = false;
    renderRoute("/campaigns/unknown-2027");
    expect(screen.getByTestId("return-location")).toHaveTextContent("/campaigns/unknown-2027");
    expect(screen.queryByText("REPORT CONTENT")).not.toBeInTheDocument();
    expect(accessMock).not.toHaveBeenCalled();
  });
});
