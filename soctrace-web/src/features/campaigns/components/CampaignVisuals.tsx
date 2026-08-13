import type { CampaignMapKind } from "@/features/campaigns/types";
import { PlaceholderBadge } from "@/features/campaigns/components/PlaceholderBadge";

const palettes: Record<CampaignMapKind, string[]> = {
  municipality: ["#4a6fa5", "#315273", "#1d344d", "#182538", "#f47c2a"],
  population: ["#183142", "#24506a", "#33738d", "#52a2b5", "#8cd5da"],
  evolution: ["#322739", "#573a50", "#89505c", "#c36b54", "#f09a5a"],
  electoral: ["#243249", "#4b3e67", "#745079", "#416678", "#765b43"],
  opportunity: ["#1c3540", "#31594f", "#6b653d", "#9b6135", "#d67538"],
  clusters: ["#334e68", "#5c4772", "#38675a", "#755942", "#794f58"],
  priority: ["#253446", "#5e473b", "#8e5039", "#c26335", "#f47c2a"],
};

const labels: Record<CampaignMapKind, string[]> = {
  municipality: ["Contexto", "Conexión", "Ámbito"], population: ["Patrón A", "Patrón B", "Por validar"],
  evolution: ["Estable", "Cambio demo", "Por validar"], electoral: ["Categoría A", "Categoría B", "Categoría C"],
  opportunity: ["Explorar", "Observar", "Validar"], clusters: ["Grupo A", "Grupo B", "Grupo C"],
  priority: ["Secuencia 1", "Secuencia 2", "Sin priorizar"],
};

export function FullScreenMap({ kind }: { kind: CampaignMapKind }) {
  const colors = palettes[kind];
  return (
    <figure className="campaign-map" aria-label={`Mapa demostrativo: ${kind}`}>
      <svg viewBox="0 0 900 600" role="img" aria-labelledby={`map-${kind}`}>
        <title id={`map-${kind}`}>Geometrías neutrales para demostrar la futura visualización</title>
        <defs><filter id="glow"><feGaussianBlur stdDeviation="12" /></filter></defs>
        <path d="M90 182 220 72l153 45 92-58 176 51 164 125-54 166-123 111-174-18-109 55-166-70-93-132Z" fill="#0b121d" stroke="#526172" strokeWidth="2" />
        <path d="M92 183 220 74l65 147-101 111-98 15Z" fill={colors[0]} opacity=".82" />
        <path d="m220 74 153 45 37 141-125-39Z" fill={colors[1]} opacity=".9" />
        <path d="m373 119 92-58 121 35-57 189-119-25Z" fill={colors[2]} opacity=".88" />
        <path d="m586 96 55 14 164 125-54 166-149-76-73-40Z" fill={colors[3]} opacity=".9" />
        <path d="m184 332 101-111 125 39 119 25 73 40-63 169-85-10-109 55-166-70Z" fill={colors[4]} opacity=".86" />
        <path d="M140 410 Q350 270 730 220" fill="none" stroke="#f5f7fb" strokeOpacity=".22" strokeWidth="5" strokeDasharray="5 10" />
        <circle cx="472" cy="310" r="44" fill={colors[4]} opacity=".17" filter="url(#glow)" />
        <circle cx="472" cy="310" r="6" fill="#fff" />
      </svg>
      <div className="campaign-map-overlay"><PlaceholderBadge /><p>Geometrías neutrales · sin valores reales</p></div>
      <figcaption>{labels[kind].map((label, index) => <span key={label}><i style={{ backgroundColor: colors[index * 2] }} />{label}</span>)}</figcaption>
    </figure>
  );
}

export function FullWidthVisual({ type }: { type: NonNullable<import("@/features/campaigns/types").CampaignChapter["visual"]> }) {
  if (type === "timeline") return <div className="campaign-timeline">{["Escucha", "Contraste", "Activación", "Cierre"].map((label, i) => <div key={label}><span>0{i + 1}</span><strong>{label}</strong><small>Fase pendiente de definir</small></div>)}</div>;
  if (type === "budget") return <div className="campaign-allocation">{[36, 26, 20, 18].map((width, i) => <div key={width} style={{ width: `${width}%` }}><span>Bloque {String.fromCharCode(65 + i)}</span></div>)}</div>;
  const items: Record<Exclude<typeof type, "timeline" | "budget">, string[]> = {
    profiles: ["Contexto de vida", "Barrera de confianza", "Canal y momento"], messages: ["Promesa común", "Prueba visible", "Adaptación territorial"],
    kpis: ["Actividad", "Respuesta", "Cambio", "Resultado"], scenarios: ["Continuidad", "Aceleración", "Contingencia"],
    methodology: ["Fuente", "Transformación", "Límite", "Confianza"],
  };
  return <div className={`campaign-visual-grid campaign-visual-${type}`}>{items[type].map((item, index) => <article key={item}><span>0{index + 1}</span><h3>{item}</h3><p>Pendiente de datos y validación.</p></article>)}</div>;
}
