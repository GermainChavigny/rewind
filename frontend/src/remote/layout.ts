/** Virtual remote: button looks and the grid layouts (tested in layout.test.ts). */

import type { GlyphName } from '../components/Glyph.svelte';

/**
 * The remote follows the TV: "tv" (channels, alarm…) or "movies" (the movie
 * screens and playback: transport keys, a touchpad, a key to leave).
 * Each mode has its own layout, saved on the TV.
 */
export type Mode = 'tv' | 'movies';

export interface Layout {
  cols: number;
  rows: number;
  /** action → cell index (row * cols + col) */
  cells: Record<string, number>;
}

export interface ButtonLook {
  /** Text printed on the key (digits, "RÉVEIL"), next to the glyph if any. */
  label: string;
  glyph?: GlyphName;
  /** Silkscreen caption under the key. */
  caption?: string;
  tone: 'power' | 'machine' | 'number' | 'play' | 'volume' | 'alarm' | 'light' | 'home';
}

export const LOOKS: Record<string, ButtonLook> = {
  tv_power: { label: '', glyph: 'power', caption: 'Télé', tone: 'power' },
  machine_power: { label: '', glyph: 'power', caption: 'Éteindre', tone: 'machine' },
  home: { label: '', glyph: 'home', caption: 'Quitter films', tone: 'home' },
  ...Object.fromEntries(
    Array.from({ length: 9 }, (_, i) => [`channel_${i + 1}`, { label: String(i + 1), tone: 'number' }]),
  ),
  play_pause: { label: '', glyph: 'playpause', caption: 'Lecture', tone: 'play' },
  next: { label: '', glyph: 'next', caption: 'Suivant', tone: 'play' },
  previous: { label: '', glyph: 'previous', caption: 'Précédent', tone: 'play' },
  seek_forward: { label: '15', glyph: 'forward', caption: 'Avancer', tone: 'play' },
  seek_backward: { label: '15', glyph: 'rewind', caption: 'Reculer', tone: 'play' },
  volume_up: { label: '', glyph: 'plus', caption: 'Volume', tone: 'volume' },
  volume_down: { label: '', glyph: 'minus', caption: 'Volume', tone: 'volume' },
  darker: { label: '', glyph: 'moon', caption: 'Plus sombre', tone: 'light' },
  brighter: { label: '', glyph: 'sun', caption: 'Plus clair', tone: 'light' },
  alarm_toggle: { label: 'RÉVEIL', caption: 'on / off', tone: 'alarm' },
  alarm_later: { label: '', glyph: 'up', caption: 'Réveil +', tone: 'alarm' },
  alarm_earlier: { label: '', glyph: 'down', caption: 'Réveil −', tone: 'alarm' },
};

/** In the movies, ↑/↓ scroll the list under the cursor (lib/tv.svelte.ts). */
const MOVIE_LOOKS: Record<string, Partial<ButtonLook>> = {
  alarm_later: { caption: 'Défiler', tone: 'play' },
  alarm_earlier: { caption: 'Défiler', tone: 'play' },
};

export function lookOf(action: string, mode: Mode): ButtonLook {
  return mode === 'movies' ? { ...LOOKS[action], ...MOVIE_LOOKS[action] } : LOOKS[action];
}

/** Silkscreen frame colour of each channel key (1–9), printed around key and name. */
export const CHANNEL_INKS = [
  '#e8c547', '#e0679f', '#4fb8d6', '#ec8a3c', '#d9d6cc', '#5fcf95', '#9d92e0', '#d95b4f', '#7fb3e8',
];

/** Default layouts: a classic remote; in the movies, only what is useful there. */
const DEFAULTS: Record<Mode, { cols: number; rows: number; order: (string | null)[] }> = {
  tv: {
    cols: 4,
    rows: 8,
    order: [
      'machine_power', 'tv_power', null, 'alarm_toggle',
      'channel_1', 'channel_2', 'channel_3', 'volume_up',
      'channel_4', 'channel_5', 'channel_6', 'volume_down',
      'channel_7', 'channel_8', 'channel_9', null,
      'previous', 'play_pause', 'next', null,
      'seek_backward', null, 'seek_forward', null,
      'alarm_earlier', 'alarm_later', 'darker', 'brighter',
    ],
  },
  movies: {
    cols: 4,
    rows: 4,
    order: [
      'home', null, 'tv_power', 'machine_power',
      'previous', 'play_pause', 'next', 'volume_up',
      'seek_backward', 'alarm_later', 'seek_forward', 'volume_down',
      'darker', 'alarm_earlier', 'brighter', null,
    ],
  },
}; // prettier-ignore

/** Keys of the movies remote (the rest of the TV remote makes no sense there). */
const MOVIE_ACTIONS = new Set(DEFAULTS.movies.order.filter((a): a is string => !!a));

/** The keys a mode shows, among those the TV offers (keymap actions + extra keys). */
export function actionsFor(mode: Mode, available: string[]): string[] {
  const known = available.filter((a) => a in LOOKS);
  return mode === 'movies' ? known.filter((a) => MOVIE_ACTIONS.has(a)) : known.filter((a) => a !== 'home');
}

export function defaultLayout(actions: string[], mode: Mode = 'tv'): Layout {
  const { cols, rows, order } = DEFAULTS[mode];
  const cells: Record<string, number> = {};
  order.forEach((a, i) => a && actions.includes(a) && (cells[a] = i));
  return fillFree({ cols, rows, cells }, actions);
}

/** Puts `action` on `cell`; the button already there (if any) takes its old place. */
export function moveTo(layout: Layout, action: string, cell: number): Layout {
  const cells = { ...layout.cells };
  const from = cells[action];
  const other = Object.keys(cells).find((a) => cells[a] === cell && a !== action);
  cells[action] = cell;
  if (other !== undefined) {
    if (from === undefined) delete cells[other];
    else cells[other] = from;
  }
  return { ...layout, cells };
}

/** Keeps a saved layout usable when actions or the grid size changed. */
export function sanitize(saved: Layout | null, actions: string[], mode: Mode = 'tv'): Layout {
  if (!saved) return defaultLayout(actions, mode);
  const size = saved.cols * saved.rows;
  const cells: Record<string, number> = {};
  const used = new Set<number>();
  for (const [a, i] of Object.entries(saved.cells)) {
    if (actions.includes(a) && i >= 0 && i < size && !used.has(i)) {
      cells[a] = i;
      used.add(i);
    }
  }
  return fillFree({ cols: saved.cols, rows: saved.rows, cells }, actions);
}

/** Actions without a cell go to the first free cells. */
function fillFree(layout: Layout, actions: string[]): Layout {
  const cells = { ...layout.cells };
  const used = new Set(Object.values(cells));
  let free = 0;
  for (const a of actions) {
    if (a in cells) continue;
    while (used.has(free)) free++;
    if (free >= layout.cols * layout.rows) break;
    cells[a] = free;
    used.add(free);
  }
  return { ...layout, cells };
}
