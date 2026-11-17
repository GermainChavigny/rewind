/**
 * Minimal i18n: `t('key', { var })`. The language comes from config.toml
 * (`[general] language`, English by default). Missing keys fall back to
 * English, then to the key. The language is reactive state: a template or a
 * $derived that calls t() follows setLanguage() at once.
 */
import adminEn from './admin.en';
import adminFr from './admin.fr';
import en from './en';
import fr from './fr';
import { lang } from './state.svelte';

type Dict = Record<string, string>;

/** The interface languages, as the admin offers them (name in its own language). */
export const LANGUAGES = [
  { id: 'en', name: 'English' },
  { id: 'fr', name: 'Français' },
] as const;

// The TV strings, then the phone ones (admin and virtual remote).
const dictionaries: Record<string, Dict> = { en: { ...en, ...adminEn }, fr: { ...fr, ...adminFr } };

/** "fr", "fr-FR" → "fr"; unknown → "en". */
export function normalizeLanguage(code: string | null | undefined): string {
  const base = (code ?? '').split('-')[0].toLowerCase();
  return base in dictionaries ? base : 'en';
}

export function setLanguage(code: string): void {
  lang.current = normalizeLanguage(code);
  if (typeof document !== 'undefined') document.documentElement.lang = lang.current;
}

export function language(): string {
  return lang.current;
}

export function t(key: keyof typeof en | string, vars: Record<string, string | number> = {}): string {
  const text = dictionaries[lang.current]?.[key] ?? dictionaries.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
}
