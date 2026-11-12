import { describe, expect, it } from 'vitest';
import { defaultLayout, LOOKS, moveTo, sanitize } from './layout';

const ACTIONS = Object.keys(LOOKS);

describe('virtual remote layout', () => {
  it('places every action on its own cell by default', () => {
    const l = defaultLayout(ACTIONS);
    expect(Object.keys(l.cells).sort()).toEqual([...ACTIONS].sort());
    expect(new Set(Object.values(l.cells)).size).toBe(ACTIONS.length);
    expect(l.cells.tv_power).toBe(0);
    expect(Math.max(...Object.values(l.cells))).toBeLessThan(l.cols * l.rows);
  });

  it('moves to an empty cell, or swaps with the button there', () => {
    const l = defaultLayout(ACTIONS);
    const empty = moveTo(l, 'channel_1', 1);
    expect(empty.cells.channel_1).toBe(1);
    const swapped = moveTo(l, 'channel_1', l.cells.channel_2);
    expect(swapped.cells.channel_1).toBe(l.cells.channel_2);
    expect(swapped.cells.channel_2).toBe(l.cells.channel_1);
  });

  it('repairs a saved layout: unknown actions, clashes, new actions', () => {
    const l = sanitize({ cols: 4, rows: 8, cells: { channel_1: 0, gone: 1, channel_2: 0, next: 99 } }, ACTIONS);
    expect(l.cells.channel_1).toBe(0);
    expect('gone' in l.cells).toBe(false);
    expect(new Set(Object.values(l.cells)).size).toBe(ACTIONS.length);
  });
});
