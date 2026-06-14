export const enabledSections = {
  navbar: true,
  hero: true,
  logoStrip: false,
  intro: false,
  story1: false,
  story2: false,
  story3: false,
  screenshots: false,
  changelog: false,
  testimonials: false,
  pricing: false,
  cta: false,
  footer: true,
} as const;

export type SectionKey = keyof typeof enabledSections;
