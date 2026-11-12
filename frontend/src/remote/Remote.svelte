<!--
  Virtual remote (/remote/, opened from the phone admin): an early-90s
  hi-fi remote (charcoal plastic, matte rubber keys, silkscreened captions)
  drawn with the same hard bevels as the admin's 90s desktop. Its buttons
  send the configured actions to the TV, like the physical one. Channel
  keys carry their number, the channel name is printed under them inside a
  coloured frame.
  It follows the TV (`/api/remote/events`): in the movies it only keeps the
  useful keys and adds a touchpad that moves the TV's cursor, and a key to
  leave the movies. When the TV waits for text (search, advisor keywords),
  a field opens the phone's own keyboard and types into the TV.
  "Rearrange" mode: drag a button onto another cell to match your own
  remote (the button there swaps places); each mode's layout is saved on the TV.
  Everything fits the screen height, no scrolling.
-->
<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Brand from '../components/Brand.svelte';
  import Glyph from '../components/Glyph.svelte';
  import {
    actionsFor,
    CHANNEL_INKS,
    defaultLayout,
    type Layout,
    lookOf,
    LOOKS,
    type Mode,
    moveTo,
    sanitize,
  } from './layout';

  interface TvState {
    listening: boolean;
    mode: Mode;
    keyboard: { text: string; purpose: 'movie' | 'series' | 'advisor' } | null;
  }

  /** Every key the TV offers: keymap actions + home / computer power. */
  let available = $state<string[]>([]);
  /** Channel number → its name, printed under the 1–9 keys. */
  let channels = $state<Record<number, { name: string }>>({});
  let layouts = $state<Record<Mode, Layout> | null>(null);
  let mode = $state<Mode>('tv');
  let keyboard = $state<TvState['keyboard']>(null);
  let editing = $state(false);
  let confirmOff = $state(false);
  let led = $state(false);
  let toast = $state('');
  let pressed = $state<string | null>(null);
  let drag = $state<{ action: string; x: number; y: number; over: number | null } | null>(null);
  let toastTimer: ReturnType<typeof setTimeout> | undefined;
  let events: EventSource | null = null;

  const actions = $derived(actionsFor(mode, available));
  const layout = $derived(layouts?.[mode] ?? null);
  const byCell = $derived(
    layout ? Object.fromEntries(Object.entries(layout.cells).map(([a, i]) => [i, a])) : {},
  );

  onMount(async () => {
    try {
      const data = await (await fetch('/api/remote/layout')).json();
      available = [...data.actions, ...data.extra].filter((a: string) => a in LOOKS);
      layouts = {
        tv: sanitize(data.layouts.tv, actionsFor('tv', available), 'tv'),
        movies: sanitize(data.layouts.movies, actionsFor('movies', available), 'movies'),
      };
      const list = await (await fetch('/api/channels')).json();
      channels = Object.fromEntries(list.map((c: { number: number; name: string }) => [c.number, c]));
    } catch {
      say('La télé ne répond pas.');
    }
    follow();
  });

  onDestroy(() => events?.close());

  /** Follows what the TV shows (EventSource reconnects by itself). */
  function follow() {
    events = new EventSource('/api/remote/events');
    events.onmessage = (message) => {
      let event: { type: string; message?: string } & Partial<TvState>;
      try {
        event = JSON.parse(message.data);
      } catch {
        return;
      }
      if (event.type === 'state') {
        setMode(event.mode ?? 'tv');
        keyboard = event.keyboard ?? null;
        if (keyboard && document.activeElement !== field) typed = keyboard.text;
      } else if (event.type === 'error' && event.message === 'shutdown_failed') {
        say("L'ordinateur a refusé de s'éteindre.");
      }
    };
  }

  /** The TV changed mode: switch layouts (and leave the rearranging). */
  function setMode(next: Mode) {
    if (next === mode) return;
    if (editing) {
      void save();
      editing = false;
    }
    drag = null;
    mode = next;
  }

  function say(text: string) {
    toast = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 2800);
  }

  function blink() {
    navigator.vibrate?.(12);
    led = true;
    setTimeout(() => (led = false), 140);
  }

  async function post(path: string, body?: unknown): Promise<boolean> {
    try {
      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body ?? {}),
      });
      if (!res.ok) throw new Error(String(res.status));
      const { delivered } = await res.json();
      if (delivered === false) say("La télé n'écoute pas : est-elle allumée sur REWIND ?");
      return true;
    } catch {
      say('La télé ne répond pas.');
      return false;
    }
  }

  function press(action: string) {
    if (editing) return;
    if (action === 'machine_power') {
      confirmOff = true;
      return;
    }
    blink();
    void post('/api/remote/press', { action });
    // Leaving the movies resets the remote at once (the TV confirms it).
    if (action === 'home') {
      setMode('tv');
      keyboard = null;
    }
  }

  async function shutdown() {
    confirmOff = false;
    blink();
    try {
      const res = await fetch('/api/remote/shutdown', { method: 'POST' });
      if (!res.ok) throw new Error(String(res.status));
      say('Fin des émissions… Bonne nuit !');
    } catch {
      say("Impossible d'éteindre l'ordinateur.");
    }
  }

  async function save() {
    if (!layouts) return;
    await fetch(`/api/remote/layout/${mode}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layouts[mode]),
    }).catch(() => say('Disposition non enregistrée.'));
  }

  function toggleEdit() {
    if (editing) void save();
    editing = !editing;
  }

  function reset() {
    if (layouts) layouts[mode] = defaultLayout(actions, mode);
  }

  // --- drag & drop (pointer events: works with fingers and mice) -------------------

  function cellAt(x: number, y: number): number | null {
    const el = document.elementFromPoint(x, y)?.closest<HTMLElement>('[data-cell]');
    return el ? Number(el.dataset.cell) : null;
  }

  function dragStart(e: PointerEvent, action: string) {
    if (!editing) return;
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    drag = { action, x: e.clientX, y: e.clientY, over: null };
  }

  function dragMove(e: PointerEvent) {
    if (!drag) return;
    drag.x = e.clientX;
    drag.y = e.clientY;
    drag.over = cellAt(e.clientX, e.clientY);
  }

  function dragEnd(e: PointerEvent) {
    if (!drag || !layouts) return;
    const cell = cellAt(e.clientX, e.clientY);
    if (cell !== null) layouts[mode] = moveTo(layouts[mode], drag.action, cell);
    drag = null;
  }

  // --- touchpad (movies) -------------------------------------------------------------
  // Finger moves are summed and sent ~30 times a second, one request at a time.

  const TAP_MS = 250;
  const TAP_MOVE = 8;
  const fingers = new Map<number, { x: number; y: number }>();
  let gesture = { start: 0, moved: 0, multi: false };
  let pending = { dx: 0, dy: 0, scroll: 0, click: false };
  let sending = false;
  let flushTimer: ReturnType<typeof setTimeout> | undefined;
  let padActive = $state(false);

  function padDown(e: PointerEvent) {
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    if (fingers.size === 0) gesture = { start: Date.now(), moved: 0, multi: false };
    fingers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (fingers.size > 1) gesture.multi = true;
    padActive = true;
  }

  function padMove(e: PointerEvent) {
    const last = fingers.get(e.pointerId);
    if (!last) return;
    const dx = e.clientX - last.x;
    const dy = e.clientY - last.y;
    fingers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    gesture.moved += Math.abs(dx) + Math.abs(dy);
    if (fingers.size > 1) {
      // Two fingers: scroll, driven by the first finger only.
      if (e.pointerId === fingers.keys().next().value) pending.scroll += -dy;
    } else if (!gesture.multi) {
      pending.dx += dx;
      pending.dy += dy;
    }
    schedule();
  }

  function padUp(e: PointerEvent) {
    if (!fingers.delete(e.pointerId)) return;
    if (fingers.size > 0) return;
    padActive = false;
    if (!gesture.multi && gesture.moved < TAP_MOVE && Date.now() - gesture.start < TAP_MS) click();
  }

  function click() {
    blink();
    pending.click = true;
    schedule();
  }

  function schedule() {
    if (flushTimer === undefined) flushTimer = setTimeout(flush, 33);
  }

  async function flush() {
    flushTimer = undefined;
    if (sending) return schedule();
    const batch = pending;
    if (!batch.dx && !batch.dy && !batch.scroll && !batch.click) return;
    pending = { dx: 0, dy: 0, scroll: 0, click: false };
    sending = true;
    try {
      await fetch('/api/remote/pointer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batch),
      });
    } catch {
      say('La télé ne répond pas.');
    } finally {
      sending = false;
    }
  }

  // --- the phone's keyboard types into the TV ------------------------------------------

  let field = $state<HTMLInputElement | null>(null);
  let typed = $state('');
  let typeTimer: ReturnType<typeof setTimeout> | undefined;

  function onType() {
    clearTimeout(typeTimer);
    typeTimer = setTimeout(() => void post('/api/remote/text', { text: typed }), 90);
  }

  function submitText(e: SubmitEvent) {
    e.preventDefault();
    clearTimeout(typeTimer);
    blink();
    void post('/api/remote/text', { text: typed, submit: true });
    field?.blur();
  }

  const PLACEHOLDERS = { movie: 'Titre du film…', series: 'Titre de la série…', advisor: 'Acteur, thème…' };
</script>

{#snippet face(action: string)}
  {@const look = lookOf(action, mode)}
  {#if look.glyph}<span class="k-glyph"><Glyph name={look.glyph} size="100%" /></span>{/if}
  {#if look.label}<span class="k-label">{look.label}</span>{/if}
{/snippet}

<main class:editing class:movies={mode === 'movies'}>
  <div class="body">
    <div class="ir" aria-hidden="true"><span class="led" class:on={led}></span></div>
    <header>
      <Brand size={22} />
      <button class="mode" onclick={toggleEdit}>{editing ? 'TERMINÉ' : 'RÉORGANISER'}</button>
    </header>

    {#if editing}
      <p class="hint">Glissez une touche sur une autre case. <button class="reset" onclick={reset}>PAR DÉFAUT</button></p>
    {/if}

    {#if keyboard && !editing}
      <form class="typing" onsubmit={submitText}>
        <span class="t-icon"><Glyph name="keyboard" size="100%" /></span>
        <!-- svelte-ignore a11y_autofocus (the TV is waiting for this text) -->
        <input
          bind:this={field}
          bind:value={typed}
          oninput={onType}
          placeholder={PLACEHOLDERS[keyboard.purpose]}
          enterkeyhint={keyboard.purpose === 'advisor' ? 'done' : 'search'}
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          maxlength="80"
          autofocus
        />
        <button class="ok" type="submit">OK</button>
      </form>
    {/if}

    {#if mode === 'movies' && !editing}
      <div class="padzone">
        <span class="silk">Films &amp; séries · pavé tactile</span>
        <div
          class="pad"
          class:active={padActive}
          role="application"
          aria-label="Pavé tactile : glissez pour déplacer le curseur de la télé, touchez pour cliquer"
          onpointerdown={padDown}
          onpointermove={padMove}
          onpointerup={padUp}
          onpointercancel={padUp}
        >
          <span class="pad-hint">glisser · toucher = clic · 2 doigts = défiler</span>
        </div>
        <button class="key click" onclick={click}><span class="k-label">CLIC</span></button>
      </div>
    {/if}

    {#if layout}
      <div class="grid" style:--cols={layout.cols} style:--rows={layout.rows}>
        {#each Array(layout.cols * layout.rows) as _, i (i)}
          {@const action = byCell[i]}
          <div class="cell" data-cell={i} class:over={drag?.over === i}>
            {#if action && LOOKS[action]}
              {@const look = lookOf(action, mode)}
              {@const num = action.startsWith('channel_') ? Number(action.slice(8)) : 0}
              {@const ch = num ? channels[num] : undefined}
              <!-- The printed frame groups the key and its caption, like the silkscreen on a real remote. -->
              <div class="slot" class:framed={!!ch} style:--ink={ch ? CHANNEL_INKS[num - 1] : null}>
                <button
                  class="key {look.tone}"
                  class:down={pressed === action}
                  class:lifted={drag?.action === action}
                  onpointerdown={(e) => (editing ? dragStart(e, action) : (pressed = action))}
                  onpointermove={dragMove}
                  onpointerup={(e) => (editing ? dragEnd(e) : ((pressed = null), press(action)))}
                  onpointercancel={() => ((pressed = null), (drag = null))}
                  onpointerleave={() => !editing && (pressed = null)}
                  aria-label={ch ? `${look.label} ${ch.name}` : look.caption ? `${look.caption} ${look.label}` : look.label}
                >
                  {@render face(action)}
                </button>
                {#if ch}
                  <span class="caption">{ch.name}</span>
                {:else if look.caption}
                  <span class="caption">{look.caption}</span>
                {/if}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if drag && LOOKS[drag.action]}
    <div class="ghost key {lookOf(drag.action, mode).tone}" style:left="{drag.x}px" style:top="{drag.y}px">
      {@render face(drag.action)}
    </div>
  {/if}

  {#if confirmOff}
    <div class="modal" role="presentation" onclick={(e) => e.target === e.currentTarget && (confirmOff = false)}>
      <div class="dialog" role="alertdialog" aria-labelledby="off-title" aria-describedby="off-text">
        <div class="d-title" id="off-title">Éteindre REWIND ?</div>
        <p id="off-text">
          L'ordinateur de la télé va s'éteindre (et la télé avec lui). Pour le rallumer, il faudra appuyer sur son
          bouton.
        </p>
        <div class="d-actions">
          <button class="d-btn" onclick={() => (confirmOff = false)}>Annuler</button>
          <button class="d-btn danger" onclick={shutdown}>Éteindre</button>
        </div>
      </div>
    </div>
  {/if}
  {#if toast}<div class="toast">{toast}</div>{/if}
</main>

<style>
  @font-face {
    font-family: 'Remote Condensed';
    src: url('/fonts/Oswald-Medium.woff2') format('woff2');
  }
  :global(html),
  :global(body) {
    margin: 0;
    height: 100%;
    /* the admin's dithered blue desk, the remote lies on it */
    background-color: #2340c8;
    background-image: radial-gradient(#3354dc 1px, transparent 1.2px);
    background-size: 4px 4px;
    overflow: hidden;
    overscroll-behavior: none;
    -webkit-user-select: none;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  main {
    --silk: #d9d6cc; /* silkscreen print */
    --hi: #5a5a5e;
    --lo: #0c0c0d;
    height: 100dvh;
    display: flex;
    justify-content: center;
    padding: max(10px, env(safe-area-inset-top)) 10px max(10px, env(safe-area-inset-bottom));
    box-sizing: border-box;
    font-family: 'Remote Condensed', 'Arial Narrow', sans-serif;
    touch-action: manipulation;
  }
  main.editing {
    touch-action: none;
  }
  /* The plastic body: matte charcoal, square shoulders, a hard 1px bevel. */
  .body {
    position: relative;
    width: 100%;
    max-width: 420px;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 14px 16px;
    box-sizing: border-box;
    border: 2px solid #000;
    border-radius: 10px 10px 22px 22px;
    background-color: #29292c;
    /* faint vertical grain, like the textured plastic */
    background-image: repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.025) 0 1px, transparent 1px 3px);
    box-shadow:
      inset 2px 2px 0 #46464b,
      inset -2px -2px 0 #141416,
      6px 6px 0 rgba(0, 0, 0, 0.45);
  }
  /* Infrared window across the top edge, the LED glows behind it. */
  .ir {
    height: 16px;
    margin: 0 -14px;
    border-bottom: 2px solid #000;
    border-radius: 8px 8px 0 0;
    background: linear-gradient(#3a0c10, #1c0507);
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .led {
    width: 28px;
    height: 5px;
    background: #4a1014;
  }
  .led.on {
    background: #ff3b30;
    box-shadow: 0 0 12px 3px #ff3b30;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 4px 0 6px;
    border-bottom: 1px solid #47474c;
  }
  header :global(.brand) {
    --brand-tag: var(--silk);
  }
  /* Header buttons: the admin's grey bevelled push buttons. */
  .mode,
  .reset {
    font: 15px/1 'Remote Condensed', sans-serif;
    letter-spacing: 0.04em;
    color: #000;
    min-height: 34px;
    padding: 6px 12px;
    background: #c3c3bb;
    border: 2px solid #000;
    border-radius: 3px;
    box-shadow:
      inset 2px 2px 0 #fff,
      inset -2px -2px 0 #6e6e66;
  }
  .mode:active,
  .reset:active {
    box-shadow:
      inset 2px 2px 0 #6e6e66,
      inset -2px -2px 0 #fff;
  }
  .hint {
    margin: 0;
    padding: 6px 8px;
    color: #000;
    background: #ecebb4;
    border: 2px solid #000;
    font: 13px/1.3 Verdana, Geneva, sans-serif;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .grid {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(var(--cols), 1fr);
    grid-template-rows: repeat(var(--rows), 1fr);
    gap: 9px 10px;
  }
  .cell {
    min-height: 0;
    display: flex;
    border-radius: 5px;
  }
  /* A key and its caption printed under it. */
  .slot {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  /* Channel keys: a coloured frame printed around the key and the channel name. */
  .slot.framed {
    padding: 3px 3px 2px;
    border: 1.5px solid var(--ink);
    border-radius: 6px;
  }
  .caption {
    flex: 0 0 auto;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
    text-align: center;
    font-size: clamp(9px, 1.45dvh, 12px);
    /* room above the capitals: overflow would clip the accents (TÉLÉ) */
    line-height: 1.3;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--silk);
    opacity: 0.85;
  }
  .framed .caption {
    color: var(--ink);
    opacity: 1;
  }
  .editing .cell {
    outline: 1px dashed #6a6a70;
  }
  .cell.over {
    outline: 2px solid #f3ec3a;
  }
  /* Matte rubber keys: flat colour, hard bevel, a dark socket around them. */
  .key {
    --cap: #4a4a4f;
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 0;
    border: 1px solid #000;
    border-radius: 5px;
    color: #f0eee6;
    font-family: inherit;
    cursor: pointer;
    background: var(--cap);
    box-shadow:
      inset 1px 1px 0 rgba(255, 255, 255, 0.28),
      inset -1px -2px 0 rgba(0, 0, 0, 0.45),
      0 0 0 2px #151517,
      0 3px 0 2px #0b0b0c;
    transition: transform 0.05s;
  }
  .key.down {
    transform: translateY(2px);
    box-shadow:
      inset 1px 1px 0 rgba(0, 0, 0, 0.45),
      inset -1px -1px 0 rgba(255, 255, 255, 0.12),
      0 0 0 2px #151517,
      0 1px 0 2px #0b0b0c;
    filter: brightness(0.9);
  }
  .editing .key {
    cursor: grab;
    animation: wiggle 0.5s ease-in-out infinite alternate;
  }
  .key.lifted {
    opacity: 0.25;
  }
  @keyframes wiggle {
    from {
      transform: rotate(-1.5deg);
    }
    to {
      transform: rotate(1.5deg);
    }
  }
  .k-label {
    font-size: clamp(16px, 4dvh, 28px);
    line-height: 1;
  }
  .k-glyph {
    display: flex;
    width: clamp(16px, 3.4dvh, 26px);
    height: clamp(16px, 3.4dvh, 26px);
  }
  .key.play .k-label {
    font-size: clamp(11px, 2dvh, 15px);
  }
  .key.power {
    --cap: #b5241d;
  }
  .key.number {
    --cap: #3a3a3e;
  }
  .key.play {
    --cap: #4c4f57;
    color: #9cc0ff;
  }
  .key.volume {
    --cap: #57575c;
    color: #ffc352;
  }
  .key.alarm {
    --cap: #3f4a40;
    color: #8be09a;
  }
  .key.alarm .k-label {
    font-size: clamp(13px, 2.5dvh, 19px);
    letter-spacing: 0.05em;
  }
  .key.light {
    --cap: #48445a;
    color: #c9bfff;
  }
  .key.machine {
    --cap: #2c2c30;
    color: #ff6a5f;
  }
  .key.home {
    --cap: #5a4a2a;
    color: #ffd27a;
  }
  /* Movies: the touchpad (a recessed rubber pad) with its click key. */
  .padzone {
    flex: 1 1 0;
    min-height: 130px;
    display: grid;
    grid-template-columns: 1fr 64px;
    grid-template-rows: auto 1fr;
    gap: 4px 10px;
  }
  .silk {
    grid-column: 1 / -1;
    font-size: clamp(9px, 1.45dvh, 12px);
    line-height: 1.3;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--silk);
    opacity: 0.85;
  }
  .pad {
    position: relative;
    min-height: 0;
    border: 1px solid #000;
    border-radius: 8px;
    background-color: #1b1b1d;
    background-image:
      linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
    background-size: 14px 14px;
    box-shadow:
      inset 2px 2px 0 #0b0b0c,
      inset -1px -1px 0 #3c3c40,
      0 0 0 2px #151517;
    touch-action: none;
  }
  .pad.active {
    background-color: #202024;
  }
  .pad-hint {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 8px;
    text-align: center;
    font-size: clamp(9px, 1.4dvh, 12px);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6d6d73;
    pointer-events: none;
  }
  .key.click {
    --cap: #4c4f57;
    color: #9cc0ff;
  }
  .key.click .k-label {
    font-size: clamp(13px, 2.4dvh, 18px);
    letter-spacing: 0.06em;
  }
  main.movies .grid {
    flex: 1.15 1 0;
  }
  /* The TV waits for text: the phone's keyboard types into it. */
  .typing {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    padding: 6px 8px;
    background: #ecebb4;
    border: 2px solid #000;
  }
  .t-icon {
    display: flex;
    width: 22px;
    height: 22px;
    color: #000;
  }
  .typing input {
    flex: 1;
    min-width: 0;
    height: 36px;
    padding: 0 8px;
    font: 17px/1 Verdana, Geneva, sans-serif; /* ≥ 16px: iOS does not zoom */
    color: #000;
    background: #fff;
    border: 2px solid #000;
    border-radius: 0;
    box-shadow: inset 2px 2px 0 #6e6e66;
    -webkit-user-select: text;
    user-select: text;
  }
  .ok {
    font: 15px/1 'Remote Condensed', sans-serif;
    min-height: 36px;
    padding: 6px 12px;
    color: #000;
    background: #c3c3bb;
    border: 2px solid #000;
    box-shadow:
      inset 2px 2px 0 #fff,
      inset -2px -2px 0 #6e6e66;
  }
  /* Confirmation: a 90s dialog box over the remote. */
  .modal {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: rgba(0, 0, 0, 0.55);
  }
  .dialog {
    width: 100%;
    max-width: 340px;
    background: #c3c3bb;
    border: 2px solid #000;
    box-shadow:
      inset 2px 2px 0 #fff,
      inset -2px -2px 0 #6e6e66,
      6px 6px 0 rgba(0, 0, 0, 0.5);
    font: 14px/1.4 Verdana, Geneva, sans-serif;
    color: #000;
  }
  .d-title {
    padding: 6px 10px;
    background: #9b1c16;
    color: #fff;
    font: 16px/1.2 'Remote Condensed', sans-serif;
    letter-spacing: 0.04em;
  }
  .dialog p {
    margin: 12px 12px 4px;
  }
  .d-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 12px;
  }
  .d-btn {
    font: 15px/1 'Remote Condensed', sans-serif;
    min-height: 40px;
    min-width: 96px;
    padding: 8px 14px;
    color: #000;
    background: #c3c3bb;
    border: 2px solid #000;
    box-shadow:
      inset 2px 2px 0 #fff,
      inset -2px -2px 0 #6e6e66;
  }
  .d-btn:active {
    box-shadow:
      inset 2px 2px 0 #6e6e66,
      inset -2px -2px 0 #fff;
  }
  .d-btn.danger {
    color: #fff;
    background: #b5241d;
    box-shadow:
      inset 2px 2px 0 #e0675f,
      inset -2px -2px 0 #6a120e;
  }
  .ghost {
    position: fixed;
    z-index: 10;
    width: 72px;
    height: 56px;
    transform: translate(-50%, -60%) scale(1.15);
    pointer-events: none;
  }
  /* Error message: the admin's yellow note box. */
  .toast {
    position: fixed;
    left: 50%;
    bottom: calc(24px + env(safe-area-inset-bottom));
    transform: translateX(-50%);
    max-width: 90vw;
    padding: 10px 14px;
    background: #f3ec3a;
    color: #000;
    border: 2px solid #000;
    font: 14px/1.35 Verdana, Geneva, sans-serif;
    box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.5);
  }
</style>
