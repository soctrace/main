import { esES } from "@/i18n/locales/es-ES";
import { enUS } from "@/i18n/locales/en-US";

export const defaultLocale = "es-ES";

export const locales = {
  "es-ES": esES,
  "en-US": enUS,
} as const;

export type Locale = keyof typeof locales;

export const t = esES;
