import { spawn, execFileSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import process from "node:process";
import { chromium } from "playwright";

const port=4178;
const base=`http://127.0.0.1:${port}`;
const output=resolve("docs/review/campaign-intelligence/print");
const screenshots=resolve(output,"screenshots");
const pdfPath=resolve(output,"mijas-2027-report.pdf");
const retained=["Mijas 2027","Doce elecciones. Distintas fotografías.","Claves territoriales de la victoria del PSOE.","Cinco lecturas compartidas.","Estudios superiores y distribución territorial del voto.","Todo el territorio, todas las métricas, en un único Dashboard.","Fuentes"];
const removed=["10 · Fiabilidad","11 · Jerarquía de evidencia","12 · Red reducida","13 · Lo que la evidencia no sostiene","14 · Síntesis consultiva basada en análisis territorial multivariable","Radiografía municipal"];

await mkdir(screenshots,{recursive:true});
const server=spawn(resolve("node_modules/.bin/vite"),["--host","127.0.0.1","--port",String(port),"--strictPort"],{stdio:["inherit","pipe","pipe"]});
let serverOutput="";
server.stdout.on("data",chunk=>{serverOutput+=chunk});
server.stderr.on("data",chunk=>{serverOutput+=chunk});
const stop=()=>{if(!server.killed)server.kill("SIGTERM")};
process.on("exit",stop);process.on("SIGINT",()=>{stop();process.exit(130)});

async function waitForServer(){
 for(let attempt=0;attempt<60;attempt++){
  try{const response=await fetch(`${base}/campaigns/mijas-2027`);if(response.ok)return}catch{}
  await new Promise(resolve=>setTimeout(resolve,250));
 }
 throw new Error(`Vite did not become ready for print audit${serverOutput?`:\n${serverOutput}`:""}`);
}

let browser;
try{
 await waitForServer();
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 await page.goto(`${base}/campaigns/mijas-2027`,{waitUntil:"networkidle"});

 await page.evaluate(()=>{window.__printAuditCalled=false;window.print=()=>{window.__printAuditCalled=true}});
 await page.getByRole("button",{name:"Imprimir / Guardar PDF"}).click();
 await page.locator(".campaign-print-report").waitFor({state:"attached"});
 await page.waitForFunction(()=>window.__printAuditCalled===true);

 await page.emulateMedia({media:"print"});
 await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.querySelectorAll(".campaign-print-report img")].map(image=>image.complete?Promise.resolve():image.decode()))});
 const text=await page.locator(".campaign-print-report").textContent()??"";
 for(const value of retained)if(!text.includes(value))throw new Error(`Missing retained print content: ${value}`);
 for(const value of removed)if(text.includes(value))throw new Error(`Removed module returned in print: ${value}`);
 const electionCount=await page.locator(".print-election-timeline article").count();
 if(electionCount!==12)throw new Error(`Expected 12 print elections, found ${electionCount}`);
 const controls=await page.locator(".campaign-print-report button:visible,.campaign-print-report .exec-explore:visible").count();
 if(controls)throw new Error(`Found ${controls} interactive print controls`);
 const sourcesBox=await page.locator(".print-sources").evaluate(node=>{const box=node.getBoundingClientRect();return{width:box.width,height:box.height,display:getComputedStyle(node).display}});
 if(sourcesBox.display==="none"||sourcesBox.width<300||sourcesBox.height<100)throw new Error("Print sources section is not visibly laid out");
 const visuals=await page.locator('.campaign-print-report svg[role="img"],.campaign-print-report svg[role="group"]').evaluateAll(nodes=>nodes.map(node=>{const rect=node.getBoundingClientRect();return{className:node.getAttribute("class"),label:node.getAttribute("aria-label"),width:rect.width,height:rect.height,paths:node.querySelectorAll("path").length}}));
 const invalidVisuals=visuals.filter(item=>item.width<120||item.height<80||(item.paths>0&&item.paths<2));
 if(invalidVisuals.length)throw new Error(`A required SVG is blank or undersized in print mode: ${JSON.stringify(invalidVisuals)}`);
 const dashboard=await page.locator(".print-dashboard img").evaluate(image=>({complete:image.complete,width:image.naturalWidth,height:image.naturalHeight}));
 if(!dashboard.complete||dashboard.width!==1829||dashboard.height!==909)throw new Error("Dashboard screenshot is not ready at source resolution");

 await page.pdf({path:pdfPath,format:"A4",portrait:true,printBackground:true,displayHeaderFooter:false,preferCSSPageSize:true});
 const info=execFileSync("pdfinfo",[pdfPath],{encoding:"utf8"});
 const pageCount=Number(info.match(/^Pages:\s+(\d+)/m)?.[1]??0);
 const size=info.match(/^Page size:\s+(.+)$/m)?.[1]??"unknown";
 if(!pageCount)throw new Error("Generated PDF has no pages");
 if(!/59[45]\.\d+ x 841\.\d+ pts \(A4\)/.test(size))throw new Error(`Unexpected PDF page size: ${size}`);
 const pdfText=execFileSync("pdftotext",[pdfPath,"-"],{encoding:"utf8"});
 const normalizedPdfText=pdfText.replace(/\s+/g," ").toLocaleLowerCase("es");
 for(const value of retained)if(!normalizedPdfText.includes(value.toLocaleLowerCase("es")))throw new Error(`PDF text missing: ${value}`);
 for(const value of removed)if(normalizedPdfText.includes(value.toLocaleLowerCase("es")))throw new Error(`Removed text present in PDF: ${value}`);
 execFileSync("pdftoppm",["-png","-r","96",pdfPath,resolve(screenshots,"page")],{stdio:"ignore"});
 console.log(JSON.stringify({pdfPath,screenshots,pageCount,pageSize:size,electionCount,svgCount:visuals.length,dashboard},null,2));
}finally{
 if(browser)await browser.close();
 stop();
}
