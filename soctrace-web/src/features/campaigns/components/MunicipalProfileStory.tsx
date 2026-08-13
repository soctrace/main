import { ArrowDown, CheckCircle2, Info, MapPin, ShieldAlert } from "lucide-react";
import { useMemo } from "react";
import blockAJson from "@/features/campaigns/data/generated/mijas-2027-block-a-municipal-profile.json";
import municipalityJson from "@/features/campaigns/data/generated/mijas-2027-municipality.json";
import evolutionJson from "@/features/campaigns/data/generated/mijas-2027-territorial-evolution.json";

type Point = [number, number];
type Geometry = { type: "MultiPolygon"; coordinates: Point[][][] };
type SummaryMetric = { metric: string; value: number; unit: string; period: string; source: string; calculation_method: string; evidence_status: string };
type Ranking = { metric: string; ranking_side: "top" | "bottom"; rank: number; seccion_id: string; territory: string; value: number; unit: string; period: string; geography: string; source: string; comparability_warning: string | null };
type Correlation = { relationship: string; sample_size: number; pearson_r: number; spearman_rho: number; period: string; geography: string; warning: string };
type ProfileSection = { seccion_id: string; display_name: string; density_per_km2: number; average_age: number; under_30_pct: number; over_65_pct: number; income_individual: number; income_household: number; building_intensity: number; average_plot_size_m2: number };
type Accessibility = { seccion_id: string; section_name: string; geography_year: number; accessibility_score: number; service_count: number; accessibility_label: string };
type GrowthFamily = { family_id: string; territory: string; growth_absolute: number; growth_percent: number; contribution_to_municipal_growth_pct: number; trend_classification: "sustained_growth" | "variable" };
type BlockA = { snapshotVersion: string; status: string; municipalSummary: SummaryMetric[]; sections2024: ProfileSection[]; populationGrowthFamilies2021To2025: GrowthFamily[]; accessibility2026: Accessibility[]; rankings: Ranking[]; descriptiveCorrelations: Correlation[] };
type MunicipalitySnapshot = { sections: { id: string; geometry: Geometry }[] };
type EvolutionSnapshot = { summary: { topFiveContributionPercent: number }; units: { id: string; label: string; cumulativeChange: number; geometry: Geometry }[] };

const data = blockAJson as unknown as BlockA;
const municipality = municipalityJson as unknown as MunicipalitySnapshot;
const evolution = evolutionJson as unknown as EvolutionSnapshot;
const integer = new Intl.NumberFormat("es-ES");
const decimal = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const money = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

function project(geometries: Geometry[]) {
  const points = geometries.flatMap((geometry) => geometry.coordinates.flatMap((polygon) => polygon.flatMap((ring) => ring)));
  const xs = points.map(([x]) => x); const ys = points.map(([, y]) => y);
  const minX = Math.min(...xs); const maxX = Math.max(...xs); const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const width = 960; const height = 650; const padding = 28;
  const scale = Math.min((width - 2 * padding) / (maxX - minX), (height - 2 * padding) / (maxY - minY));
  const offsetX = (width - (maxX - minX) * scale) / 2; const offsetY = (height - (maxY - minY) * scale) / 2;
  const point = ([x, y]: Point) => [offsetX + (x - minX) * scale, height - offsetY - (y - minY) * scale];
  return (geometry: Geometry) => geometry.coordinates.map((polygon) => polygon.map((ring) => ring.map((coordinate, index) => `${index ? "L" : "M"}${point(coordinate).map((value) => value.toFixed(1)).join(" ")}`).join(" ") + " Z").join(" ")).join(" ");
}

function metric(id: string) {
  const item = data.municipalSummary.find(({ metric: key }) => key === id);
  if (!item) throw new Error(`Missing Block A summary metric: ${id}`);
  return item;
}

function endpoint(id: string, side: "top" | "bottom") {
  const item = data.rankings.find(({ metric: key, ranking_side, rank }) => key === id && ranking_side === side && rank === 1);
  if (!item) throw new Error(`Missing Block A ranking: ${id}/${side}`);
  return item;
}

function Evidence({ status = "Dato verificado", children }: { status?: string; children: React.ReactNode }) {
  return <span className={`profile-evidence profile-evidence--${status.toLowerCase().includes("provisional") ? "provisional" : status.toLowerCase().includes("asociación") ? "association" : "verified"}`}><CheckCircle2 />{status}{children ? <small>{children}</small> : null}</span>;
}

function SourceNote({ value, unit, period, geography, source, status }: { value: string; unit: string; period: string; geography: string; source: string; status: string }) {
  return <details className="profile-source"><summary><Info /> Evidencia y fuente</summary><dl><div><dt>Valor</dt><dd>{value} {unit}</dd></div><div><dt>Periodo</dt><dd>{period}</dd></div><div><dt>Geografía</dt><dd>{geography}</dd></div><div><dt>Fuente</dt><dd>{source}</dd></div><div><dt>Estado</dt><dd>{status}</dd></div></dl></details>;
}

function GrowthMap() {
  const path = useMemo(() => project(evolution.units.map(({ geometry }) => geometry)), []);
  const leaders = new Set(evolution.units.slice(0, 5).map(({ id }) => id));
  const maximum = Math.max(...evolution.units.map(({ cumulativeChange }) => cumulativeChange));
  return <div className="profile-growth-map"><svg viewBox="0 0 960 650" aria-label="Mapa de crecimiento de 32 familias territoriales armonizadas entre 2021 y 2025">{evolution.units.map((unit) => <path key={unit.id} d={path(unit.geometry)} fill={leaders.has(unit.id) ? `rgba(244,124,42,${.55 + .4 * unit.cumulativeChange / maximum})` : "rgba(66,84,98,.5)"} className={leaders.has(unit.id) ? "leader" : ""} fillRule="evenodd"><title>{unit.label}: {unit.cumulativeChange > 0 ? "+" : ""}{integer.format(unit.cumulativeChange)} personas</title></path>)}</svg><div className="profile-map-key"><span><i />Cinco mayores aportaciones</span><span><i />Resto de territorios</span></div></div>;
}

function DensityMap() {
  const joined = municipality.sections.map((section) => ({ ...section, profile: data.sections2024.find(({ seccion_id }) => seccion_id === section.id) })).filter((section) => section.profile);
  const path = useMemo(() => project(joined.map(({ geometry }) => geometry)), [joined]);
  const maximum = Math.max(...joined.map(({ profile }) => profile!.density_per_km2));
  return <svg className="profile-density-map" viewBox="0 0 960 650" aria-label="Densidad de población por sección oficial de 2024">{joined.map((section) => { const ratio = Math.log1p(section.profile!.density_per_km2) / Math.log1p(maximum); return <path key={section.id} d={path(section.geometry)} fill={`rgba(244,124,42,${.16 + ratio * .8})`} fillRule="evenodd"><title>{section.profile!.display_name}: {decimal.format(section.profile!.density_per_km2)} personas/km²</title></path>; })}</svg>;
}

function Contrast({ label, high, low, format = integer.format }: { label: string; high: Ranking; low: Ranking; format?: (value: number) => string }) {
  return <div className="profile-contrast"><p>{label}</p><article><span>Mayor valor</span><h4>{high.territory.replace(/^Sección \d+ · /, "")}</h4><strong>{format(high.value)}</strong><small>{high.unit}</small></article><i aria-hidden="true" /><article><span>Menor valor</span><h4>{low.territory.replace(/^Sección \d+ · /, "")}</h4><strong>{format(low.value)}</strong><small>{low.unit}</small></article></div>;
}

export function MunicipalProfileStory() {
  const population2021 = metric("population_2021"); const population2025 = metric("population_2025");
  const growth = metric("growth_2021_2025"); const growthPercent = metric("growth_percent_2021_2025");
  const densityHigh = endpoint("density", "top"); const densityLow = endpoint("density", "bottom");
  const ageYoung = endpoint("youngest_average_age", "top"); const ageOld = endpoint("oldest_average_age", "top");
  const under30High = endpoint("under_30_share", "top"); const under30Low = endpoint("under_30_share", "bottom");
  const over65High = endpoint("over_65_share", "top"); const over65Low = endpoint("over_65_share", "bottom");
  const incomeHigh = endpoint("individual_income", "top"); const incomeLow = endpoint("individual_income", "bottom");
  const householdHigh = endpoint("household_income", "top"); const householdLow = endpoint("household_income", "bottom");
  const intensityHigh = endpoint("building_intensity", "top"); const intensityLow = endpoint("building_intensity", "bottom");
  const plotHigh = endpoint("average_plot_size", "top"); const plotLow = endpoint("average_plot_size", "bottom");
  const accessHigh = endpoint("accessibility", "top"); const accessLow = endpoint("accessibility", "bottom");
  const servicesHigh = endpoint("service_availability", "top"); const servicesLow = endpoint("service_availability", "bottom");
  const association = data.descriptiveCorrelations.find(({ relationship }) => relationship === "density ↔ built form")!;
  const topGrowth = data.populationGrowthFamilies2021To2025.slice().sort((a, b) => b.growth_absolute - a.growth_absolute).slice(0, 5);
  const timeline = [population2021, metric("population_2022"), metric("population_2023"), metric("population_2024"), population2025];
  const minPopulation = Math.min(...timeline.map(({ value }) => value)); const maxPopulation = Math.max(...timeline.map(({ value }) => value));
  return <section id="population" className="municipal-profile" aria-labelledby="municipal-profile-title">
    <header className="profile-opening"><div><Evidence>Snapshot {data.snapshotVersion}</Evidence><p>04 · Contexto territorial</p><h2 id="municipal-profile-title">Radiografía<br />municipal</h2><span>Un municipio, múltiples realidades territoriales.</span></div></header>

    <section className="profile-scene profile-growth" aria-labelledby="profile-growth-title"><div className="profile-scene-copy"><p>01 · Escala municipal</p><h3 id="profile-growth-title">Mijas crece con fuerza.</h3><strong>+{integer.format(growth.value)}</strong><span>residentes entre 2021 y 2025 · +{decimal.format(growthPercent.value)} %</span><p className="profile-body">La población municipal pasa de {integer.format(population2021.value)} a {integer.format(population2025.value)} residentes en cuatro años.</p><SourceNote value={`+${integer.format(growth.value)}`} unit="personas" period="2021–2025" geography="Municipio de Mijas" source={growth.source} status="Dato verificado" /></div><div className="profile-time-visual" aria-label="Evolución de población de Mijas entre 2021 y 2025">{timeline.map((item) => <div key={item.period}><span>{integer.format(item.value)}</span><i style={{ height: `${35 + 65 * (item.value - minPopulation) / (maxPopulation - minPopulation)}%` }} /><small>{item.period}</small></div>)}</div></section>

    <section className="profile-scene profile-concentration" aria-labelledby="profile-concentration-title"><div className="profile-sticky-map"><GrowthMap /><div className="profile-map-caption"><Evidence status="Tendencia verificada">2021–2025</Evidence><span>32 familias territoriales armonizadas</span></div></div><div className="profile-ranked-copy"><p>02 · Concentración del crecimiento</p><h3 id="profile-concentration-title">El aumento no se reparte por igual.</h3><strong>{decimal.format(evolution.summary.topFiveContributionPercent)} %</strong><span>del crecimiento neto se concentra en cinco territorios.</span><div className="profile-growth-ranking">{topGrowth.map((item, index) => <article key={item.family_id}><span>0{index + 1}</span><div><h4>{item.territory.replace(/^Sección \d+ · /, "")}</h4><i style={{ width: `${100 * item.growth_absolute / topGrowth[0].growth_absolute}%` }} /></div><strong>+{integer.format(item.growth_absolute)}</strong></article>)}</div><p className="profile-body">15 territorios mantienen crecimiento en los cuatro intervalos anuales; 17 presentan una evolución variable.</p><SourceNote value={`${decimal.format(evolution.summary.topFiveContributionPercent)}`} unit="% del crecimiento neto" period="2021–2025" geography="32 familias armonizadas" source="Snapshot de Evolución Territorial" status="Tendencia verificada" /></div></section>

    <section className="profile-scene profile-density" aria-labelledby="profile-density-title"><div className="profile-density-copy"><p>03 · Densidad</p><h3 id="profile-density-title">De la máxima compacidad a la dispersión.</h3><Contrast label="Densidad residencial" high={densityHigh} low={densityLow} format={decimal.format} /><div className="profile-association"><span>Asociación descriptiva</span><strong>ρ {association.spearman_rho.toFixed(4)}</strong><p>Las secciones densas también tienden a mostrar mayor intensidad construida.</p><small>Spearman · n={association.sample_size} · no implica causalidad</small></div><SourceNote value={association.spearman_rho.toFixed(4)} unit="Spearman rho" period={association.period} geography={association.geography} source="Block A · densidad e intensidad construida" status="Asociación descriptiva" /></div><DensityMap /></section>

    <section className="profile-scene profile-age" aria-labelledby="profile-age-title"><header><p>04 · Estructura demográfica</p><h3 id="profile-age-title">La edad dibuja municipios distintos.</h3><div><span>Edad media ponderada · 2024</span><strong>{decimal.format(metric("weighted_average_age").value)}</strong><small>años</small></div></header><div className="profile-age-comparisons"><Contrast label="Edad media" high={ageOld} low={ageYoung} format={decimal.format} /><Contrast label="Población menor de 30" high={under30High} low={under30Low} format={(value) => `${decimal.format(value)} %`} /><Contrast label="Población de 65 o más" high={over65High} low={over65Low} format={(value) => `${decimal.format(value)} %`} /></div><footer><span>Referencia municipal 2025</span><p><b>{decimal.format(metric("under_30_share").value)} %</b> menores de 30 · <b>{decimal.format(metric("over_65_share").value)} %</b> mayores de 65</p><p><b>{decimal.format(metric("men_share").value)} %</b> hombres · <b>{decimal.format(metric("women_share").value)} %</b> mujeres</p><SourceNote value={decimal.format(metric("weighted_average_age").value)} unit="años" period="2024" geography="37 secciones oficiales" source={metric("weighted_average_age").source} status="Dato verificado" /></footer></section>

    <section className="profile-scene profile-income" aria-labelledby="profile-income-title"><div><p>05 · Capacidad económica relativa</p><h3 id="profile-income-title">La posición económica cambia con el territorio.</h3><p className="profile-body">Media entre secciones en 2023: {money.format(metric("mean_individual_income").value)} por persona y {money.format(metric("mean_household_income").value)} por hogar.</p><SourceNote value={money.format(metric("mean_individual_income").value)} unit="por persona y año" period="2023" geography="Media no ponderada de 37 secciones" source={metric("mean_individual_income").source} status="Dato verificado" /></div><div className="profile-income-rails"><Contrast label="Renta individual" high={incomeHigh} low={incomeLow} format={money.format} /><Contrast label="Renta del hogar" high={householdHigh} low={householdLow} format={money.format} /></div></section>

    <section className="profile-scene profile-built" aria-labelledby="profile-built-title"><header><p>06 · Forma construida</p><h3 id="profile-built-title">Un continuo entre compacidad y grandes parcelas.</h3><div className="profile-built-totals"><span><strong>{integer.format(metric("built_footprint").value)}</strong>m² de huella construida</span><span><strong>{integer.format(metric("parcel_count").value)}</strong>parcelas</span><span><strong>{integer.format(metric("building_part_count").value)}</strong>partes de edificio</span></div></header><div className="profile-built-continuum"><article><span>Mayor intensidad construida</span><h4>{intensityHigh.territory.replace(/^Sección \d+ · /, "")}</h4><strong>{intensityHigh.value.toFixed(4)}</strong><i className="compact" /></article><div><span>Forma compacta</span><b>→</b><span>Parcelas dispersas</span></div><article><span>Mayor parcela media</span><h4>{plotHigh.territory.replace(/^Sección \d+ · /, "")}</h4><strong>{decimal.format(plotHigh.value)} m²</strong><i className="dispersed" /></article></div><p className="profile-built-footnote">Extremos complementarios: menor intensidad, {intensityLow.territory.replace(/^Sección \d+ · /, "")} ({intensityLow.value.toFixed(4)}); menor parcela media, {plotLow.territory.replace(/^Sección \d+ · /, "")} ({decimal.format(plotLow.value)} m²).</p><div className="profile-omission"><ShieldAlert /><p><strong>Precio de vivienda no cartografiado.</strong> El valor de mercado y el valor catastral disponibles son referencias municipales repetidas en las 37 filas, no diferencias territoriales.</p></div><SourceNote value={integer.format(metric("built_footprint").value)} unit="m²" period="2023" geography="37 secciones oficiales" source={metric("built_footprint").source} status="Dato verificado" /></section>

    <section className="profile-scene profile-access" aria-labelledby="profile-access-title"><div className="profile-access-heading"><Evidence status="Evidencia provisional">Geografía 2026 · 41 secciones</Evidence><p>07 · Accesibilidad</p><h3 id="profile-access-title">El acceso registrado tampoco es homogéneo.</h3><strong>{decimal.format(metric("mean_accessibility_score").value)}<small>/100</small></strong><span>puntuación media de accesibilidad</span></div><div className="profile-access-field"><Contrast label="Puntuación de accesibilidad" high={accessHigh} low={accessLow} format={decimal.format} /><Contrast label="Servicios registrados" high={servicesHigh} low={servicesLow} /><div className="profile-warning"><ShieldAlert /><p><strong>Lectura provisional.</strong> “0” significa que no hay servicios registrados en la fuente disponible; no demuestra que no existan. Esta geografía no se compara directamente con el perfil descriptivo de 2024.</p></div><SourceNote value={decimal.format(metric("mean_accessibility_score").value)} unit="puntos sobre 100" period="2026" geography="41 secciones provisionales" source={metric("mean_accessibility_score").source} status="Evidencia provisional con datos ausentes" /></div></section>

    <section className="profile-closing"><div><Evidence status="Síntesis consultiva">Basada en evidencia verificada</Evidence><p>08 · Síntesis</p><h3>Mijas no es un mercado político uniforme.</h3><span>El crecimiento, la forma urbana, la estructura demográfica, la renta y la accesibilidad definen realidades territoriales marcadamente distintas.</span><a href="#electoral-landscape">Continuar al diagnóstico electoral <ArrowDown /></a></div><MapPin aria-hidden="true" /></section>
  </section>;
}
