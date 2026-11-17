/** Pure helpers for the phone admin (tested in helpers.test.ts). */
import { language, t } from '../lib/i18n';

/**
 * The playlist id from whatever the user pastes: a full YouTube link
 * (watch?v=…&list=…, playlist?list=…, youtu.be/…?list=…) or the bare id.
 */
export function playlistId(input: string): string {
  const text = input.trim();
  const fromLink = text.match(/[?&]list=([\w-]+)/);
  if (fromLink) return fromLink[1];
  return text;
}

// Symbols, or i18n keys (admin.key.*).
const KEY_NAMES: Record<string, string> = {
  ' ': 'admin.key.space',
  ArrowUp: '↑',
  ArrowDown: '↓',
  ArrowLeft: '←',
  ArrowRight: '→',
  AudioVolumeMute: 'admin.key.mute',
  AudioVolumeUp: 'Vol +',
  AudioVolumeDown: 'Vol −',
  MediaPlayPause: 'admin.key.playpause',
  MediaTrackNext: 'admin.key.next',
  MediaTrackPrevious: 'admin.key.previous',
  PageUp: 'Page ↑',
  PageDown: 'Page ↓',
  Enter: 'admin.key.enter',
  Escape: 'admin.key.escape',
  Backspace: 'admin.key.backspace',
};

/** A readable name for a keyboard key value ("ArrowUp" → "↑"). */
export function keyLabel(key: string): string {
  const name = KEY_NAMES[key];
  if (name) return t(name);
  return key.length === 1 ? key.toUpperCase() : key;
}

export interface ActionGroup {
  id: string;
  title: string;
  actions: { id: string; label: string }[];
}

/** The remote actions by group, labelled in the interface language. */
export function actionGroups(): ActionGroup[] {
  const group = (id: string, actions: string[]) => ({
    id,
    title: t(`admin.act.group.${id}`),
    actions: actions.map((a) => ({ id: a, label: t(`admin.act.${a}`) })),
  });
  return [
    {
      id: 'channels',
      title: t('admin.menu.channels'),
      actions: Array.from({ length: 9 }, (_, i) => ({ id: `channel_${i + 1}`, label: t('admin.ch.default_name', { n: i + 1 }) })),
    },
    group('tv', ['tv_power']),
    group('playback', ['play_pause', 'next', 'previous', 'seek_forward', 'seek_backward']),
    group('picture', ['volume_up', 'volume_down', 'darker', 'brighter']),
    group('alarm', ['alarm_toggle', 'alarm_later', 'alarm_earlier']),
  ];
}

/** "45 s", "2 min", "2 min 30 s". */
export function duration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return rest ? `${m} min ${rest} s` : `${m} min`;
}

/** Signed milliseconds for the A/V offset, as a sentence. */
export function avOffsetText(ms: number): string {
  if (!ms) return t('admin.av.none');
  return t(ms > 0 ? 'admin.av.later' : 'admin.av.earlier', { ms: Math.abs(ms) });
}

/** Alarm chimes (frontend/public/audio/chimes/<id>.mp3, made by scripts/make-chimes.py). */
export const CHIMES = ['classic', 'bells', 'musicbox', 'dawn', 'drops', 'none'];

/** A chime's name and description in the interface language. */
export function chimeText(id: string): { label: string; description: string } {
  return { label: t(`admin.chime.${id}`), description: t(`admin.chime.${id}_hint`) };
}

/** Audio port the A/V offset was last applied to live (restored on Cancel). */
export const liveAudio: { port: string | null } = { port: null };

export interface ProviderPreset {
  id: string;
  name: string;
  kind: 'gemini' | 'openai';
  base_url: string | null;
  model: string;
  keyUrl: string | null;
  note: string; // i18n key
}

/** AI providers for the Movie Advisor: Gemini, or any OpenAI-compatible API. */
export const PROVIDERS: ProviderPreset[] = [
  { id: 'gemini', name: 'Gemini', kind: 'gemini', base_url: null, model: 'gemini-2.5-flash',
    keyUrl: 'https://aistudio.google.com/apikey', note: 'admin.prov.gemini' },
  { id: 'groq', name: 'Groq', kind: 'openai', base_url: 'https://api.groq.com/openai/v1',
    model: 'llama-3.3-70b-versatile', keyUrl: 'https://console.groq.com/keys', note: 'admin.prov.fast_free' },
  { id: 'mistral', name: 'Mistral', kind: 'openai', base_url: 'https://api.mistral.ai/v1',
    model: 'mistral-small-latest', keyUrl: 'https://console.mistral.ai/api-keys', note: 'admin.prov.mistral' },
  { id: 'openrouter', name: 'OpenRouter', kind: 'openai', base_url: 'https://openrouter.ai/api/v1',
    model: 'openai/gpt-4o-mini', keyUrl: 'https://openrouter.ai/keys', note: 'admin.prov.openrouter' },
  { id: 'cerebras', name: 'Cerebras', kind: 'openai', base_url: 'https://api.cerebras.ai/v1',
    model: 'llama-3.3-70b', keyUrl: 'https://cloud.cerebras.ai', note: 'admin.prov.fast_free' },
  { id: 'openai', name: 'OpenAI', kind: 'openai', base_url: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini', keyUrl: 'https://platform.openai.com/api-keys', note: 'admin.prov.openai' },
  { id: 'deepseek', name: 'DeepSeek', kind: 'openai', base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat', keyUrl: 'https://platform.deepseek.com/api_keys', note: 'admin.prov.deepseek' },
  { id: 'ollama', name: 'Ollama (local)', kind: 'openai', base_url: 'http://127.0.0.1:11434/v1',
    model: 'llama3.2', keyUrl: null, note: 'admin.prov.ollama' },
]; // prettier-ignore

/** The preset an advisor entry was made from, guessed from its kind and address. */
export function presetOf(p: { kind?: string; base_url?: string | null }): ProviderPreset | null {
  if (p.kind === 'gemini') return PROVIDERS[0];
  return PROVIDERS.find((x) => x.base_url && p.base_url?.startsWith(x.base_url)) ?? null;
}

/** A local service address as the phone can open it (127.0.0.1 → the TV's address). */
export function phoneUrl(url: string, tvHost: string): string {
  try {
    const u = new URL(url);
    if (['127.0.0.1', 'localhost', '0.0.0.0'].includes(u.hostname)) u.hostname = tvHost;
    return u.toString();
  } catch {
    return url;
  }
}

/** Lower case without accents, to match what is typed ("fr" ~ "Français"). */
export function fold(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

/** Subtitle languages that can be chosen (backend config.SUBTITLE_LANGUAGES). */
export const SUBTITLE_CODES = [
  'ar', 'bg', 'ca', 'cs', 'da', 'de', 'el', 'en', 'es', 'et', 'eu', 'fa', 'fi', 'fr', 'he', 'hi',
  'hr', 'hu', 'id', 'is', 'it', 'ja', 'ko', 'lt', 'lv', 'ms', 'nl', 'no', 'pl', 'pt', 'ro', 'ru',
  'sk', 'sl', 'sr', 'sv', 'th', 'tr', 'uk', 'vi', 'zh',
]; // prettier-ignore
export const MAX_SUBTITLE_LANGUAGES = 4;

/** Language name in the interface language ("en" → "Anglais" in French). */
export function languageName(code: string, uiLanguage = language()): string {
  try {
    const name = new Intl.DisplayNames([uiLanguage], { type: 'language' }).of(code) ?? code;
    return name.charAt(0).toLocaleUpperCase(uiLanguage) + name.slice(1);
  } catch {
    return code;
  }
}
