/** Virtual remote: button looks and the grid layout (tested in layout.test.ts). */

export interface Layout {
  cols: number;
  rows: number;
  /** action → cell index (row * cols + col) */
  cells: Record<string, number>;
}

export interface ButtonLook {
  label: string;
  caption?: string;
  tone: 'power' | 'number' | 'play' | 'volume' | 'alarm' | 'light';
}

export const LOOKS: Record<string, ButtonLook> = {
  tv_power: { label: 'Télé', caption: 'Télé', tone: 'power' },
  ...Object.fromEntries(
    Array.from({ length: 9 }, (_, i) => [`channel_${i + 1}`, { label: String(i + 1), tone: 'number' }]),
  ),
  play_pause: { label: '►‖', caption: 'Lecture', tone: 'play' },
  next: { label: '►►|', caption: 'Suivant', tone: 'play' },
  previous: { label: '|◄◄', caption: 'Précédent', tone: 'play' },
  seek_forward: { label: '15 ►', caption: 'Avancer', tone: 'play' },
  seek_backward: { label: '◄ 15', caption: 'Reculer', tone: 'play' },
  volume_up: { label: '+', caption: 'Volume', tone: 'volume' },
  volume_down: { label: '−', caption: 'Volume', tone: 'volume' },
  darker: { label: '☾', caption: 'Plus sombre', tone: 'light' },
  brighter: { label: '☀', caption: 'Plus clair', tone: 'light' },
  alarm_toggle: { label: 'RÉVEIL', caption: 'on / off', tone: 'alarm' },
  alarm_later: { label: '▲', caption: 'Réveil +', tone: 'alarm' },
  alarm_earlier: { label: '▼', caption: 'Réveil −', tone: 'alarm' },
};

/** A classic remote: power on top, digits, volume on the side, transport, alarm. */
export function defaultLayout(actions: string[]): Layout {
  const cols = 4;
  const rows = 8;
  const order: (string | null)[] = [
    'tv_power', null, null, 'alarm_toggle',
    'channel_1', 'channel_2', 'channel_3', 'volume_up',
    'channel_4', 'channel_5', 'channel_6', 'volume_down',
    'channel_7', 'channel_8', 'channel_9', null,
    'previous', 'play_pause', 'next', null,
    'seek_backward', null, 'seek_forward', null,
    'alarm_earlier', 'alarm_later', 'darker', 'brighter',
  ]; // prettier-ignore
  const cells: Record<string, number> = {};
  order.forEach((a, i) => a && actions.includes(a) && (cells[a] = i));
  // Any action the layout above does not know goes to the first free cells.
  let free = 0;
  for (const a of actions) {
    if (a in cells) continue;
    while (Object.values(cells).includes(free)) free++;
    if (free >= cols * rows) break;
    cells[a] = free;
  }
  return { cols, rows, cells };
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
export function sanitize(saved: Layout | null, actions: string[]): Layout {
  if (!saved) return defaultLayout(actions);
  const size = saved.cols * saved.rows;
  const cells: Record<string, number> = {};
  const used = new Set<number>();
  for (const [a, i] of Object.entries(saved.cells)) {
    if (actions.includes(a) && i >= 0 && i < size && !used.has(i)) {
      cells[a] = i;
      used.add(i);
    }
  }
  // New actions (not in the saved layout) go to the first free cells.
  let free = 0;
  for (const a of actions) {
    if (a in cells) continue;
    while (used.has(free)) free++;
    if (free >= size) break;
    cells[a] = free;
    used.add(free);
  }
  return { cols: saved.cols, rows: saved.rows, cells };
}
