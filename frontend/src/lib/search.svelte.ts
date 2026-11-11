/**
 * Search results (movies: indexer releases enriched by TMDB; series: TMDB
 * shows) and the magnet reachability probe (…/✓/✗) of the movie results.
 */

import { api, ApiError, type MovieResult, type ProbeState, type ShowResult } from './api';
import { t } from './i18n';

export type SearchKind = 'movie' | 'series';

export const SORTS = ['seeders', 'size', 'title', 'relevance'] as const;
export type Sort = (typeof SORTS)[number];

class Search {
  kind = $state<SearchKind>('movie');
  query = $state('');
  message = $state<string | null>(null);
  movies = $state<(MovieResult & { rank: number })[]>([]);
  shows = $state<ShowResult[]>([]);
  sort = $state<Sort>('seeders');
  probe = $state<Record<string, ProbeState>>({});
  private seq = 0;
  private probeTimer: ReturnType<typeof setInterval> | null = null;

  get sortedMovies(): MovieResult[] {
    const list = [...this.movies];
    switch (this.sort) {
      case 'seeders':
        return list.sort((a, b) => b.torrent.seeders - a.torrent.seeders);
      case 'size':
        return list.sort((a, b) => (b.torrent.size ?? 0) - (a.torrent.size ?? 0));
      case 'title':
        return list.sort((a, b) => a.title.localeCompare(b.title, 'fr', { sensitivity: 'base' }));
      default:
        return list.sort((a, b) => a.rank - b.rank);
    }
  }

  cycleSort(): void {
    this.sort = SORTS[(SORTS.indexOf(this.sort) + 1) % SORTS.length];
  }

  async run(query: string, kind: SearchKind = this.kind): Promise<void> {
    const seq = ++this.seq;
    this.kind = kind;
    this.query = query;
    this.movies = [];
    this.shows = [];
    this.stopProbing();
    this.message = t(kind === 'series' ? 'search.searching_series' : 'search.searching', { query });
    try {
      if (kind === 'series') {
        const shows = await api.searchSeries(query);
        if (seq !== this.seq) return;
        this.shows = shows;
      } else {
        const movies = await api.searchMovies(query);
        if (seq !== this.seq) return;
        this.movies = movies.map((m, rank) => ({ ...m, rank }));
        this.startProbing();
      }
      const empty = kind === 'series' ? !this.shows.length : !this.movies.length;
      this.message = empty ? t('search.none', { query }) : null;
    } catch (err) {
      if (seq !== this.seq) return;
      this.message =
        err instanceof ApiError && err.status === 503 ? t('search.not_configured') : t('search.error');
    }
  }

  toggleKind(): void {
    this.kind = this.kind === 'series' ? 'movie' : 'series';
    if (this.query) void this.run(this.query, this.kind);
  }

  /** Probe the best magnets, most seeded first (the backend works in that order). */
  private startProbing(): void {
    const items = this.movies
      .filter((m) => m.torrent.hash)
      .map((m) => ({ hash: m.torrent.hash!, magnet: m.torrent.magnet, seeders: m.torrent.seeders }))
      .sort((a, b) => b.seeders - a.seeders);
    if (!items.length) return;
    void api.probe(items).catch(() => {});
    const hashes = items.map((i) => i.hash);
    const poll = async () => {
      const states = await api.probeStatus(hashes).catch(() => null);
      if (!states) return;
      this.probe = { ...this.probe, ...states };
      if (hashes.every((h) => states[h] === 'reachable' || states[h] === 'unreachable')) this.stopProbing();
    };
    void poll();
    this.probeTimer = setInterval(() => void poll(), 1500);
  }

  stopProbing(): void {
    if (this.probeTimer) clearInterval(this.probeTimer);
    this.probeTimer = null;
  }
}

export const search = new Search();
