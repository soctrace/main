import { mockSectionFeatures } from "@/data/mockSections";

export type KpiMetric = {
  label: string;
  value: string;
  tone: "violet" | "cyan" | "green" | "orange";
};

export type AgePyramidDatum = {
  label: string;
  men: number;
  women: number;
};

export type LinePoint = {
  label: string;
  value: number;
};

export type PartyResult = {
  party: string;
  value: number;
  color: string;
};

export type SectionDetail = {
  summary: string;
  kpis: KpiMetric[];
  agePyramid: AgePyramidDatum[];
  turnoutEvolution: LinePoint[];
  partyResults: PartyResult[];
  housingSignals: { label: string; value: string }[];
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export const mockSectionDetails = Object.fromEntries(
  mockSectionFeatures.map((feature, index) => {
    const section = feature.properties;
    const agePivot = clamp((section.medianAge - 30) / 22, 0, 1);
    const turnoutDrift = clamp((section.turnout - 56) / 20, 0, 1);
    const progressiveLean = clamp(section.foreignBorn / 34 + (0.35 - section.intensity), 0.08, 0.74);
    const conservativeLean = clamp(section.incomeIndex / 180 + turnoutDrift * 0.2, 0.12, 0.58);
    const baseOthers = 0.08 + (index % 5) * 0.01;
    const pp = Number((conservativeLean * 39).toFixed(1));
    const psoe = Number((progressiveLean * 31).toFixed(1));
    const vox = Number((clamp((section.incomeIndex - 85) / 80, 0, 0.42) * 24).toFixed(1));
    const masMadrid = Number((clamp(section.foreignBorn / 28, 0.1, 0.42) * 27).toFixed(1));
    const others = Number((100 - pp - psoe - vox - masMadrid - baseOthers).toFixed(1));

    const agePyramid: AgePyramidDatum[] = [
      { label: "85+", men: 2 + agePivot * 3, women: 3 + agePivot * 4.4 },
      { label: "65-84", men: 4 + agePivot * 6, women: 5 + agePivot * 6.5 },
      { label: "50-64", men: 7 + agePivot * 5, women: 8 + agePivot * 4.8 },
      { label: "35-49", men: 9 + (1 - agePivot) * 2, women: 9.4 + (1 - agePivot) * 2.2 },
      { label: "20-34", men: 10 + section.intensity * 4.6, women: 10.4 + section.intensity * 4.2 },
      { label: "0-19", men: 6 + (1 - agePivot) * 3, women: 5.7 + (1 - agePivot) * 2.7 },
    ].map((bucket) => ({
      ...bucket,
      men: Number(bucket.men.toFixed(1)),
      women: Number(bucket.women.toFixed(1)),
    }));

    const turnoutEvolution: LinePoint[] = [
      { label: "2015", value: Number((section.turnout - 3.2).toFixed(1)) },
      { label: "2019", value: Number((section.turnout - 0.7 + (index % 3) * 0.9).toFixed(1)) },
      { label: "2023", value: section.turnout },
    ];

    const detail: SectionDetail = {
      summary:
        section.turnout > 66
          ? "Young, educated and highly mobilized. Competitive territory with room for micro-targeted persuasion."
          : "Mixed socio-demographic profile with latent turnout upside. Worth tracking with layered demographic filters.",
      kpis: [
        {
          label: "Population",
          value: section.population.toLocaleString("en-US"),
          tone: "violet",
        },
        {
          label: "Median Age",
          value: section.medianAge.toFixed(1),
          tone: "green",
        },
        {
          label: "Foreign-born",
          value: `${section.foreignBorn.toFixed(1)}%`,
          tone: "orange",
        },
        {
          label: "Turnout 2023",
          value: `${section.turnout.toFixed(1)}%`,
          tone: "cyan",
        },
      ],
      agePyramid,
      turnoutEvolution,
      partyResults: [
        { party: "PP", value: pp, color: "#3B82F6" },
        { party: "PSOE", value: psoe, color: "#FB7185" },
        { party: "VOX", value: vox, color: "#5CD38B" },
        { party: "Más Madrid", value: masMadrid, color: "#38BDF8" },
        { party: "Others", value: Number(Math.max(others, 5.8).toFixed(1)), color: "#94A3B8" },
      ],
      housingSignals: [
        { label: "Rent pressure", value: `${section.housingPressure.toFixed(1)} / 100` },
        { label: "Income index", value: `${section.incomeIndex}` },
        { label: "Dominant signal", value: section.dominantParty },
      ],
    };

    return [section.id, detail];
  }),
) as Record<string, SectionDetail>;
