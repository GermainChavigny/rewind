/** Typed client for the REWIND backend (same origin). */

import type { Keymap } from './keymap';

export interface Channel {
  number: number;
  id: string;
  name: string;
  show_name: boolean;
  logo: string | null;
  kind: 'youtube' | 'library';
  playlist_id: string | null;
  save_progress: boolean;
  alarm: boolean;
}

export interface ModuleState {
  id: string;
  configured: boolean;
}

export interface UiSettings {
  language: string;
  keymap: Keymap;
  alarm: {
    step_minutes: number;
    sound_ramp_s: number;
    video_delay_s: number;
    video_ramp_s: number;
    max_duration_s: number;
  };
  crt_effects: boolean;
}

export interface Alarm {
  time: string;
  enabled: boolean;
}

export interface DisplayState {
  darkness: number;
  volume: number;
}

export interface PlaylistProgress {
  video_id?: string;
  video_index?: number;
  position?: number;
  videos?: Record<string, number>;
}

export interface Weather {
  location: string | null;
  code: number;
  hour: string;
  day: { code: number; hi: number; lo: number };
  periods: { id: 'morning' | 'afternoon' | 'evening'; code: number; temp: number }[];
}

export interface Logo {
  id: string;
  url: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, `${method} ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  ui: () => call<UiSettings>('GET', '/api/ui'),
  modules: () => call<ModuleState[]>('GET', '/api/modules'),
  channels: () => call<Channel[]>('GET', '/api/channels'),
  logos: () => call<Logo[]>('GET', '/api/logos'),
  state: () => call<DisplayState>('GET', '/api/state'),
  patchState: (patch: Partial<DisplayState>) => call<DisplayState>('PATCH', '/api/state', patch),
  progress: (playlistId: string) =>
    call<PlaylistProgress>('GET', `/api/progress/${encodeURIComponent(playlistId)}`),
  saveProgress: (playlistId: string, p: { video_id: string; video_index: number; position: number }) =>
    call<unknown>('PUT', `/api/progress/${encodeURIComponent(playlistId)}`, p),
  alarm: () => call<Alarm>('GET', '/api/alarm'),
  saveAlarm: (a: Alarm) => call<Alarm>('PUT', '/api/alarm', a),
  power: () => call<{ on: boolean }>('GET', '/api/tv/power'),
  setPower: (on: boolean) => call<{ on: boolean }>('POST', '/api/tv/power', { on }),
  weather: () => call<Weather>('GET', '/api/weather'),
};
