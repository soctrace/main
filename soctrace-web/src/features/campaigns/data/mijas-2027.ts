import type { CampaignChapter, CampaignReport } from "@/features/campaigns/types";

// SECURITY: Never place confidential campaign evidence, internal strategic notes,
// unpublished recommendations, or client data in publicly downloadable frontend files.
// Protected content must arrive through an RLS-protected query or authorized backend.

const chapter = (
  id: string,
  number: string,
  navLabel: string,
  title: string,
  introduction: string,
  blocks: CampaignChapter["blocks"],
  extra: Pick<CampaignChapter, "map" | "visual"> = {},
): CampaignChapter => ({
  id, number, navLabel, title, introduction, blocks,
  group: id === "methodology-annex" ? "methodology"
    : ["cover", "executive-summary", "municipality", "population", "territorial-evolution"].includes(id) ? "context"
      : ["electoral-landscape", "territorial-typologies", "territorial-relationships", "opportunity-map"].includes(id) ? "diagnosis"
        : ["strategic-clusters", "priority-territories", "target-profiles"].includes(id) ? "priorities"
          : ["narrative-messaging", "resource-allocation"].includes(id) ? "strategy"
            : "execution",
  ...extra,
});

export const mijas2027Campaign: CampaignReport = {
  id: "mijas-2027",
  slug: "mijas-2027",
  municipality: "Mijas",
  title: "Mijas 2027",
  productName: "Campaign Intelligence",
  subtitle: "Estrategia territorial basada en datos",
  preparedBy: "Preparado por soctrace",
  status: "published",
  statusLabel: "Análisis territorial verificado",
  publicationStatus: "Campaign Intelligence",
  branding: { accent: "#f47c2a", secondary: "#4a6fa5" },
  access: { policy: "supabase-membership", campaignId: "mijas-2027" },
  evidence: [
    { id: "structure", status: "example", confidence: "high", clientExplanation: "Ejemplo de servicio personalizado; no representa una recomendación para Mijas." },
  ],
  sources: [{ id: "official-sources", label: "Geometrías oficiales, padrón, resultados electorales, renta y entorno construido", status: "example" }],
  chapters: [
    chapter("cover", "00", "Mijas 2027", "Mijas 2027", "Entender el territorio antes de decidir la campaña.", []),
    chapter("executive-summary", "01", "La lectura", "Mijas exige más de una mirada", "La estructura municipal, su evolución y su comportamiento electoral forman una sola historia territorial.", []),
    chapter("municipality", "02", "Municipio", "El municipio como sistema", "Una lectura de núcleos, conexiones y contrastes sobre geometrías oficiales.", []),
    chapter("territorial-evolution", "03", "Evolución", "Cómo está cambiando", "La comparación armonizada distingue transformaciones sostenidas de movimientos puntuales.", []),
    chapter("population", "04", "Radiografía", "Radiografía municipal", "Un municipio, múltiples realidades territoriales.", [{ title: "Evidencia territorial verificada", body: "Crecimiento, densidad, demografía, renta, forma construida y accesibilidad, con sus geografías y periodos explícitos." }]),
    chapter("electoral-landscape", "05", "Diagnóstico", "Diagnóstico electoral", "Mijas no vota igual en todas las elecciones ni en todos sus territorios.", [{ title: "Evidencia electoral verificada", body: "Doce elecciones, resultados municipales, competencia territorial, participación y comparaciones geográficas válidas." }]),
    chapter("target-profiles", "06", "Perfiles", "Perfiles territoriales", "Cada sección combina una realidad demográfica, urbana y electoral diferente.", []),
    chapter("territorial-typologies", "07", "Tipologías", "Tipologías territoriales", "Cinco familias analíticas describen similitudes multidimensionales entre las 37 secciones.", []),
    chapter("territorial-relationships", "08", "Relaciones", "Relaciones territoriales", "Qué explicaciones aparentes resisten el contraste y cuáles necesitan más evidencia.", []),
    chapter("your-campaign", "09", "Tu campaña", "Campaign Intelligence · Tu candidatura", "El conocimiento de Mijas se convierte en estrategia cuando incorporamos tu punto de partida y tu objetivo.", []),
    chapter("methodology-annex", "10", "Metodología", "Cómo sostenemos cada afirmación", "Fuentes, armonización y límites expuestos con claridad.", []),
  ],
};
