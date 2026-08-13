import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CampaignCover, ChapterSection } from "@/features/campaigns/components/CampaignStory";
import { StickyChapterNav } from "@/features/campaigns/components/CampaignNavigation";
import { getCampaign } from "@/features/campaigns/data";

describe("Mijas campaign configuration", () => {
  const campaign = getCampaign("mijas-2027");
  it("loads a complete, uniquely-addressable commercial report", () => {
    expect(campaign).not.toBeNull(); expect(campaign?.chapters).toHaveLength(11);
    expect(new Set(campaign?.chapters.map(({ id }) => id)).size).toBe(11);
    expect(campaign?.chapters.map(({ id }) => id)).toContain("your-campaign");
    expect(campaign?.chapters.map(({ id }) => id)).not.toEqual(expect.arrayContaining(["opportunity-map", "priority-territories", "resource-allocation", "measurement-kpis"]));
    expect(campaign?.chapters.every(({ group }) => ["context", "diagnosis", "priorities", "strategy", "execution", "methodology"].includes(group))).toBe(true);
  });
  it("grouped navigation references only configured chapters", () => {
    render(<MemoryRouter><StickyChapterNav chapters={campaign!.chapters} /></MemoryRouter>);
    const links = screen.getAllByRole("link"); expect(links.length).toBeGreaterThanOrEqual(10);
    expect(links.every((link) => campaign!.chapters.some(({ id }) => link.getAttribute("href") === `#${id}`))).toBe(true);
  });
  it("presents verified scope without unfinished product language", () => {
    render(<MemoryRouter><CampaignCover campaign={campaign!} /></MemoryRouter>);
    expect(screen.getByText(/37 territorios · 12 procesos electorales/)).toBeVisible();
    expect(JSON.stringify(campaign)).not.toMatch(/internalNote|nota interna|plantilla en construcción|borrador/i);
  });
  it("renders a chapter without optional visual data", () => {
    const chapter = { ...campaign!.chapters[1], map: undefined, visual: undefined };
    render(<MemoryRouter><ChapterSection chapter={chapter} evidence={campaign!.evidence} /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: chapter.title })).toBeVisible();
  });
});
