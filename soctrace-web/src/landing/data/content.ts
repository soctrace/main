import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Blocks,
  ChartColumnBig,
  Command,
  FileCode2,
  Radar,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
};

export type Capability = {
  title: string;
  description: string;
  eyebrow: string;
  icon: LucideIcon;
  bullets: string[];
};

export type StoryBlock = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  metrics: string[];
};

export type ScreenshotShowcase = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  points: string[];
};

export type ChangelogItem = {
  version: string;
  date: string;
  summary: string;
};

export type Testimonial = {
  quote: string;
  name: string;
  role: string;
};

export type PricingPlan = {
  name: string;
  price: string;
  description: string;
  features: string[];
  featured?: boolean;
};

export type HeroStat = {
  label: string;
  value: string;
};

export type HeroHighlight = {
  icon: LucideIcon;
  text: string;
};

export const navItems: NavItem[] = [
  { label: "Inicio", href: "/" },
];

export const socialProof = [
  "Equipos de estrategia",
  "Consultoras electorales",
  "Analistas territoriales",
  "Partners de datos",
  "Operaciones de campaña",
];

export const capabilities: Capability[] = [
  {
    eyebrow: "Territorio en contexto",
    title: "Une demografía, resultados y señales operativas en un solo flujo.",
    description:
      "La landing MVP presenta el producto como un sistema de lectura territorial con capas accionables, vistas comparables y salidas listas para decisión.",
    icon: Radar,
    bullets: [
      "Capas cruzadas por sección censal y zona operativa",
      "Comparativas rápidas sin saltar entre herramientas",
      "Lectura ejecutiva y profundidad analítica en la misma interfaz",
    ],
  },
  {
    eyebrow: "Stack preparado",
    title: "Arquitectura modular para crecer sin rehacer la home.",
    description:
      "Cada bloque está desacoplado y controlado por configuración, para activar nuevas narrativas conforme el producto gane casos de uso o prueba social.",
    icon: Blocks,
    bullets: [
      "Secciones activables con `enabledSections`",
      "Contenido, layout y estilo desacoplados",
      "Preparada para iterar por campañas, clientes o verticales",
    ],
  },
  {
    eyebrow: "Entrega premium",
    title: "Estética oscura, técnica y sobria, inspirada en software de alto valor.",
    description:
      "El MVP ya deja el tono visual de una plataforma seria: superficies profundas, tipografía marcada y previews tipo consola/panel para anticipar producto real.",
    icon: Sparkles,
    bullets: [
      "Dark mode como identidad principal",
      "Componentes visuales reutilizables para futuras capturas",
      "Jerarquía clara para escalar a una landing larga",
    ],
  },
];

export const storyBlocks: StoryBlock[] = [
  {
    id: "future-story-1",
    eyebrow: "Story block 01",
    title: "Del dato crudo a una lectura territorial usable.",
    description:
      "Sección reservada para contar cómo se ensamblan fuentes, transformaciones y visualización sin convertir la home en una ficha técnica.",
    metrics: ["Pipelines versionados", "Marts analíticos", "Outputs listos para cliente"],
  },
  {
    id: "future-story-2",
    eyebrow: "Story block 02",
    title: "Compara secciones, patrones y oportunidades con menos fricción.",
    description:
      "Bloque preparado para explicar workflows y casos de uso reales con estructura editorial similar a la referencia larga.",
    metrics: ["Mapas comparables", "Segmentación operativa", "Insights accionables"],
  },
  {
    id: "future-story-3",
    eyebrow: "Story block 03",
    title: "Diseñado para equipos que necesitan claridad y velocidad.",
    description:
      "Espacio futuro para reforzar colaboración, reporting y despliegue en operaciones con mensajes de producto más maduros.",
    metrics: ["Menos hojas sueltas", "Menos pasos manuales", "Más consistencia"],
  },
];

export const screenshotShowcases: ScreenshotShowcase[] = [
  {
    id: "screenshots",
    eyebrow: "Screens",
    title: "Galería preparada para capturas de producto reales.",
    description:
      "Módulo reservado para reemplazar previews sintéticos por screenshots del producto conforme avance el roadmap comercial.",
    points: ["Comparadores", "Paneles de detalle", "Capas de mapa", "Evolución temporal"],
  },
];

export const changelogItems: ChangelogItem[] = [
  {
    version: "v0.3",
    date: "Abr 2026",
    summary: "Base modular de landing, sistema de secciones y nuevo lenguaje visual.",
  },
  {
    version: "v0.4",
    date: "Próximo",
    summary: "Inserción de screenshots reales, narrativa larga y bloques de confianza.",
  },
];

export const testimonials: Testimonial[] = [
  {
    quote:
      "Nos permitió aterrizar contexto territorial mucho más rápido que con dashboards genéricos.",
    name: "Responsable de estrategia",
    role: "Equipo de campaña",
  },
  {
    quote: "La lectura por secciones pasó de intuición dispersa a sistema compartido.",
    name: "Dirección de análisis",
    role: "Consultora política",
  },
];

export const pricingPlans: PricingPlan[] = [
  {
    name: "Starter",
    price: "Desde 490 EUR",
    description: "Para validar el producto con una necesidad operativa concreta.",
    features: ["Landing corta", "1 flujo principal", "Soporte de activación"],
  },
  {
    name: "Growth",
    price: "Custom",
    description: "Para equipos que quieren adaptar narrativa, demos y módulos por vertical.",
    features: ["Secciones largas", "Narrativa por caso de uso", "Capturas y prueba social"],
    featured: true,
  },
];

export const heroStats: HeroStat[] = [
  { label: "Módulos activables", value: "11" },
  { label: "Tema visual", value: "Oscuro premium" },
  { label: "Base tecnológica", value: "React + TS" },
];

export const heroHighlights: HeroHighlight[] = [
  { icon: Command, text: "Narrativa modular tipo flagship landing" },
  { icon: ShieldCheck, text: "Arquitectura limpia y mantenible" },
  { icon: FileCode2, text: "Preparada para screenshots y casos reales" },
  { icon: ChartColumnBig, text: "Orientada a producto de analítica territorial" },
  { icon: Activity, text: "MVP corto con presencia sólida" },
];
