import { describe, expect, it } from 'vitest';
import { buildKeyLookup, channelNumber } from './keymap';
import { changeDarkness, shiftTime, stepToVolume, volumeToStep, VOLUME_STEPS } from './levels';
import { computeStage } from './stage';

describe('volume curve', () => {
  it('maps the ends exactly', () => {
    expect(stepToVolume(0)).toBe(0);
    expect(stepToVolume(VOLUME_STEPS)).toBe(100);
  });
  it('is perceptual (half the steps is a quarter of the gain)', () => {
    expect(stepToVolume(VOLUME_STEPS / 2)).toBe(25);
  });
  it('round-trips', () => {
    for (let s = 0; s <= VOLUME_STEPS; s++) expect(volumeToStep(stepToVolume(s))).toBe(s);
  });
});

describe('darkness', () => {
  it('uses finer steps when dark (v1 behaviour)', () => {
    expect(changeDarkness(0, 1)).toBe(0.05);
    expect(changeDarkness(0.6, 1)).toBe(0.62);
    expect(changeDarkness(0.9, 1)).toBe(0.91);
    expect(changeDarkness(0.9, -1)).toBe(0.89);
  });
  it('clamps', () => {
    expect(changeDarkness(1, 1)).toBe(1);
    expect(changeDarkness(0.02, -1)).toBe(0);
  });
});

describe('alarm time', () => {
  it('wraps around midnight', () => {
    expect(shiftTime('23:55', 10)).toBe('00:05');
    expect(shiftTime('00:05', -10)).toBe('23:55');
    expect(shiftTime('07:50', 10)).toBe('08:00');
  });
});

describe('stage', () => {
  it('fills a 720x576 CRT at scale 1', () => {
    expect(computeStage(720, 576)).toEqual({ left: 0, top: 0, width: 720, height: 576, scaleX: 1, scaleY: 1 });
  });
  it('pillarboxes 16:9 to 4:3', () => {
    const g = computeStage(1920, 1080);
    expect([g.left, g.width, g.height]).toEqual([240, 1440, 1080]);
    expect(g.scaleX).toBe(2);
    expect(g.scaleY).toBe(1.875);
  });
});

describe('keymap', () => {
  it('looks up AZERTY and digit keys', () => {
    const lookup = buildKeyLookup({ channel_1: ['&', '1'], tv_power: ['AudioVolumeMute'] });
    expect(lookup.get('&')).toBe('channel_1');
    expect(lookup.get('1')).toBe('channel_1');
    expect(channelNumber('channel_1')).toBe(1);
    expect(channelNumber('tv_power')).toBeNull();
  });
});
