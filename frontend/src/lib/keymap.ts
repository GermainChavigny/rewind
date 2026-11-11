/**
 * Remote control: maps `KeyboardEvent.key` values to actions, from the keymap
 * in config.toml (`[remote.keys]`).
 */

export type Action =
  | `channel_${1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9}`
  | 'alarm_toggle'
  | 'alarm_later'
  | 'alarm_earlier'
  | 'tv_power'
  | 'play_pause'
  | 'next'
  | 'previous'
  | 'seek_forward'
  | 'seek_backward'
  | 'volume_up'
  | 'volume_down'
  | 'darker'
  | 'brighter';

export type Keymap = Record<string, string[]>;

export function buildKeyLookup(keymap: Keymap): Map<string, Action> {
  const lookup = new Map<string, Action>();
  for (const [action, keys] of Object.entries(keymap)) {
    for (const key of keys) {
      if (!lookup.has(key)) lookup.set(key, action as Action);
    }
  }
  return lookup;
}

/** channel_3 → 3, anything else → null. */
export function channelNumber(action: Action): number | null {
  const m = /^channel_(\d)$/.exec(action);
  return m ? Number(m[1]) : null;
}
