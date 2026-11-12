/**
 * Retro UI sounds, synthesized with WebAudio (no files): a soft "tick" per
 * element appearing on screen, and a "beep" on clicks. The AudioContext can
 * only start after a user gesture: it is woken on the first click or key.
 */

let ctx: AudioContext | null = null;
let master: GainNode | null = null;

export function wakeAudio(): void {
  if (!ctx) {
    ctx = new AudioContext();
    master = ctx.createGain();
    master.gain.value = 0.5;
    master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume().catch(() => {});
}

export function blip(kind: 'click' | 'tick'): void {
  if (!ctx || !master || ctx.state !== 'running') return;
  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  const click = kind === 'click';
  osc.type = click ? 'square' : 'sine';
  osc.frequency.value = click ? 1180 : 720;
  gain.gain.setValueAtTime(click ? 0.06 : 0.025, now);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + (click ? 0.05 : 0.03));
  osc.connect(gain).connect(master);
  osc.start(now);
  osc.stop(now + 0.06);
}

/**
 * Staggered "loading" reveal of a screen's elements (v1 RetroFx): each element
 * pops in after the previous one, with a tick every other element.
 */
export const REVEAL = '[data-reveal], .detail > *';

export function reveal(root: HTMLElement | null | undefined, selector = REVEAL, max = 26): void {
  if (!root) return; // the screen may have closed meanwhile
  const items = [...root.querySelectorAll<HTMLElement>(selector)].slice(0, max);
  items.forEach((el, i) => {
    const delay = i * 32;
    el.animate([{ opacity: 0 }, { opacity: 1 }], {
      duration: 80,
      delay,
      easing: 'steps(1, start)',
      fill: 'backwards',
    });
    setTimeout(() => blip('tick'), delay); // one tick per element, as v1
  });
}

/**
 * A/V sync test beep: schedules a short 1 kHz beep and returns in how many ms
 * the browser will actually output it (its own audio latency included), so
 * the flash can be shown at that moment. Only the system/TV lag remains,
 * which the A/V offset setting compensates. Null when audio is not running.
 */
export function syncBeep(): number | null {
  wakeAudio();
  if (!ctx || ctx.state !== 'running') return null;
  const lead = 0.1;
  const at = ctx.currentTime + lead;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.frequency.value = 1000;
  gain.gain.setValueAtTime(0, at);
  gain.gain.linearRampToValueAtTime(0.5, at + 0.003);
  gain.gain.setValueAtTime(0.5, at + 0.08);
  gain.gain.linearRampToValueAtTime(0, at + 0.085);
  osc.connect(gain).connect(ctx.destination);
  osc.start(at);
  osc.stop(at + 0.1);
  return (lead + (ctx.baseLatency || 0) + (ctx.outputLatency || 0)) * 1000;
}

/** What counts as clickable for the hover tick. */
const CLICKABLE = 'button:not(:disabled), a[href], [role="button"], select, label';
let hovered: Element | null = null;

/**
 * The reveal "tick" when the pointer enters a clickable element (once per
 * element, not again while moving inside it). Listen on pointerover.
 */
export function hoverTick(event: PointerEvent): void {
  if (event.pointerType === 'touch') return;
  const el = (event.target as Element | null)?.closest?.(CLICKABLE) ?? null;
  if (el === hovered) return;
  hovered = el;
  if (el) blip('tick');
}
