/**
 * Library store: the catalog, the running jobs (polled while something
 * downloads) and the v1 ordering rules.
 *
 * Movie list order (v1): downloads in progress → already played (most
 * recently played first) → never played (most recently added first) → errors.
 */

import { api, type Job, type LibraryFeatures, type Media } from './api';
import { t } from './i18n';
import { announce } from './voice';

export const WATCHED_THRESHOLD = 0.92;
const POLL_MS = 1500;
const ACTIVE = new Set(['queued', 'downloading', 'fetching-subs', 'transcoding']);

export const isActive = (m: { status: string }) => ACTIVE.has(m.status);
export const isReady = (m: { status: string }) => m.status === 'ready';

export function isWatched(m: Media): boolean {
  return m.watched || (m.duration > 0 && m.position >= WATCHED_THRESHOLD * m.duration);
}

export function playedRatio(m: Media): number {
  return m.duration ? Math.max(0, Math.min(1, m.position / m.duration)) : 0;
}

export const pad2 = (n: number | null) => String(n ?? 0).padStart(2, '0');
export const episodeCode = (season: number | null, episode: number | null) =>
  `S${pad2(season)}E${pad2(episode)}`;

/** 5400 → "01:30:00"; 2820 → "47:00". */
export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.round(seconds || 0));
  const h = Math.floor(s / 3600);
  const mm = pad2(Math.floor((s % 3600) / 60));
  const ss = pad2(s % 60);
  return h ? `${pad2(h)}:${mm}:${ss}` : `${mm}:${ss}`;
}

/**
 * "Watched / length" without seconds, short enough for one line of the side
 * panel: "0h12 / 1h30", or "12 / 47 min" for anything under an hour.
 */
export function formatProgress(position: number, duration: number): string {
  const min = (s: number) => Math.floor(Math.max(0, s || 0) / 60);
  const hm = (s: number) => `${Math.floor(min(s) / 60)}h${pad2(min(s) % 60)}`;
  return duration >= 3600 ? `${hm(position)} / ${hm(duration)}` : `${min(position)} / ${min(duration)} min`;
}

/** Status label and progress of an unfinished item (a library row or a job). */
export function statusInfo(m: { status: string; progress?: Job['progress']; error?: string | null }): {
  label: string;
  full: string;
  ratio: number;
  phase: 'download' | 'convert' | null;
} {
  const p = m.progress ?? {};
  const pct = (r = 0) => `${Math.round(r * 100)}%`;
  switch (m.status) {
    case 'queued':
      return { label: t('lib.queued'), full: t('lib.queued'), ratio: 0, phase: null };
    case 'downloading':
      return { label: `DL ${pct(p.download)}`, full: t('lib.downloading', { pct: pct(p.download) }),
               ratio: p.download ?? 0, phase: 'download' }; // prettier-ignore
    case 'fetching-subs':
      return { label: t('lib.subtitles'), full: t('lib.subtitles'), ratio: 1, phase: 'convert' };
    case 'transcoding':
      return { label: `CONV. ${pct(p.transcode)}`, full: t('lib.converting', { pct: pct(p.transcode) }),
               ratio: p.transcode ?? 0, phase: 'convert' }; // prettier-ignore
    case 'error':
      return { label: t('lib.error'), full: `${t('lib.error')} : ${m.error ?? ''}`, ratio: 0, phase: null };
    default:
      return { label: '', full: '', ratio: 0, phase: null };
  }
}

class Library {
  items = $state<Media[]>([]);
  jobs = $state<Record<string, Job>>({});
  features = $state<LibraryFeatures>({ search: false, series: false, advisor: false });
  freeBytes = $state<number | null>(null);

  private polling: ReturnType<typeof setInterval> | null = null;
  private jobIds = '';
  /** Deleted by the user: their disappearance is not "movie ready". */
  private ignored = new Set<string>();

  async init(): Promise<void> {
    this.features = await api.libraryFeatures().catch(() => this.features);
    await this.load();
    this.watchJobs(); // show downloads resumed after a reboot
  }

  async load(): Promise<void> {
    const [items, disk] = await Promise.all([api.library(), api.disk().catch(() => null)]);
    this.items = items;
    if (disk) this.freeBytes = disk.free_bytes;
  }

  get(id: string | null | undefined): Media | null {
    return (id && this.items.find((m) => m.id === id)) || null;
  }

  /** Movies, in the v1 order. */
  get movies(): Media[] {
    const rank = (m: Media) =>
      isActive(m) ? 0 : m.status === 'error' ? 3 : m.last_played_at || m.position > 0 ? 1 : 2;
    return this.items
      .filter((m) => m.kind === 'movie')
      .sort((a, b) => {
        const ra = rank(a);
        const rb = rank(b);
        if (ra !== rb) return ra - rb;
        if (ra === 1) return (b.last_played_at || b.added_at) - (a.last_played_at || a.added_at);
        return b.added_at - a.added_at;
      });
  }

  get shows(): Media[] {
    return this.items.filter((m) => m.kind === 'series').sort((a, b) => b.added_at - a.added_at);
  }

  /** Ready episodes of a show, in order. */
  readyEpisodes(showId: string): Media[] {
    return this.items
      .filter((m) => m.kind === 'episode' && m.parent_id === showId && isReady(m))
      .sort((a, b) => (a.season! - b.season!) || (a.episode! - b.episode!)); // prettier-ignore
  }

  totalEpisodes(show: Media): number {
    return (show.seasons ?? []).reduce((n, s) => n + (s.episode_count || 0), 0);
  }

  lastPlayedEpisode(showId: string, watchedOnly = false): Media | null {
    let best: Media | null = null;
    for (const e of this.readyEpisodes(showId)) {
      if (!e.last_played_at || (watchedOnly && !isWatched(e))) continue;
      if (!best || e.last_played_at > best.last_played_at!) best = e;
    }
    return best;
  }

  nextReadyEpisode(showId: string, season: number, episode: number): Media | null {
    return (
      this.readyEpisodes(showId).find(
        (e) => e.season! > season || (e.season === season && e.episode! > episode),
      ) ?? null
    );
  }

  /** Local copy of a playback change (the backend has it already). */
  patchLocal(id: string, fields: Partial<Media>): void {
    const item = this.items.find((m) => m.id === id);
    if (item) Object.assign(item, fields);
  }

  async remove(item: Media): Promise<void> {
    this.ignored.add(item.id);
    for (const child of this.items.filter((m) => m.parent_id === item.id)) this.ignored.add(child.id);
    await api.deleteMedia(item.id).catch(() => {});
    await this.load();
  }

  /** Poll the jobs while some exist; reload the catalog when the set of jobs changes. */
  watchJobs(): void {
    if (this.polling) return;
    const tick = async () => {
      let jobs: Record<string, Job>;
      try {
        jobs = await api.jobs();
      } catch {
        return;
      }
      const active = Object.fromEntries(Object.entries(jobs).filter(([, j]) => j.status !== 'error'));
      for (const [id, job] of Object.entries(this.jobs)) {
        if (jobs[id] || this.ignored.has(id) || job.status === 'error') continue;
        // A known job vanished: it is ready. Series jobs stay silent (a pack = many episodes).
        if (job.kind === 'movie') announce(t('lib.voice_ready'));
      }
      for (const id of this.ignored) if (!jobs[id]) this.ignored.delete(id);
      this.jobs = jobs;
      for (const [id, job] of Object.entries(jobs)) this.patchLocal(id, { status: job.status, progress: job.progress, error: job.error });
      const ids = Object.keys(jobs).sort().join(',');
      if (ids !== this.jobIds) {
        this.jobIds = ids;
        await this.load();
      }
      if (!Object.keys(active).length) this.stopWatching();
    };
    void tick();
    this.polling = setInterval(() => void tick(), POLL_MS);
  }

  private stopWatching(): void {
    if (this.polling) clearInterval(this.polling);
    this.polling = null;
  }
}

export const library = new Library();
