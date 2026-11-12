import { describe, expect, it } from 'vitest';
import { ACTION_GROUPS, avOffsetText, duration, keyLabel, playlistId } from './helpers';

describe('playlistId', () => {
  it('extracts the id from YouTube links', () => {
    expect(playlistId('https://www.youtube.com/playlist?list=PLabc_12-x')).toBe('PLabc_12-x');
    expect(playlistId('https://youtube.com/watch?v=dQw4&list=PLzz&index=3')).toBe('PLzz');
    expect(playlistId('https://youtu.be/dQw4?list=PLyy&si=x')).toBe('PLyy');
  });
  it('keeps a bare id', () => {
    expect(playlistId('  PLbare ')).toBe('PLbare');
  });
});

describe('labels', () => {
  it('names special keys', () => {
    expect(keyLabel('ArrowUp')).toBe('↑');
    expect(keyLabel(' ')).toBe('Espace');
    expect(keyLabel('é')).toBe('É');
    expect(keyLabel('F7')).toBe('F7');
  });
  it('covers every remote action once', () => {
    const ids = ACTION_GROUPS.flatMap((g) => g.actions.map((a) => a.id));
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toHaveLength(22);
  });
  it('formats durations and offsets', () => {
    expect(duration(45)).toBe('45 s');
    expect(duration(120)).toBe('2 min');
    expect(duration(150)).toBe('2 min 30 s');
    expect(avOffsetText(0)).toContain('synchronisés');
    expect(avOffsetText(-120)).toBe('Le son est avancé de 120 ms.');
  });
});
