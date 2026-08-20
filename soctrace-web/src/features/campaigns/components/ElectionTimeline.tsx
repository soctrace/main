import { CheckCircle2, Equal, Info } from "lucide-react";
import { useState, type ReactNode } from "react";
import electoralJson from "@/features/campaigns/data/generated/mijas-2027-block-b-electoral-diagnosis.json";

type Inventory={election_id:number;election_type:string;official_name:string;election_date:string;sections:number;geography_year:number;source_file:string};
type Summary={election_id:number;winner:string;winner_share_pct:number;participation_pct:number;margin_pct_points:number};
type Profile={election_id:number;display_name:string;winner_tie:boolean};
type Snapshot={electionInventory:Inventory[];municipalSummaries:Summary[];sectionProfiles:Profile[];latestElection:{election_id:number};evidenceReferences:{partyShare:{calculation:string}}};

const data=electoralJson as unknown as Snapshot;
const decimal=new Intl.NumberFormat("es-ES",{minimumFractionDigits:1,maximumFractionDigits:1});
const shortDate=new Intl.DateTimeFormat("es-ES",{day:"2-digit",month:"short",year:"numeric"});
const summary=(id:number)=>{const item=data.municipalSummaries.find(x=>x.election_id===id);if(!item)throw new Error(`Missing election summary ${id}`);return item};

type PartyFamily="pp"|"psoe"|"vox"|"cs"|"local"|"other";
function partyPresentation(value:string,{compact=false}={}){
 const normalized=value.trim().toUpperCase().replace(/[^A-Z0-9]/g,"");
 const family:PartyFamily=normalized==="PP"||normalized==="PARTIDOPOPULAR"?"pp":normalized==="PSOE"||normalized==="PSOEA"?"psoe":normalized==="VOX"?"vox":normalized==="CS"||normalized==="CIUDADANOS"?"cs":normalized==="LOCAL"?"local":"other";
 const label=family==="pp"?"PP":family==="psoe"&&compact?"PSOE":value;
 return {family,label,className:`electoral-party electoral-party--${family}`};
}

function Status({kind="verified",children}:{kind?:"verified"|"baseline";children:ReactNode}){return <span className={`electoral-status electoral-status--${kind}`}><CheckCircle2/>{children}</span>}

export function ElectionTimeline(){
 const ordered=[...data.electionInventory].sort((a,b)=>a.election_date.localeCompare(b.election_date));
 const [selected,setSelected]=useState(ordered[ordered.length-1].election_id);
 const active=summary(selected),inv=ordered.find(x=>x.election_id===selected)!;
 const ties=data.sectionProfiles.filter(x=>x.election_id===selected&&x.winner_tie);
 const activeParty=partyPresentation(active.winner);
 return <div className="electoral-timeline"><div className="electoral-timeline-track" role="tablist" aria-label="Elecciones disponibles">{ordered.map((item,index)=>{const winner=partyPresentation(summary(item.election_id).winner,{compact:true});return <button key={item.election_id} role="tab" aria-selected={selected===item.election_id} onClick={()=>setSelected(item.election_id)}><em className={`electoral-timeline-winner ${winner.className}`}>{winner.label}</em><i className={selected===item.election_id?"active":""}/><span>{item.election_type==="PARLAMENTO_EUROPEO"?"UE":item.election_type==="MUNICIPALES"?"MUN":item.election_type==="ANDALUZAS"?"AND":"CON"}</span><strong>{new Date(`${item.election_date}T12:00:00`).getFullYear()}</strong>{index===ordered.length-1?<small>Última</small>:null}</button>})}</div><article className="electoral-timeline-detail" aria-live="polite"><header><div><p>{inv.official_name}</p><h4>{shortDate.format(new Date(`${inv.election_date}T12:00:00`))}</h4></div>{selected===data.latestElection.election_id?<Status kind="baseline">Última elección cargada</Status>:<Status>Resultado verificado</Status>}</header><div><span>Ganador municipal</span><strong className={activeParty.className}>{activeParty.label}</strong><small>{decimal.format(active.winner_share_pct)} %</small></div><div><span>Participación</span><strong>{decimal.format(active.participation_pct)} %</strong></div><div><span>Margen</span><strong>{decimal.format(active.margin_pct_points)} pp</strong></div>{ties.length?<p className="electoral-tie-note"><Equal/> {ties.length} empate{ties.length>1?"s":""} en primera posición: {ties.map(x=>x.display_name.replace(/^Sección \d+ · /,"")).join(", ")}.</p>:null}<details className="electoral-evidence"><summary><Info/> Evidencia y método</summary><dl><div><dt>Valor</dt><dd>{decimal.format(active.winner_share_pct)} %</dd></div><div><dt>Denominador</dt><dd>votos a candidaturas</dd></div><div><dt>Elección</dt><dd>{inv.official_name} · {inv.election_date}</dd></div><div><dt>Geografía</dt><dd>{inv.geography_year} · {inv.sections} secciones</dd></div><div><dt>Ámbito</dt><dd>Municipio de Mijas</dd></div><div><dt>Fuente</dt><dd>{inv.source_file}</dd></div><div><dt>Cálculo</dt><dd>{data.evidenceReferences.partyShare.calculation}</dd></div><div><dt>Estado</dt><dd>Resultado electoral verificado</dd></div><div><dt>Comparabilidad</dt><dd>Lectura dentro de la geografía de la elección</dd></div></dl></details></article></div>
}
