import { describe, expect, it } from 'vitest';
import { actionsFor, defaultLayout, lookOf, LOOKS, moveTo, sanitize } from './layout';

const AVAILABLE = Object.keys(LOOKS);
const TV = actionsFor('tv', AVAILABLE);
const MOVIES = actionsFor('movies', AVAILABLE);

describe('virtual remote layout', () => {
  it('places every action on its own cell by default', () => {
    for (const [mode, actions] of [['tv', TV], ['movies', MOVIES]] as const) {
      const l = defaultLayout(actions, mode);
      expect(Object.keys(l.cells).sort()).toEqual([...actions].sort());
      expect(new Set(Object.values(l.cells)).size).toBe(actions.length);
      expect(Math.max(...Object.values(l.cells))).toBeLessThan(l.cols * l.rows);
    }
    expect(defaultLayout(TV, 'tv').cells.tv_power).toBe(1);
  });

  it('keeps only the useful keys in the movies, with a key to leave', () => {
    expect(MOVIES).toContain('home');
    expect(MOVIES).toContain('play_pause');
    expect(MOVIES).toContain('machine_power');
    expect(MOVIES).not.toContain('channel_1');
    expect(MOVIES).not.toContain('alarm_toggle');
    expect(TV).not.toContain('home');
    expect(lookOf('alarm_later', 'movies').caption).toBe('Défiler');
    expect(lookOf('alarm_later', 'tv').caption).toBe('Réveil +');
  });

  it('shows the computer power key only when the TV offers it', () => {
    const keymapOnly = AVAILABLE.filter((a) => a !== 'machine_power' && a !== 'home');
    expect(actionsFor('tv', keymapOnly)).not.toContain('machine_power');
    expect(actionsFor('movies', [...keymapOnly, 'home'])).toContain('home');
  });

  it('moves to an empty cell, or swaps with the button there', () => {
    const l = defaultLayout(TV);
    const empty = moveTo(l, 'channel_1', 2);
    expect(empty.cells.channel_1).toBe(2);
    const swapped = moveTo(l, 'channel_1', l.cells.channel_2);
    expect(swapped.cells.channel_1).toBe(l.cells.channel_2);
    expect(swapped.cells.channel_2).toBe(l.cells.channel_1);
  });

  it('repairs a saved layout: unknown actions, clashes, new actions', () => {
    const l = sanitize({ cols: 4, rows: 8, cells: { channel_1: 0, gone: 1, channel_2: 0, next: 99 } }, TV);
    expect(l.cells.channel_1).toBe(0);
    expect('gone' in l.cells).toBe(false);
    expect(new Set(Object.values(l.cells)).size).toBe(TV.length);
  });
});
