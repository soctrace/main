import dashboardScreenshot from "@/assets/dashboard-mijas.png";
import electoralJson from "@/features/campaigns/data/generated/mijas-2027-block-b-electoral-diagnosis.json";
import { campaignSourceLine } from "@/features/campaigns/data/clientSources";
import { ElectionTimelinePrint } from "./ElectionTimeline";
import { MijasMap } from "./ExecutiveCampaign";
import { PsoeVictoryStory } from "./PsoeVictoryStory";
import { TerritorialEvolutionStory } from "./TerritorialEvolutionStory";
import { TerritorialRelationshipsStory } from "./TerritorialRelationshipsStory";
import { TerritorialTypologyStory } from "./TerritorialTypologyStory";

type Inventory={election_id:number;election_type:string;election_date:string};
type Summary={election_id:number;winner:string;runner_up:string;winner_share_pct:number;participation_pct:number;margin_pct_points:number};
type Electoral={electionInventory:Inventory[];municipalSummaries:Summary[]};
const electoral=electoralJson as unknown as Electoral;
const municipalElection=electoral.electionInventory.find(item=>item.election_type==="MUNICIPALES"&&item.election_date.startsWith("2023"));
const municipal=electoral.municipalSummaries.find(item=>item.election_id===municipalElection?.election_id);
const two=new Intl.NumberFormat("es-ES",{minimumFractionDigits:2,maximumFractionDigits:2});

const questions=[
 "¿Dónde se decidió realmente la victoria del PSOE en 2023?",
 "¿Qué territorios pueden cambiar el equilibrio político de Mijas en 2027?",
 "¿Dónde existe más espacio para una candidatura alternativa a PP y PSOE?",
];

const dashboardCapabilities=[
 ["Proyección de voto","Explora escenarios y evolución electoral por territorio."],
 ["Renta","Compara niveles de renta individual y del hogar entre secciones."],
 ["Inteligencia inmobiliaria","Identifica zonas con mayor interés inmobiliario, intensidad construida y contexto residencial."],
 ["Población y crecimiento","Analiza dónde crece Mijas y cómo cambia su estructura territorial."],
 ["Edad y estructura demográfica","Compara edad media, población joven y población mayor."],
 ["Participación y comportamiento electoral","Consulta participación, abstención, ganadores y márgenes por sección."],
];

function PrintChapter({number,label,title,children,className=""}:{number:string;label:string;title:string;children:React.ReactNode;className?:string}){
 return <section className={`print-chapter ${className}`}><header className="print-chapter-heading"><span>{number} · {label}</span><h2>{title}</h2></header>{children}</section>;
}

export function CampaignPrintReport(){
 if(!municipal) throw new Error("Missing Municipal 2023 summary");
 return <article className="campaign-print-report">
  <section className="print-cover"><div className="print-cover-brand">soctrace</div><div><p>Informe pre-electoral</p><h1>Mijas 2027</h1><h2>Entender Mijas antes de decidir la campaña.</h2><ol>{questions.map((question,index)=><li key={question}><span>0{index+1}</span><strong>{question}</strong></li>)}</ol></div><footer>Campaign Intelligence · agosto 2026</footer></section>

  <PrintChapter number="01" label="Lectura territorial" title="Mijas no es un único municipio." className="print-opening"><p className="print-lead">El crecimiento, la edad, la renta, la forma urbana, la participación y el voto dibujan realidades territoriales diferentes.</p><div className="print-kpis"><article><strong>+7.764</strong><span>residentes desde 2021</span></article><article><strong>23,6 %</strong><span>de la población en cinco secciones</span></article><article><strong>38,0–69,4 %</strong><span>rango territorial de participación</span></article></div><div className="print-map-pair"><figure><figcaption>Población por sección</figcaption><MijasMap mode="population"/><p>La población municipal crece, pero no se distribuye de manera uniforme.</p></figure><figure><figcaption>Variación reciente de población</figcaption><MijasMap mode="variation"/><p>El crecimiento reciente también presenta una geografía desigual.</p></figure></div><blockquote>Para competir en Mijas primero hay que entender sus diferencias.</blockquote></PrintChapter>

  <PrintChapter number="02" label="Evolución territorial" title="Mijas está cambiando más rápido en unos territorios que en otros." className="print-evolution"><TerritorialEvolutionStory/></PrintChapter>

  <PrintChapter number="03" label="Trayectoria electoral" title="Mijas tampoco vota igual." className="print-electoral"><ElectionTimelinePrint/></PrintChapter>

  <PrintChapter number="04" label="Municipales 2023" title="PSOE y PP quedaron separados por solo 2,03 puntos en el conjunto de Mijas." className="print-municipal"><div className="print-kpis print-kpis--four"><article><strong>{two.format(municipal.winner_share_pct)} %</strong><span>{municipal.winner.replace("PSOE-A","PSOE")} · ganador municipal</span></article><article><strong>{municipal.runner_up}</strong><span>segunda fuerza</span></article><article><strong>{two.format(municipal.margin_pct_points)} pp</strong><span>margen</span></article><article><strong>{two.format(municipal.participation_pct)} %</strong><span>participación</span></article></div><figure className="print-main-map"><figcaption>Ganador por sección</figcaption><MijasMap mode="electoral"/><div className="print-legend"><span><i className="psoe"/>PSOE</span><span><i className="pp"/>PP</span><span><i className="other"/>Otras / empate</span></div></figure></PrintChapter>

  <section className="print-component-chapter print-victory"><PsoeVictoryStory/></section>
  <section className="print-component-chapter print-typologies"><TerritorialTypologyStory/></section>
  <section className="print-component-chapter print-relationships"><TerritorialRelationshipsStory printMode/></section>

  <section className="print-dashboard"><header><p>Sigue explorando Mijas</p><h2>Todo el territorio, todas las métricas, en un único Dashboard.</h2><span>El informe te cuenta qué está pasando. El Dashboard te permite explorarlo territorio a territorio.</span></header><figure><figcaption>Dashboard analítico de soctrace</figcaption><img src={dashboardScreenshot} alt="Dashboard analítico de soctrace con métricas territoriales, socioeconómicas y electorales de Mijas"/></figure><ul>{dashboardCapabilities.map(([title,copy])=><li key={title}><strong>{title}</strong><span>{copy}</span></li>)}</ul><footer><a href="https://soctrace.ai/request-demo">soctrace.ai/request-demo</a><a href="mailto:soctrace@gmail.com">soctrace@gmail.com</a></footer></section>

  <section className="print-sources"><div><h2>Fuentes</h2><strong>{campaignSourceLine}</strong><p>Los indicadores combinan fuentes públicas oficiales, armonización territorial y análisis propios de soctrace. Las comparaciones históricas usan territorios equivalentes; los resultados electorales conservan la identidad y el año de cada elección.</p></div></section>
  <footer className="print-running-footer">soctrace · Mijas 2027</footer>
 </article>;
}
