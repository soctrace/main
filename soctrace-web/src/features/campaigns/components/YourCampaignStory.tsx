import { ArrowRight, Check, CircleDot, Map, MessageSquareText, Route, Timer, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import "./YourCampaignStory.css";

const questions = [
  "¿Cuántos votos necesitas para alcanzar tu objetivo?",
  "¿Qué territorios debes consolidar y en cuáles puedes crecer?",
  "¿Dónde existe mayor competencia para tu candidatura?",
  "¿Dónde tienes apoyo, pero menor movilización?",
  "¿Qué zonas están creciendo y tendrán más peso territorial que en 2023?",
  "¿Qué territorios requieren mensajes diferentes?",
  "¿Dónde merece la pena concentrar trabajo de campo?",
  "¿Qué canales deberían utilizarse en cada tipo de territorio?",
  "¿Cómo deberías distribuir presupuesto, equipo y tiempo?",
  "¿Qué resultado podría producir un escenario conservador, central o favorable?",
];

const modules = [
  { letter: "A", title: "Objetivo electoral", text: "Votos necesarios, punto de partida, distancia al objetivo y escenarios.", icon: CircleDot },
  { letter: "B", title: "Prioridades territoriales", text: "Un marco personalizado para consolidar, competir, movilizar e investigar.", icon: Map },
  { letter: "C", title: "Audiencias territoriales", text: "Perfiles relevantes, estructura del electorado y áreas que requieren validación cualitativa.", icon: Route },
  { letter: "D", title: "Mensajes y comunicación", text: "Pilares, adaptación territorial, canales, frecuencia y trabajo de campo.", icon: MessageSquareText },
  { letter: "E", title: "Asignación de recursos", text: "Presupuesto, equipo, eventos, inversión digital, tiempo y calendario.", icon: Timer },
  { letter: "F", title: "Escenarios electorales", text: "Escenarios conservador, central y favorable con supuestos e incertidumbre explícitos.", icon: TrendingUp },
];

const inputs = ["Candidatura o partido", "Posición electoral de 2023", "Objetivo para 2027", "Candidato o candidata", "Equipo disponible", "Presupuesto de campaña", "Conocimiento territorial", "Fortalezas y debilidades organizativas", "Sondeos o evidencia cualitativa disponible"];

function PreviewVisual({ index }: { index: number }) {
  return <div className={`campaign-preview-visual preview-${index}`} aria-hidden="true"><i/><i/><i/><span/><span/><span/></div>;
}

export function YourCampaignStory() {
  const requestHref = "/request-demo?context=Mijas%202027%20Campaign%20Intelligence";
  return <section id="your-campaign" className="your-campaign" aria-labelledby="your-campaign-title">
    <header className="campaign-transition"><div><span>09 · Tu campaña</span><p>Hasta aquí hemos analizado Mijas.</p><h2>Falta una variable.</h2><strong id="your-campaign-title">Tu candidatura.</strong><small>Los mismos datos producen decisiones diferentes según quién compite, desde qué posición parte y qué quiere conseguir.</small></div></header>

    <section className="campaign-questions" aria-labelledby="campaign-questions-title"><header><span>La estrategia empieza con las preguntas correctas</span><h3 id="campaign-questions-title">Lo que este análisis todavía no puede responder sin conocerte.</h3></header><ol>{questions.map((question, index) => <li key={question}><span>{String(index + 1).padStart(2, "0")}</span><p>{question}</p></li>)}</ol></section>

    <section className="campaign-workspace" aria-labelledby="workspace-title"><header><span>Campaign Intelligence · Tu candidatura</span><h3 id="workspace-title">Así convertimos el conocimiento en campaña.</h3><p>Cada módulo se construye con tu posición electoral, tus objetivos y tu capacidad real de actuación.</p></header><div className="campaign-module-grid">{modules.map(({ letter, title, text, icon: Icon }, index) => <article key={letter}><div className="campaign-module-label"><span>{letter}</span><small>Ejemplo de módulo personalizado</small></div><PreviewVisual index={index}/><Icon/><h4>{title}</h4><p>{text}</p></article>)}</div><aside>Estas visualizaciones muestran la forma del servicio. No contienen prioridades, presupuestos ni previsiones reales para Mijas.</aside></section>

    <section className="campaign-inputs"><div><span>El punto de partida</span><h3>Para convertir Mijas en tu estrategia necesitamos conocerte.</h3><p>No es un formulario. Es el comienzo de una conversación estratégica.</p></div><ul>{inputs.map(input => <li key={input}><Check/>{input}</li>)}</ul></section>

    <section className="campaign-proposition"><span>soctrace combina datos territoriales, historia electoral y estrategia de campaña para responder tres preguntas.</span><div><p>Dónde competir.</p><p>A quién comprender.</p><p>Dónde invertir.</p></div></section>

    <section className="campaign-final-cta"><div><span>Mijas ya está analizada.</span><h3>Ahora diseñemos la estrategia para tu candidatura.</h3><p>Una sesión para situar tu punto de partida, tu objetivo y las decisiones que el territorio exige.</p><div><Link className="campaign-cta-primary" to={requestHref}>Diseñar mi campaña con soctrace <ArrowRight/></Link><Link className="campaign-cta-secondary" to={requestHref}>Solicitar una sesión estratégica</Link></div></div></section>
  </section>;
}

export function CampaignMethodology() {
  const areas = [
    ["Territorio", "Geometrías oficiales de sección y correspondencias geográficas armonizadas."],
    ["Demografía", "Evolución 2021–2025; perfil principal sobre 37 secciones oficiales 2023/2024."],
    ["Elecciones", "Inventario de 12 procesos y comparaciones ajustadas a geografías compatibles."],
    ["Contexto", "Renta, estructura socioeconómica, forma construida y accesibilidad con periodo explícito."],
    ["Análisis", "Perfilado multivariable, agrupación territorial y asociaciones descriptivas."],
    ["Límites", "Los territorios no son personas: una asociación agregada no revela ideología, intención o causalidad individual."],
  ];
  return <section id="methodology-annex" className="campaign-methodology" aria-labelledby="methodology-title"><header><span>10 · Metodología</span><h2 id="methodology-title">La evidencia marca el límite de lo que afirmamos.</h2><p>soctrace solo afirma lo que la evidencia disponible permite sostener.</p></header><div>{areas.map(([title, body]) => <article key={title}><h3>{title}</h3><p>{body}</p></article>)}</div><details><summary>Cómo leer el nivel de evidencia</summary><ul><li><b>Dato verificado</b> · medida directa con fuente y periodo identificados.</li><li><b>Tendencia verificada</b> · evolución comparable sostenida por la serie.</li><li><b>Comparación armonizada</b> · geografías distintas reconciliadas mediante reglas documentadas.</li><li><b>Asociación descriptiva</b> · variables que se mueven juntas; no prueba causalidad.</li><li><b>Evidencia provisional</b> · útil con limitaciones explícitas, como la accesibilidad 2026.</li><li><b>Síntesis consultiva</b> · interpretación profesional dentro de esos límites.</li><li><b>Ejemplo de servicio personalizado</b> · formato del futuro entregable, sin valores inventados.</li></ul></details></section>;
}
