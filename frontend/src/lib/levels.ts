/**
 * Pure helpers for the remote's "analog" settings: volume, darkness, alarm time.
 */

/** Volume steps on the remote (the OSD bar shows one segment per step). */
export const VOLUME_STEPS = 20;

/**
 * Perceptual volume curve. Players take a linear 0–100 gain, but loudness is
 * perceived logarithmically: equal gain steps sound uneven (big jumps at the
 * bottom, nothing at the top). We move along `step` evenly and square it.
 */
export function stepToVolume(step: number): number {
  const s = Math.max(0, Math.min(VOLUME_STEPS, Math.round(step)));
  return Math.round(100 * (s / VOLUME_STEPS) ** 2 * 10) / 10;
}

export function volumeToStep(volume: number): number {
  const v = Math.max(0, Math.min(100, volume));
  return Math.round(Math.sqrt(v / 100) * VOLUME_STEPS);
}

/**
 * Darkness = opacity of the black veil over the whole UI (0 = none, 1 = black).
 * Steps get finer as it gets darker, for precise control at night (as in v1):
 * 5% normally, 2% above 50%, 1% above 80%.
 */
export function darknessStep(current: number): number {
  if (current > 0.8) return 0.01;
  if (current > 0.5) return 0.02;
  return 0.05;
}

export function changeDarkness(current: number, direction: 1 | -1): number {
  const next = current + direction * darknessStep(current);
  return Math.round(Math.max(0, Math.min(1, next)) * 100) / 100;
}

/** "07:50" + 20 → "08:10" (wraps around midnight). */
export function shiftTime(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number);
  const total = (((h * 60 + m + minutes) % 1440) + 1440) % 1440;
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}
