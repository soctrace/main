import { Link } from "react-router-dom";
import {
  ArrowRight,
  BotMessageSquare,
  BrainCircuit,
  Layers3,
  MapPin,
  MessageSquare,
  Sparkles,
  Target,
  UsersRound,
} from "lucide-react";
import { ActionButton } from "@/landing/components/ActionButton";
import { SectionShell } from "@/landing/components/SectionShell";
import type { HeroHighlight, HeroStat } from "@/landing/data/content";
import heroMapMadrid from "@/assets/hero-map-madrid.png";

type HeroSectionProps = {
  stats: HeroStat[];
  highlights: HeroHighlight[];
};

const intelligenceCards = [
  {
    title: "Inteligencia electoral",
    text: "Entiende cómo vota cada barrio y por qué.",
    icon: Target,
    tone: "violet",
  },
  {
    title: "Inteligencia demográfica",
    text: "Comprende quién vive detrás de cada decisión.",
    icon: UsersRound,
    tone: "blue",
  },
  {
    title: "Inteligencia territorial",
    text: "Detecta oportunidades calle a calle.",
    icon: MapPin,
    tone: "green",
  },
  {
    title: "Analista político IA",
    text: "Haz preguntas. Obtén respuestas estratégicas.",
    icon: Sparkles,
    tone: "violet",
  },
] as const;

const iconTone = {
  violet:
    "border-violet-300/20 bg-violet-500/18 text-violet-200 shadow-[0_0_38px_rgba(139,92,246,0.24)]",
  blue:
    "border-blue-300/20 bg-blue-500/18 text-blue-200 shadow-[0_0_38px_rgba(59,130,246,0.24)]",
  green:
    "border-emerald-300/20 bg-emerald-500/18 text-emerald-200 shadow-[0_0_38px_rgba(16,185,129,0.2)]",
} as const;

const metricItems = [
  {
    value: "2,000+",
    label: "Capas de inteligencia territorial",
    icon: Layers3,
    tone: "violet",
  },
  {
    value: "Calle a calle",
    label: "Granularidad",
    icon: MapPin,
    tone: "blue",
  },
  {
    value: "IA aplicada",
    label: "Recomendaciones estratégicas",
    icon: BrainCircuit,
    tone: "green",
  },
  {
    value: "1 pregunta",
    label: "Para entender un municipio completo",
    icon: MessageSquare,
    tone: "violet",
  },
] as const;

function AgeStructurePanel() {
  const bars = [
    { label: "0-14", value: 34, text: "8,3%" },
    { label: "15-24", value: 54, text: "13,2%" },
    { label: "25-34", value: 73, text: "17,8%" },
    { label: "35-44", value: 77, text: "18,7%" },
    { label: "45-54", value: 70, text: "17,1%" },
    { label: "55-74", value: 61, text: "15,0%" },
    { label: "75+", value: 21, text: "2,7%" },
  ];

  return (
    <div className="panel-dark overflow-hidden p-5 sm:p-6">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-base font-semibold text-white">Estructura de edad</h3>
        <div className="hidden rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 py-2 text-[0.66rem] text-slate-400 sm:block">
          Ver por&nbsp; <span className="text-slate-200">edad media</span>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[0.52fr_1fr]">
        <div>
          <p className="text-xs text-slate-400">Edad media</p>
          <p className="mt-3 text-4xl font-medium text-white">44,2</p>
          <p className="mt-1 text-xs text-slate-500">años</p>
          <p className="mt-8 text-xs text-slate-400">Distribución por edad</p>
        </div>

        <div className="relative min-h-[170px] overflow-hidden rounded-2xl border border-white/[0.06] bg-[#07101b]">
          <img
            src={heroMapMadrid}
            alt=""
            className="absolute inset-0 h-full w-full object-cover opacity-75 saturate-125"
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_54%_44%,rgba(250,204,21,0.32),transparent_25%),linear-gradient(90deg,rgba(5,7,12,0.48),transparent_55%)]" />
        </div>
      </div>

      <div className="mt-5 flex h-32 items-end gap-3 border-b border-white/[0.06] pb-4">
        {bars.map((bar) => (
          <div key={bar.label} className="flex flex-1 flex-col items-center gap-2">
            <span className="text-[0.62rem] text-slate-300">{bar.text}</span>
            <div
              className="w-full max-w-8 rounded-t-md bg-[linear-gradient(180deg,rgba(59,130,246,0.8),rgba(30,64,175,0.32))]"
              style={{ height: `${bar.value}%` }}
            />
            <span className="text-[0.62rem] text-slate-500">{bar.label}</span>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <div className="h-3 rounded-full bg-[linear-gradient(90deg,#e4d64c,#7fc96b,#21b6a8,#1888db,#153d95)]" />
        <div className="mt-2 flex justify-between text-[0.62rem] text-slate-400">
          <span>&lt; 18</span>
          <span>18 - 24</span>
          <span>25 - 34</span>
          <span>35 - 44</span>
          <span>45 - 54</span>
          <span>55+</span>
        </div>
      </div>
    </div>
  );
}

function QualityOfLifePanel() {
  const topAreas = [
    ["El Chaparral", "8,7"],
    ["La Cala", "8,5"],
    ["Calahonda", "8,1"],
    ["Riviera del Sol", "7,9"],
    ["Mijas Pueblo", "7,8"],
  ];
  const lowAreas = [
    ["Las Lagunas", "3,2"],
    ["La Zona", "3,4"],
    ["Calypso", "3,6"],
  ];

  return (
    <div className="panel-dark overflow-hidden p-5 sm:p-6">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-base font-semibold text-white">Índice de calidad de vida</h3>
        <div className="hidden rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 py-2 text-[0.66rem] text-slate-400 sm:block">
          Ver por&nbsp; <span className="text-slate-200">puntuación global</span>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[0.45fr_1fr_0.6fr]">
        <div>
          <p className="text-xs text-slate-400">Puntuación global</p>
          <p className="mt-3 text-4xl font-medium text-white">7,6</p>
          <p className="mt-1 text-xs text-slate-500">/10</p>
          <div className="mt-8 space-y-2 text-xs text-slate-400">
            {[
              ["Muy alta", "bg-emerald-400"],
              ["Alta", "bg-lime-400"],
              ["Media", "bg-yellow-400"],
              ["Baja", "bg-orange-400"],
              ["Muy baja", "bg-red-400"],
            ].map(([label, color]) => (
              <div key={label} className="flex items-center gap-2">
                <span className={`h-3 w-3 rounded-full ${color}`} />
                {label}
              </div>
            ))}
          </div>
        </div>

        <div className="relative min-h-[230px] overflow-hidden rounded-2xl border border-white/[0.06] bg-[#07140f]">
          <img
            src={heroMapMadrid}
            alt=""
            className="absolute inset-0 h-full w-full object-cover opacity-65 hue-rotate-[75deg] saturate-150"
          />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_48%_46%,rgba(234,179,8,0.32),transparent_24%),linear-gradient(180deg,transparent,rgba(5,7,12,0.28))]" />
        </div>

        <div className="grid gap-6 text-xs">
          <div>
            <p className="font-semibold text-slate-300">Mejores zonas</p>
            <div className="mt-3 space-y-2">
              {topAreas.map(([label, score], index) => (
                <div key={label} className="grid grid-cols-[1rem_1fr_auto] gap-2 text-slate-400">
                  <span>{index + 1}</span>
                  <span>{label}</span>
                  <span className="text-yellow-300">{score}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="font-semibold text-slate-300">Zonas más bajas</p>
            <div className="mt-3 space-y-2">
              {lowAreas.map(([label, score], index) => (
                <div key={label} className="grid grid-cols-[1rem_1fr_auto] gap-2 text-slate-400">
                  <span>{index + 1}</span>
                  <span>{label}</span>
                  <span className="text-red-300">{score}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.035] p-4 text-xs text-slate-400 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2 text-slate-100">
          <Sparkles className="h-4 w-4 text-blue-300" />
          <span>21 indicadores</span>
        </div>
        <p className="leading-5">
          que cubren entorno, servicios, movilidad, seguridad, vivienda, educación y más.
        </p>
      </div>
    </div>
  );
}

export function HeroSection({ stats, highlights }: HeroSectionProps) {
  void stats;
  void highlights;

  return (
    <SectionShell id="hero" className="pt-14 sm:pt-20 lg:pb-14">
      <div className="grid items-center gap-14 lg:grid-cols-[minmax(0,0.78fr)_minmax(520px,1fr)]">
        <div>
          <h1 className="max-w-4xl text-balance text-5xl font-semibold leading-[0.94] text-white sm:text-6xl lg:text-[4.85rem]">
            Decisiones con IA para la vida real
          </h1>

          <p className="section-copy mt-7 max-w-2xl">
            Convierte la complejidad local en decisiones más rápidas, claras e inteligentes.
          </p>

          <div className="mt-9 flex flex-col gap-4 sm:flex-row">
            <Link
              to="/login"
              className="inline-flex items-center justify-center rounded-full border border-[rgba(74,111,165,0.24)] bg-[linear-gradient(135deg,rgba(74,111,165,0.12),rgba(244,124,42,0.05))] px-5 py-3 text-sm font-semibold text-white transition duration-200 hover:-translate-y-0.5 hover:border-[rgba(244,124,42,0.28)]"
            >
              Abrir demo
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              to="/request-demo"
              className="inline-flex items-center justify-center rounded-full border border-[rgba(74,111,165,0.24)] bg-[linear-gradient(135deg,rgba(74,111,165,0.08),rgba(244,124,42,0.05))] px-5 py-3 text-sm font-semibold text-white transition duration-200 hover:-translate-y-0.5 hover:border-[rgba(244,124,42,0.28)] hover:bg-[linear-gradient(135deg,rgba(74,111,165,0.12),rgba(244,124,42,0.08))]"
            >
              Solicitar demo
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="relative lg:pt-1">
          <div className="absolute -left-8 top-10 h-40 w-40 rounded-full bg-soc-accent/20 blur-3xl" />
          <div className="absolute -right-4 bottom-10 h-36 w-36 rounded-full bg-soc-warm/12 blur-3xl" />
          <div className="panel-dark relative overflow-hidden p-3">
            <div className="absolute inset-x-0 top-0 h-24 bg-[linear-gradient(180deg,rgba(74,111,165,0.16),transparent)]" />
            <img
              src={heroMapMadrid}
              alt="Mapa demográfico y electoral de Madrid"
              className="relative block w-full rounded-[1.5rem] border border-[rgba(74,111,165,0.18)] object-cover shadow-[0_24px_90px_rgba(0,0,0,0.28)]"
            />
          </div>
        </div>
      </div>

      <div className="mt-16 grid gap-5 sm:grid-cols-2 lg:mt-20 lg:grid-cols-4">
        {intelligenceCards.map(({ title, text, icon: Icon, tone }) => (
          <article
            key={title}
            className="panel-soft min-h-[210px] p-6 shadow-[0_18px_70px_rgba(0,0,0,0.18)] sm:min-h-[250px] lg:min-h-[270px]"
          >
            <div className={`flex h-16 w-16 items-center justify-center rounded-full border ${iconTone[tone]}`}>
              <Icon className="h-8 w-8" />
            </div>
            <h2 className="mt-8 text-2xl font-semibold leading-tight text-white">{title}</h2>
            <p className="mt-7 max-w-[16rem] text-sm leading-6 text-slate-400">{text}</p>
          </article>
        ))}
      </div>

      <div className="mx-auto mt-16 max-w-4xl text-center lg:mt-20">
        <h2 className="text-balance text-3xl font-semibold leading-tight text-white sm:text-4xl">
          Plataforma de microsegmentación y consultoría de comunicación
        </h2>
        <p className="mt-4 text-base text-slate-400 sm:text-lg">
          Optimiza tus recursos de comunicación hacia tu público objetivo.
        </p>
      </div>

      <div className="mt-10 grid gap-5 lg:grid-cols-2">
        <AgeStructurePanel />
        <QualityOfLifePanel />
      </div>

      <div className="mx-auto mt-16 max-w-3xl text-center lg:mt-20">
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">
          Datos accionables con IA, sin fricción
        </h2>
      </div>

      <div className="panel-dark mt-8 grid overflow-hidden p-0 sm:grid-cols-2 lg:grid-cols-4">
        {metricItems.map(({ value, label, icon: Icon, tone }, index) => (
          <div
            key={value}
            className={`flex min-h-[180px] flex-col items-center justify-center px-6 py-8 text-center ${
              index > 0 ? "border-t border-white/[0.08] sm:border-l sm:border-t-0" : ""
            } ${index === 2 ? "sm:border-t lg:border-t-0" : ""}`}
          >
            <Icon className={`h-12 w-12 ${tone === "green" ? "text-emerald-300" : tone === "blue" ? "text-blue-300" : "text-violet-300"}`} />
            <p className="mt-5 text-2xl font-semibold text-white sm:text-3xl">{value}</p>
            <p className="mt-3 max-w-[11rem] text-sm leading-6 text-slate-400">{label}</p>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}
