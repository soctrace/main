export type EvidenceStatus = "pending-data" | "pending-validation" | "example";

export type CampaignEvidence = {
  id: string;
  sourceReference?: string;
  metricReference?: string;
  territorialScope?: string;
  referenceYear?: number;
  status: EvidenceStatus;
  confidence?: "pending" | "low" | "medium" | "high";
  clientExplanation: string;
};

export type CampaignMapKind =
  | "municipality"
  | "population"
  | "evolution"
  | "electoral"
  | "opportunity"
  | "clusters"
  | "priority";

export type NarrativeBlock = {
  eyebrow?: string;
  title: string;
  body: string;
  finding?: string;
  recommendation?: string;
  evidenceId?: string;
};

export type CampaignChapter = {
  id: string;
  number: string;
  navLabel: string;
  group: "context" | "diagnosis" | "priorities" | "strategy" | "execution" | "methodology";
  title: string;
  introduction: string;
  blocks: NarrativeBlock[];
  map?: CampaignMapKind;
  visual?: "profiles" | "messages" | "budget" | "timeline" | "kpis" | "scenarios" | "methodology";
};

export type CampaignReport = {
  id: string;
  slug: string;
  municipality: string;
  title: string;
  productName: string;
  subtitle: string;
  preparedBy: string;
  status: "template" | "draft" | "published";
  statusLabel: string;
  publicationStatus: string;
  branding: { accent: string; secondary: string };
  access: { policy: "supabase-membership"; campaignId: string };
  chapters: CampaignChapter[];
  evidence: CampaignEvidence[];
  sources: { id: string; label: string; status: EvidenceStatus }[];
};
