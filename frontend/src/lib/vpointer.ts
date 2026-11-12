/**
 * Virtual mouse, driven by the phone remote's touchpad (movies mode).
 *
 * The page cannot move the system cursor, so it plays the mouse itself: it
 * keeps a position, fires the mouse/pointer events the UI listens to (the
 * retro cursor follows `mousemove`), and clicks what is under it. CSS
 * `:hover` cannot be triggered from script: every `:hover` rule is copied
 * once as a `.v-hover` rule, and that class is put on the hovered elements.
 * Works the same under X11, cage/Wayland and on a dev Mac (no system tool).
 */

const HOVER = 'v-hover';
let x = typeof window === 'undefined' ? 0 : window.innerWidth / 2;
let y = typeof window === 'undefined' ? 0 : window.innerHeight / 2;
/** Hovered element and its ancestors (innermost first). */
let chain: Element[] = [];
const patched = new WeakSet<CSSStyleSheet>();

if (typeof window !== 'undefined') {
  // The real mouse (air mouse) moved: start from there, and let real :hover work.
  window.addEventListener(
    'mousemove',
    (e) => {
      if (!e.isTrusted) return;
      x = e.clientX;
      y = e.clientY;
      setHover([]);
    },
    { capture: true, passive: true },
  );
}

/**
 * Finger movement on the phone pad (phone pixels) → cursor movement, with a
 * little acceleration: slow moves are precise, fast swipes cross the screen.
 */
export function pointerGain(d: number, screen: number): number {
  const base = screen / 400; // a 400 px swipe crosses the screen at slow speed
  const speedUp = Math.min(2.5, 1 + Math.abs(d) / 12);
  return d * base * speedUp * 0.5;
}

export function movePointer(dx: number, dy: number): void {
  x = clamp(x + pointerGain(dx, window.innerWidth), 0, window.innerWidth - 1);
  y = clamp(y + pointerGain(dy, window.innerHeight), 0, window.innerHeight - 1);
  const target = document.elementFromPoint(x, y);
  setHover(target ? ancestors(target) : []);
  fire(target ?? document.body, 'pointermove', true);
  fire(target ?? document.body, 'mousemove', true);
}

export function clickPointer(): void {
  const target = document.elementFromPoint(x, y);
  if (!target) return;
  for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup'] as const) fire(target, type, true);
  const field = target.closest<HTMLElement>('input, textarea, select, [tabindex]');
  field?.focus();
  fire(target, 'click', true);
}

/** Scrolls the scrollable box under the cursor (two-finger drag on the pad). */
export function scrollPointer(dy: number): void {
  let node = document.elementFromPoint(x, y);
  while (node && node !== document.documentElement) {
    const el = node as HTMLElement;
    const style = getComputedStyle(el);
    if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 1) {
      el.scrollBy({ top: dy * 2 });
      return;
    }
    if (/(auto|scroll)/.test(style.overflowX) && el.scrollWidth > el.clientWidth + 1) {
      el.scrollBy({ left: dy * 2 });
      return;
    }
    node = node.parentElement;
  }
}

function fire(target: Element, type: string, bubbles: boolean): void {
  const init = { bubbles, cancelable: true, composed: true, clientX: x, clientY: y, button: 0, view: window };
  const event = type.startsWith('pointer')
    ? new PointerEvent(type, { ...init, pointerType: 'mouse', isPrimary: true, pointerId: 1 })
    : new MouseEvent(type, init);
  target.dispatchEvent(event);
}

function ancestors(el: Element): Element[] {
  const out: Element[] = [];
  for (let n: Element | null = el; n; n = n.parentElement) out.push(n);
  return out;
}

/** Moves the emulated hover to `next`, with the enter/leave/over/out events. */
function setHover(next: Element[]): void {
  if (next[0] === chain[0]) return;
  patchHoverRules();
  const kept = new Set(next.filter((el) => chain.includes(el)));
  if (chain[0]) {
    fire(chain[0], 'pointerout', true);
    fire(chain[0], 'mouseout', true);
  }
  for (const el of chain) {
    if (kept.has(el)) continue;
    el.classList.remove(HOVER);
    fire(el, 'pointerleave', false);
    fire(el, 'mouseleave', false);
  }
  if (next[0]) {
    fire(next[0], 'pointerover', true);
    fire(next[0], 'mouseover', true);
  }
  for (const el of [...next].reverse()) {
    if (kept.has(el)) continue;
    el.classList.add(HOVER);
    fire(el, 'pointerenter', false);
    fire(el, 'mouseenter', false);
  }
  chain = next;
}

/** Copies every `:hover` rule of the page's style sheets as a `.v-hover` rule. */
function patchHoverRules(): void {
  for (const sheet of Array.from(document.styleSheets)) {
    if (patched.has(sheet)) continue;
    patched.add(sheet);
    try {
      patchRules(sheet, sheet.cssRules);
    } catch {
      // cross-origin sheet: not ours, nothing to copy
    }
  }
}

function patchRules(owner: CSSStyleSheet | CSSGroupingRule, rules: CSSRuleList): void {
  const copies: string[] = [];
  for (const rule of Array.from(rules)) {
    if (rule instanceof CSSStyleRule && rule.selectorText.includes(':hover')) {
      copies.push(`${hoverSelector(rule.selectorText)} { ${rule.style.cssText} }`);
    } else if (rule instanceof CSSGroupingRule) {
      patchRules(rule, rule.cssRules);
    }
  }
  for (const css of copies) {
    try {
      owner.insertRule(css, owner.cssRules.length);
    } catch {
      // a selector the engine rejects once rewritten: skip it
    }
  }
}

export function hoverSelector(selector: string): string {
  return selector.replaceAll(':hover', `.${HOVER}`);
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}
