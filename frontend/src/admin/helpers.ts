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
  MediaTrackNext: 'Suivant ⏭',
  MediaTrackPrevious: 'Précédent ⏮',
  PageUp: 'Page ↑',
  PageDown: 'Page ↓',
  Enter: 'Entrée',
  Escape: 'Échap',
  Backspace: 'Retour ⌫',
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
    actions: [{ id: 'tv_power', label: 'Allumer / éteindre (Mute)' }],
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
