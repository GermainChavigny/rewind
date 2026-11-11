/**
 * Minimal i18n: `t('key', { var })`. The language comes from config.toml
 * (`[general] language`). Missing keys fall back to French, then to the key.
 */
import fr from './fr';

type Dict = Record<string, string>;

const dictionaries: Record<string, Dict> = { fr };
let current: Dict = fr;

export function setLanguage(lang: string): void {
  current = dictionaries[lang] ?? fr;
}

export function t(key: keyof typeof fr | string, vars: Record<string, string | number> = {}): string {
  const text = current[key] ?? (fr as Dict)[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
}
