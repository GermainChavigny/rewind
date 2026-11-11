import { describe, expect, it } from 'vitest';
import type { Media } from './api';
import { episodeCode, formatTime, isWatched, library, statusInfo } from './library.svelte';

function media(fields: Partial<Media>): Media {
  return {
    id: 'x', kind: 'movie', parent_id: null, title: 'X', year: null, season: null, episode: null,
    status: 'ready', file: 'x.mp4', duration: 0, position: 0, watched: false,
    last_played_at: null, added_at: 0, ...fields,
  }; // prettier-ignore
}

describe('library rules', () => {
  it('formats times like v1', () => {
    expect(formatTime(5400)).toBe('01:30:00');
    expect(formatTime(2820)).toBe('47:00');
    expect(episodeCode(2, 3)).toBe('S02E03');
  });

  it('counts a movie as watched at 92 %', () => {
    expect(isWatched(media({ duration: 100, position: 91 }))).toBe(false);
    expect(isWatched(media({ duration: 100, position: 92 }))).toBe(true);
    expect(isWatched(media({ watched: true }))).toBe(true);
  });

  it('labels unfinished items', () => {
    expect(statusInfo({ status: 'downloading', progress: { download: 0.42 } }).label).toBe('DL 42%');
    const conv = statusInfo({ status: 'transcoding', progress: { transcode: 0.5 } });
    expect(conv.phase).toBe('convert');
    expect(conv.ratio).toBe(0.5);
  });

  it('orders movies: downloads, played (recent first), new (recent first), errors', () => {
    library.items = [
      media({ id: 'new-old', added_at: 1 }),
      media({ id: 'error', status: 'error', added_at: 9 }),
      media({ id: 'played-old', last_played_at: 10, added_at: 2 }),
      media({ id: 'dl', status: 'downloading', added_at: 3 }),
      media({ id: 'new-recent', added_at: 8 }),
      media({ id: 'played-recent', last_played_at: 20, added_at: 4 }),
      media({ id: 'show', kind: 'series' }),
    ];
    expect(library.movies.map((m) => m.id)).toEqual([
      'dl', 'played-recent', 'played-old', 'new-recent', 'new-old', 'error',
    ]); // prettier-ignore
  });

  it('finds the next ready episode across seasons', () => {
    library.items = [
      media({ id: 's1e1', kind: 'episode', parent_id: 'show', season: 1, episode: 1 }),
      media({ id: 's1e3', kind: 'episode', parent_id: 'show', season: 1, episode: 3 }),
      media({ id: 's2e1', kind: 'episode', parent_id: 'show', season: 2, episode: 1 }),
      media({ id: 's1e2', kind: 'episode', parent_id: 'show', season: 1, episode: 2, status: 'downloading' }),
    ];
    expect(library.nextReadyEpisode('show', 1, 1)?.id).toBe('s1e3');
    expect(library.nextReadyEpisode('show', 1, 3)?.id).toBe('s2e1');
    expect(library.nextReadyEpisode('show', 2, 1)).toBeNull();
  });
});
