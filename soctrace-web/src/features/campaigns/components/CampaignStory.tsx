import { ArrowDown, ArrowRight, Lightbulb, ShieldCheck } from "lucide-react";
import { Component, lazy, type ReactNode, Suspense } from "react";
import type { CampaignChapter, CampaignEvidence, CampaignReport } from "@/features/campaigns/types";
import { PlaceholderBadge } from "@/features/campaigns/components/PlaceholderBadge";

const LazyMap = lazy(async () => ({ default: (await import("@/features/campaigns/components/CampaignVisuals")).FullScreenMap }));
const LazyVisual = lazy(async () => ({ default: (await import("@/features/campaigns/components/CampaignVisuals")).FullWidthVisual }));

function AuditableMap({ kind }: { kind: NonNullable<CampaignChapter["map"]> }) {
  if (import.meta.env.DEV && new URLSearchParams(window.location.search).get("auditMapFailure") === "1") {
    throw new Error("Intentional visual-audit map failure");
  }
  return <LazyMap kind={kind} />;
}

class VisualBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? <div className="campaign-visual-error" role="status"><p>La visualización no está disponible.</p><span>El relato y las conclusiones del capítulo siguen accesibles.</span></div> : this.props.children; }
}

export function CampaignCover({ campaign }: { campaign: CampaignReport }) {
  return <section id="cover" className="campaign-cover" aria-labelledby="campaign-title">
    <div className="campaign-cover-orbit" aria-hidden="true" />
    <div className="campaign-cover-top"><a href="/" className="brand-mark">soctrace</a><span className="campaign-cover-edition">Campaign Intelligence · 00</span></div>
    <div className="campaign-cover-content"><div className="campaign-cover-status"><span>{campaign.municipality} · Municipales 2027</span></div><p className="campaign-kicker">{campaign.productName}</p><h1 id="campaign-title">{campaign.title}</h1><p>Entender el territorio<br />antes de decidir la campaña.</p><div className="campaign-cover-meta"><span>37 territorios · 12 procesos electorales · 2021–2026</span><span>Análisis territorial multivariable</span></div><a href="#executive-summary" className="campaign-primary-action">Entrar en el territorio <ArrowDown className="h-4 w-4" /></a></div>
    <div className="campaign-cover-threshold"><span>Una lectura estratégica, territorio a territorio</span><i /><small>Desliza para comenzar</small></div>
  </section>;
}

export function ExecutiveNarrative({ chapter, campaign }: { chapter: CampaignChapter; campaign: CampaignReport }) {
  const concepts = [
    { number: "01", title: "Un municipio que cambia", body: "El crecimiento transforma el peso y la estructura de cada territorio a ritmos distintos." },
    { number: "02", title: "Un municipio con múltiples realidades", body: "Demografía, renta y forma urbana dibujan contrastes que el promedio municipal oculta." },
    { number: "03", title: "Un municipio electoralmente complejo", body: "La participación y la competencia cambian entre territorios y tipos de elección." },
  ];
  return <section id={chapter.id} className="executive-story" aria-labelledby="executive-story-title">
    <div className="executive-silence">
      <div><p>La primera decisión estratégica<br />es saber qué municipio estamos mirando.</p><h2 id="executive-story-title">Mijas es más compleja<br />de lo que parece.</h2><span>Evidencia territorial, demográfica y electoral para decidir con contexto.</span></div>
    </div>
    <div className="executive-territory">
      <div className="executive-territory-sticky">
        <header><p>01 · Antes de los datos</p><h3>Primero,<br />el territorio.</h3><span>Sin clasificaciones. Sin resultados. Sin atajos.</span></header>
        <div className="executive-living-map"><VisualBoundary><Suspense fallback={<div className="campaign-visual-fallback">Preparando territorio…</div>}><AuditableMap kind="municipality" /></Suspense></VisualBoundary></div>
        <div className="executive-map-caption"><span>37 territorios oficiales · lectura municipal verificada</span></div>
      </div>
    </div>
    <div className="executive-concepts">
      <header><p>02 · La lectura</p><h3>Tres capas para comprender<br />{campaign.municipality}.</h3><span>Cada capítulo añade evidencia antes de avanzar hacia la decisión estratégica.</span></header>
      <div className="executive-concept-grid">{concepts.map((concept) => <article key={concept.number}><span>{concept.number}</span><div><h4>{concept.title}</h4><p>{concept.body}</p></div></article>)}</div>
    </div>
    <div className="executive-conclusion">
      <div><p>La implicación estratégica</p><h3>Las decisiones de campaña<br />necesitan contexto territorial.</h3><span>Primero analizamos Mijas. Después incorporamos la candidatura.</span><a href="#municipality" className="executive-next">Comprender el municipio <ArrowDown className="h-4 w-4" /></a></div>
    </div>
  </section>;
}

function evidenceLabel(evidence?: CampaignEvidence) {
  if (!evidence || evidence.status === "pending-data") return "Pendiente de datos";
  if (evidence.status === "pending-validation") return "Pendiente de validación";
  return "Ejemplo de estructura";
}

export function ChapterIntro({ chapter }: { chapter: CampaignChapter }) {
  return <header className="campaign-chapter-intro"><p>{chapter.number} / Campaign Intelligence</p><h2>{chapter.title}</h2><div className="campaign-intro-rule" /><p>{chapter.introduction}</p></header>;
}

export function ChapterSection({ chapter, evidence }: { chapter: CampaignChapter; evidence: CampaignEvidence[] }) {
  const variant = chapter.map ? "map" : chapter.visual ? `visual-${chapter.visual}` : "editorial";
  return <section id={chapter.id} className={`campaign-chapter campaign-chapter--${variant}`} aria-labelledby={`${chapter.id}-title`}>
    <div className="campaign-chapter-inner"><header className="campaign-chapter-intro"><p>{chapter.number} / Campaign Intelligence</p><h2 id={`${chapter.id}-title`}>{chapter.title}</h2><div className="campaign-intro-rule" /><p>{chapter.introduction}</p></header>
      {chapter.map ? <VisualBoundary><Suspense fallback={<div className="campaign-visual-fallback">Preparando visualización…</div>}><AuditableMap kind={chapter.map} /></Suspense></VisualBoundary> : null}
      <div className="campaign-narrative-grid">{chapter.blocks.map((block, index) => { const itemEvidence = evidence.find((item) => item.id === block.evidenceId); return <article key={`${block.title}-${index}`} className="campaign-narrative-card">{block.eyebrow ? <p className="campaign-card-eyebrow">{block.eyebrow}</p> : null}<h3>{block.title}</h3><p>{block.body}</p>{block.finding ? <div className="campaign-finding"><Lightbulb className="h-4 w-4" />{block.finding}</div> : null}{block.recommendation ? <div className="campaign-recommendation"><ArrowRight className="h-4 w-4" />{block.recommendation}</div> : null}<PlaceholderBadge>{evidenceLabel(itemEvidence)}</PlaceholderBadge>{itemEvidence ? <small>{itemEvidence.clientExplanation}</small> : null}</article>; })}</div>
      {chapter.visual ? <VisualBoundary><Suspense fallback={<div className="campaign-visual-fallback">Preparando visualización…</div>}><LazyVisual type={chapter.visual} /></Suspense></VisualBoundary> : null}
    </div>
  </section>;
}

export function CampaignFooter({ campaign }: { campaign: CampaignReport }) {
  return <footer className="campaign-footer"><div><a href="#cover" className="brand-mark">soctrace</a><p>{campaign.title} · {campaign.publicationStatus}</p></div><div><span><ShieldCheck className="h-4 w-4" /> Evidencia con límites explícitos</span><a href="#methodology-annex">Metodología</a></div></footer>;
}
