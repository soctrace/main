import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDown, CheckCircle2, MapPin } from "lucide-react";
import snapshotJson from "@/features/campaigns/data/generated/mijas-2027-municipality.json";

type Coordinate = [number, number];
type MultiPolygon = { type: "MultiPolygon"; coordinates: Coordinate[][][] };
type Section = {
  id: string; label: string; macroArea: string | null; population: number; populationYear: number;
  densityPerKm2: number; areaKm2: number; averageAge: number; ageYear: number;
  growthAbsolute: number; growthPercent: number; growthPeriod: string;
  growthClass: "growth" | "stable" | "decline"; geometry: MultiPolygon; evidenceStatus: "verified";
};
type Snapshot = {
  municipality: string; snapshotVersion: string; status: "verified";
  headline: { population2021: number; population2025: number; growthAbsolute2021To2025: number; growthPercent2021To2025: number; sectionCount: number; topFivePopulation2024: number; topFiveSharePercent2024: number; growingSections2023To2024: number; stableSections2023To2024: number; decliningSections2023To2024: number; minimumAverageAge2024: number; maximumAverageAge2024: number };
  municipalEvolution: { year: number; value: number; unit: string; source: string; evidenceStatus: "verified" }[];
  sections: Section[];
};

const snapshot = snapshotJson as unknown as Snapshot;
const number = new Intl.NumberFormat("es-ES");
const decimal = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function allCoordinates(sections: Section[]) {
  return sections.flatMap((section) => section.geometry.coordinates.flatMap((polygon) => polygon.flatMap((ring) => ring)));
}

function buildProjection(sections: Section[]) {
  const coordinates = allCoordinates(sections);
  const xs = coordinates.map(([x]) => x); const ys = coordinates.map(([, y]) => y);
  const minX = Math.min(...xs); const maxX = Math.max(...xs); const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const padding = 28; const width = 960; const height = 680;
  const scale = Math.min((width - padding * 2) / (maxX - minX), (height - padding * 2) / (maxY - minY));
  const offsetX = (width - (maxX - minX) * scale) / 2; const offsetY = (height - (maxY - minY) * scale) / 2;
  const point = ([x, y]: Coordinate) => [offsetX + (x - minX) * scale, height - offsetY - (y - minY) * scale] as Coordinate;
  const path = (geometry: MultiPolygon) => geometry.coordinates.map((polygon) => polygon.map((ring) => ring.map((coordinate, index) => `${index ? "L" : "M"}${point(coordinate).map((value) => value.toFixed(2)).join(" ")}`).join(" ") + " Z").join(" ")).join(" ");
  const center = (geometry: MultiPolygon) => { const values = geometry.coordinates.flatMap((polygon) => polygon[0]); return point([values.reduce((sum, value) => sum + value[0], 0) / values.length, values.reduce((sum, value) => sum + value[1], 0) / values.length]); };
  return { path, center };
}

function color(section: Section, mode: "population" | "growth", populationRange: [number, number]) {
  if (mode === "growth") {
    if (section.growthAbsolute < 0) return `rgba(100, 145, 186, ${Math.min(.92, .4 + Math.abs(section.growthPercent) / 14)})`;
    if (section.growthAbsolute === 0) return "rgba(120,130,142,.48)";
    return `rgba(244, 124, 42, ${Math.min(.95, .38 + section.growthPercent / 12)})`;
  }
  const [min, max] = populationRange; const ratio = (Math.sqrt(section.population) - Math.sqrt(min)) / (Math.sqrt(max) - Math.sqrt(min));
  return `rgba(${Math.round(36 + ratio * 208)}, ${Math.round(68 + ratio * 56)}, ${Math.round(92 - ratio * 50)}, ${(.46 + ratio * .48).toFixed(2)})`;
}

function EvidenceTag({ children }: { children: string }) {
  return <span className="municipality-evidence-tag"><CheckCircle2 className="h-3.5 w-3.5" /> {children}</span>;
}

function EvidenceMap({ mode }: { mode: "population" | "growth" }) {
  const [selectedId, setSelectedId] = useState(snapshot.sections[0].id);
  const projection = useMemo(() => buildProjection(snapshot.sections), []);
  const selected = snapshot.sections.find(({ id }) => id === selectedId) ?? snapshot.sections[0];
  const populations = snapshot.sections.map(({ population }) => population);
  const range: [number, number] = [Math.min(...populations), Math.max(...populations)];
  const labelled = [...snapshot.sections].sort((a, b) => b.population - a.population).slice(0, 3);
  return <div className={`municipality-real-map municipality-real-map--${mode}`}>
    <div className="municipality-map-toolbar"><div><span>{mode === "population" ? "Población por sección" : "Variación de población"}</span><strong>{mode === "population" ? "2024 · personas" : "2023–2024 · %"}</strong></div><EvidenceTag>Datos verificados</EvidenceTag></div>
    <svg className="municipality-map-svg" viewBox="0 0 960 680" role="group" aria-label={mode === "population" ? "Mapa de población por sección censal de Mijas en 2024" : "Mapa de variación de población por sección censal de Mijas entre 2023 y 2024"}>
      {snapshot.sections.map((section) => <path key={section.id} d={projection.path(section.geometry)} fill={color(section, mode, range)} className={selected.id === section.id ? "selected" : ""} fillRule="evenodd" role="button" tabIndex={0} aria-label={`${section.label}: ${mode === "population" ? `${number.format(section.population)} personas` : `${section.growthPercent > 0 ? "+" : ""}${decimal.format(section.growthPercent)} %`}`} onClick={() => setSelectedId(section.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedId(section.id); } }}><title>{section.label}</title></path>)}
      {labelled.map((section) => { const [x, y] = projection.center(section.geometry); return <text key={section.id} x={x} y={y} textAnchor="middle">{section.label.replace(/^Sección \d+ · /, "")}</text>; })}
    </svg>
    <div className="municipality-map-legend">{mode === "population" ? <><span><i className="low" />Menor concentración</span><span><i className="high" />Mayor concentración</span></> : <><span><i className="decline" />Descenso</span><span><i className="stable" />Estable</span><span><i className="growth" />Crecimiento</span></>}</div>
    <aside className="municipality-selection" aria-live="polite"><p><MapPin className="h-4 w-4" /> {selected.label}</p><strong>{mode === "population" ? number.format(selected.population) : `${selected.growthPercent > 0 ? "+" : ""}${decimal.format(selected.growthPercent)} %`}</strong><span>{mode === "population" ? `${number.format(Math.round(selected.densityPerKm2))} personas/km² · 2024` : `${selected.growthAbsolute > 0 ? "+" : ""}${number.format(selected.growthAbsolute)} personas · 2023–2024`}</span><a href="#municipality-sources">Ver evidencia</a></aside>
  </div>;
}

export function MunicipalityStory() {
  const [mapMode, setMapMode] = useState<"population" | "growth">("population");
  const populationStep = useRef<HTMLElement>(null); const growthStep = useRef<HTMLElement>(null);
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) setMapMode(entry.target === growthStep.current ? "growth" : "population"); }), { rootMargin: "-35% 0px -45%", threshold: .1 });
    if (populationStep.current) observer.observe(populationStep.current); if (growthStep.current) observer.observe(growthStep.current);
    return () => observer.disconnect();
  }, []);
  const maxPopulation = Math.max(...snapshot.municipalEvolution.map(({ value }) => value));
  return <section id="municipality" className="municipality-story" aria-labelledby="municipality-title">
    <div className="municipality-premise"><div><EvidenceTag>Hecho verificado · 2021–2025</EvidenceTag><p>02 · El municipio</p><h2 id="municipality-title">Mijas crece,<br />pero no crece igual<br />en todo su territorio.</h2><span>El crecimiento municipal está verificado. Las diferencias territoriales se muestran en el último periodo con secciones comparables.</span></div></div>
    <div className="municipality-evolution"><div className="municipality-evolution-copy"><p>Evolución municipal</p><strong>+{number.format(snapshot.headline.growthAbsolute2021To2025)}</strong><h3>personas entre 2021 y 2025</h3><span>De {number.format(snapshot.headline.population2021)} a {number.format(snapshot.headline.population2025)} habitantes: <b>+{decimal.format(snapshot.headline.growthPercent2021To2025)} %</b>.</span><a href="#municipality-sources">Fuente y definición</a></div><div className="municipality-evolution-line" aria-label="Evolución de población municipal 2021 a 2025">{snapshot.municipalEvolution.map((item, index) => <div key={item.year} style={{ height: `${Math.round(item.value / maxPopulation * 100)}%` }}><i /><span>{number.format(item.value)}</span><small>{item.year}</small>{index < snapshot.municipalEvolution.length - 1 ? <b /> : null}</div>)}</div></div>
    <div className="municipality-map-story"><div className="municipality-map-sticky"><EvidenceMap mode={mapMode} /></div><div className="municipality-map-steps"><article ref={populationStep}><p>La población no ocupa el territorio de forma uniforme.</p><h3>La concentración tiene una geografía concreta.</h3><span>Las cinco secciones con más población reúnen {number.format(snapshot.headline.topFivePopulation2024)} personas, el {decimal.format(snapshot.headline.topFiveSharePercent2024)} % del municipio en 2024.</span><EvidenceTag>Observación basada en 37 secciones</EvidenceTag></article><article ref={growthStep}><p>El mismo territorio, otra lectura.</p><h3>El crecimiento reciente también es desigual.</h3><span>Entre 2023 y 2024, {snapshot.headline.growingSections2023To2024} secciones crecieron y {snapshot.headline.decliningSections2023To2024} redujeron población. No se infieren causas.</span><EvidenceTag>Periodo comparable · 2023–2024</EvidenceTag></article></div></div>
    <div className="municipality-realities"><header><p>Cuatro observaciones territoriales</p><h3>Un municipio.<br />Realidades distintas.</h3><span>Observaciones descriptivas, todavía no segmentos de campaña.</span></header><div className="municipality-observation-list">
      <article><span>01</span><h4>La población se concentra</h4><strong>{decimal.format(snapshot.headline.topFiveSharePercent2024)} %</strong><p>de la población reside en las cinco secciones más pobladas.</p><small>Alcance: Mijas · 2024</small><a href="#municipality-sources">marts.v_population_layer</a></article>
      <article><span>02</span><h4>La densidad cambia radicalmente</h4><strong>33–63.533</strong><p>personas por km² entre los extremos seccionales.</p><small>Alcance: sección censal · 2024</small><a href="#municipality-sources">marts.v_population_layer</a></article>
      <article><span>03</span><h4>El crecimiento no es uniforme</h4><strong>{snapshot.headline.growingSections2023To2024} / {snapshot.headline.decliningSections2023To2024}</strong><p>secciones con crecimiento / descenso.</p><small>Periodo: 2023–2024</small><a href="#municipality-sources">marts.v_poblacion_seccion_anio</a></article>
      <article><span>04</span><h4>La estructura de edad contrasta</h4><strong>{decimal.format(snapshot.headline.minimumAverageAge2024)}–{decimal.format(snapshot.headline.maximumAverageAge2024)}</strong><p>años de edad media entre los extremos seccionales.</p><small>Alcance: sección censal · 2024</small><a href="#municipality-sources">marts.agent_section_profile</a></article>
    </div></div>
    <div id="municipality-sources" className="municipality-sources"><EvidenceTag>Fuentes verificadas</EvidenceTag><p>Población: marts.v_poblacion_seccion_anio · Geometría, densidad y población seccional: marts.v_population_layer · Edad: marts.agent_section_profile · Validación de límites: core.seccion_historica.</p><span>Los totales 2021–2025 concilian exactamente con core.poblacion_edad. El crecimiento seccional 2021–2025 se omite porque el número de secciones pasó de 32 a 39; se usa 2023–2024, con 37 secciones y áreas efectivamente estables.</span><small>Snapshot {snapshot.snapshotVersion} · estado de evidencia: verificado</small></div>
    <div className="municipality-implication"><div><p>Interpretación estratégica</p><h3>Un único mensaje municipal<br />no será suficiente.</h3><span>Esta es una interpretación derivada de contrastes territoriales verificados. No es todavía una recomendación electoral.</span><a href="#territorial-evolution">Continuar a la evolución territorial <ArrowDown className="h-4 w-4" /></a></div></div>
  </section>;
}
