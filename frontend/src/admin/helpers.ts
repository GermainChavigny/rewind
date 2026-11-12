/** Pure helpers for the phone admin (tested in helpers.test.ts). */

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

const KEY_NAMES: Record<string, string> = {
  ' ': 'Espace',
  ArrowUp: '↑',
  ArrowDown: '↓',
  ArrowLeft: '←',
  ArrowRight: '→',
  AudioVolumeMute: 'Muet',
  AudioVolumeUp: 'Vol +',
  AudioVolumeDown: 'Vol −',
  MediaPlayPause: 'Lecture/Pause',
  MediaTrackNext: 'Suivant',
  MediaTrackPrevious: 'Précédent',
  PageUp: 'Page ↑',
  PageDown: 'Page ↓',
  Enter: 'Entrée',
  Escape: 'Échap',
  Backspace: 'Retour',
};

/** A readable name for a keyboard key value ("ArrowUp" → "↑"). */
export function keyLabel(key: string): string {
  return KEY_NAMES[key] ?? (key.length === 1 ? key.toUpperCase() : key);
}

export interface ActionGroup {
  title: string;
  actions: { id: string; label: string }[];
}

export const ACTION_GROUPS: ActionGroup[] = [
  {
    title: 'Chaînes',
    actions: Array.from({ length: 9 }, (_, i) => ({ id: `channel_${i + 1}`, label: `Chaîne ${i + 1}` })),
  },
  {
    title: 'Télé',
    actions: [{ id: 'tv_power', label: 'Allumer / éteindre' }],
  },
  {
    title: 'Lecture',
    actions: [
      { id: 'play_pause', label: 'Lecture / pause' },
      { id: 'next', label: 'Vidéo suivante' },
      { id: 'previous', label: 'Vidéo précédente' },
      { id: 'seek_forward', label: 'Avancer de 15 s' },
      { id: 'seek_backward', label: 'Reculer de 15 s' },
    ],
  },
  {
    title: 'Son et image',
    actions: [
      { id: 'volume_up', label: 'Volume +' },
      { id: 'volume_down', label: 'Volume −' },
      { id: 'darker', label: 'Plus sombre' },
      { id: 'brighter', label: 'Plus clair' },
    ],
  },
  {
    title: 'Réveil',
    actions: [
      { id: 'alarm_toggle', label: 'Activer / couper' },
      { id: 'alarm_later', label: 'Plus tard' },
      { id: 'alarm_earlier', label: 'Plus tôt' },
    ],
  },
];

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
  if (!ms) return 'Son et image synchronisés (aucun décalage).';
  const abs = Math.abs(ms);
  return ms > 0 ? `Le son est retardé de ${abs} ms.` : `Le son est avancé de ${abs} ms.`;
}

/** Alarm chimes (frontend/public/audio/chimes/<id>.mp3, made by scripts/make-chimes.py). */
export const CHIMES: { id: string; label: string; description: string }[] = [
  { id: 'classic', label: 'Classique', description: 'La sonnerie douce' },
  { id: 'bells', label: 'Carillon', description: 'Trois cloches claires' },
  { id: 'musicbox', label: 'Boîte à musique', description: 'Une petite mélodie' },
  { id: 'dawn', label: 'Aube', description: 'Un accord chaud qui enfle' },
  { id: 'drops', label: 'Gouttes', description: 'Des notes de marimba' },
  { id: 'none', label: 'Aucune', description: 'La chaîne seulement' },
];

/** Audio port the A/V offset was last applied to live (restored on Cancel). */
export const liveAudio: { port: string | null } = { port: null };

export interface ProviderPreset {
  id: string;
  name: string;
  kind: 'gemini' | 'openai';
  base_url: string | null;
  model: string;
  keyUrl: string | null;
  note: string;
}

/** AI providers for the Movie Advisor: Gemini, or any OpenAI-compatible API. */
export const PROVIDERS: ProviderPreset[] = [
  { id: 'gemini', name: 'Gemini', kind: 'gemini', base_url: null, model: 'gemini-2.5-flash',
    keyUrl: 'https://aistudio.google.com/apikey', note: 'Google · gratuit pour un usage personnel' },
  { id: 'groq', name: 'Groq', kind: 'openai', base_url: 'https://api.groq.com/openai/v1',
    model: 'llama-3.3-70b-versatile', keyUrl: 'https://console.groq.com/keys', note: 'Très rapide · offre gratuite' },
  { id: 'mistral', name: 'Mistral', kind: 'openai', base_url: 'https://api.mistral.ai/v1',
    model: 'mistral-small-latest', keyUrl: 'https://console.mistral.ai/api-keys', note: 'Français · offre gratuite' },
  { id: 'openrouter', name: 'OpenRouter', kind: 'openai', base_url: 'https://openrouter.ai/api/v1',
    model: 'openai/gpt-4o-mini', keyUrl: 'https://openrouter.ai/keys', note: 'Des centaines de modèles, une seule clé' },
  { id: 'cerebras', name: 'Cerebras', kind: 'openai', base_url: 'https://api.cerebras.ai/v1',
    model: 'llama-3.3-70b', keyUrl: 'https://cloud.cerebras.ai', note: 'Très rapide · offre gratuite' },
  { id: 'openai', name: 'OpenAI', kind: 'openai', base_url: 'https://api.openai.com/v1',
    model: 'gpt-4o-mini', keyUrl: 'https://platform.openai.com/api-keys', note: 'ChatGPT · payant' },
  { id: 'deepseek', name: 'DeepSeek', kind: 'openai', base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat', keyUrl: 'https://platform.deepseek.com/api_keys', note: 'Payant, très bon marché' },
  { id: 'ollama', name: 'Ollama (local)', kind: 'openai', base_url: 'http://127.0.0.1:11434/v1',
    model: 'llama3.2', keyUrl: null, note: 'Sur votre ordinateur, sans clé' },
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

/** Language name in the interface language ("en" → "Anglais"). */
export function languageName(code: string, uiLanguage = 'fr'): string {
  try {
    const name = new Intl.DisplayNames([uiLanguage], { type: 'language' }).of(code) ?? code;
    return name.charAt(0).toLocaleUpperCase(uiLanguage) + name.slice(1);
  } catch {
    return code;
  }
}
