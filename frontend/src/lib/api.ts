/** Typed client for the REWIND backend (same origin). */

import type { Keymap } from './keymap';

export interface Channel {
  number: number;
  id: string;
  name: string;
  logo_style: number; // retro logo style, 1 or 2
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
    chime: string; // audio/chimes/<id>.mp3, or 'none'
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

export type MediaKind = 'movie' | 'series' | 'episode' | 'pack';
export type MediaStatus = 'queued' | 'downloading' | 'fetching-subs' | 'transcoding' | 'ready' | 'error';

export interface Season {
  season_number: number;
  episode_count: number;
  name?: string;
}

export interface AudioTrack {
  index: number;
  lang: string;
  title: string;
}

/** A library row (columns + free-form data merged by the backend). */
export interface Media {
  id: string;
  kind: MediaKind;
  parent_id: string | null;
  title: string;
  year: number | null;
  season: number | null;
  episode: number | null;
  status: MediaStatus;
  file: string | null;
  duration: number;
  position: number;
  watched: boolean;
  last_played_at: number | null;
  added_at: number;
  poster?: string | null;
  overview?: string | null;
  subtitles?: Record<string, string>;
  subtitle_mode?: 'fr' | 'en' | 'off' | null;
  subtitle_offsets?: Record<string, number>;
  audio_tracks?: AudioTrack[];
  audio_track?: number;
  fit?: 'contain' | 'cover';
  progress?: { download?: number; transcode?: number };
  error?: string | null;
  // series
  tmdb_status?: string;
  seasons?: Season[];
}

export interface Job {
  title: string;
  status: MediaStatus;
  progress: { download?: number; transcode?: number };
  error: string | null;
  kind: MediaKind;
  parent_id: string | null;
  season: number | null;
  episode: number | null;
}

export interface Torrent {
  title: string;
  magnet: string;
  hash: string | null;
  seeders: number;
  size: number | null;
  size_label: string | null;
}

export interface MovieResult {
  title: string;
  release: string;
  year: number | null;
  tmdb_id: number | null;
  imdb_id: string | null;
  poster_url: string | null;
  overview: string | null;
  torrent: Torrent;
}

export interface ShowResult {
  tmdb_id: number;
  title: string;
  original_title: string;
  year: number | null;
  poster_url: string | null;
  overview: string | null;
}

export type EpisodeState = 'missing' | 'downloading' | 'ready' | 'error';

export interface EpisodeView {
  episode: number;
  id: string;
  title: string | null;
  overview: string | null;
  still: string | null;
  state: EpisodeState;
  phase: string | null;
  progress: number;
  position: number;
  duration: number;
  watched: boolean;
}

export interface SeasonView {
  season: number;
  episodes: EpisodeView[];
  notice: string | null;
}

export interface Recommendation {
  id: string;
  title: string;
  query: string;
  kind: 'movie' | 'series';
  year: number | null;
  tmdb_id: number | null;
  poster_url: string | null;
  summary: string;
}

export interface LibraryFeatures {
  search: boolean;
  series: boolean;
  advisor: boolean;
}

export type ProbeState = 'reachable' | 'unreachable' | 'pending' | 'unknown';

export interface PlaybackPatch {
  position?: number;
  duration?: number;
  watched?: boolean;
  started?: boolean;
  subtitle_mode?: 'fr' | 'en' | 'off';
  subtitle_offsets?: Record<string, number>;
  audio_track?: number;
  fit?: 'contain' | 'cover';
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
  if (!res.ok) {
    // FastAPI errors carry a readable `detail`.
    const detail = await res
      .json()
      .then((b: { detail?: unknown }) => (typeof b.detail === 'string' ? b.detail : null))
      .catch(() => null);
    throw new ApiError(res.status, detail ?? `${method} ${path} → ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  ui: () => call<UiSettings>('GET', '/api/ui'),
  modules: () => call<ModuleState[]>('GET', '/api/modules'),
  channels: () => call<Channel[]>('GET', '/api/channels'),
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

  // library
  library: () => call<Media[]>('GET', '/api/library'),
  libraryFeatures: () => call<LibraryFeatures>('GET', '/api/library/features'),
  disk: () => call<{ free_bytes: number; total_bytes: number }>('GET', '/api/library/disk'),
  jobs: () => call<Record<string, Job>>('GET', '/api/library/jobs'),
  playback: (id: string, patch: PlaybackPatch) =>
    call<Media>('PATCH', `/api/library/${encodeURIComponent(id)}/playback`, patch),
  deleteMedia: (id: string) => call<unknown>('DELETE', `/api/library/${encodeURIComponent(id)}`),
  retry: (id: string) => call<unknown>('POST', `/api/library/${encodeURIComponent(id)}/retry`),
  searchMovies: (query: string) => call<MovieResult[]>('POST', '/api/library/search', { query }),
  probe: (items: { hash: string; magnet: string; seeders: number }[]) =>
    call<unknown>('POST', '/api/library/probe', { items }),
  probeStatus: (hashes: string[]) =>
    call<Record<string, ProbeState>>('GET', `/api/library/probe/status?hashes=${hashes.join(',')}`),
  download: (body: {
    title: string;
    year: number | null;
    magnet: string;
    tmdb_id: number | null;
    imdb_id: string | null;
    poster_url: string | null;
    overview: string | null;
  }) => call<{ id: string }>('POST', '/api/library/download', body),
  searchSeries: (query: string) => call<ShowResult[]>('POST', '/api/series/search', { query }),
  addSeries: (tmdbId: number) => call<Media>('POST', '/api/series', { tmdb_id: tmdbId }),
  season: (showId: string, season: number) =>
    call<SeasonView>('GET', `/api/series/${encodeURIComponent(showId)}/season/${season}`),
  downloadSeries: (showId: string, scope: 'episode' | 'season' | 'series', season?: number, episode?: number) =>
    call<unknown>('POST', `/api/series/${encodeURIComponent(showId)}/download`, { scope, season, episode }),
  deleteSeason: (showId: string, season: number) =>
    call<unknown>('DELETE', `/api/series/${encodeURIComponent(showId)}/season/${season}`),
  recommend: (criteria: Record<string, string>, keywords: string, kind: 'movie' | 'series') =>
    call<Recommendation[]>('POST', '/api/advisor/recommend', { criteria, keywords, kind }),
  forget: (r: { id: string; title: string; year: number | null }) =>
    call<unknown>('POST', '/api/advisor/forget', r),
};

/** Remote key learning (the phone asks, the TV reports the next key press). */
export const learn = {
  pending: () => call<{ action: string | null }>('GET', '/api/remote/learn'),
  offer: (key: string) => call<{ accepted: boolean }>('POST', '/api/remote/learn', { key }),
};

export const posterUrl = (id: string) => `/api/posters/${encodeURIComponent(id)}`;
export const mediaUrl = (file: string) => `/media/${encodeURIComponent(file)}`;
