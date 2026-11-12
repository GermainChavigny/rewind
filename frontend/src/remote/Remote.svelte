<!--
  Virtual remote (/remote/, opened from the phone admin): a late-80s remote
  whose buttons send the configured actions to the TV, like the physical
  one. "Arrange" mode: drag a button onto another cell to match your own
  remote (the button there swaps places); the layout is saved on the TV.
  Everything fits the screen height, no scrolling.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import ChannelLogo from '../components/ChannelLogo.svelte';
  import { defaultLayout, type Layout, LOOKS, moveTo, sanitize } from './layout';

  let actions = $state<string[]>([]);
  /** Channel number → its name and logo style, for the 1–9 keys. */
  let channels = $state<Record<number, { name: string; logo_style: number }>>({});
  let layout = $state<Layout | null>(null);
  let editing = $state(false);
  let led = $state(false);
  let toast = $state('');
  let pressed = $state<string | null>(null);
  let drag = $state<{ action: string; x: number; y: number; over: number | null } | null>(null);
  let toastTimer: ReturnType<typeof setTimeout> | undefined;

  const byCell = $derived(
    layout ? Object.fromEntries(Object.entries(layout.cells).map(([a, i]) => [i, a])) : {},
  );

  onMount(async () => {
    try {
      const res = await fetch('/api/remote/layout');
      const data = await res.json();
      actions = data.actions.filter((a: string) => a in LOOKS);
      layout = sanitize(data.layout, actions);
      const list = await (await fetch('/api/channels')).json();
      channels = Object.fromEntries(list.map((c: { number: number; name: string; logo_style: number }) => [c.number, c]));
    } catch {
      say('La télé ne répond pas.');
    }
  });

  function say(text: string) {
    toast = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 2500);
  }

  async function press(action: string) {
    if (editing) return;
    navigator.vibrate?.(12);
    led = true;
    setTimeout(() => (led = false), 140);
    try {
      const res = await fetch('/api/remote/press', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const { delivered } = await res.json();
      if (!delivered) say("La télé n'écoute pas : est-elle allumée sur REWIND v2 ?");
    } catch {
      say('La télé ne répond pas.');
    }
  }

  async function save() {
    if (!layout) return;
    await fetch('/api/remote/layout', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(layout),
    }).catch(() => say("Disposition non enregistrée."));
  }

  function toggleEdit() {
    if (editing) void save();
    editing = !editing;
  }

  function reset() {
    layout = defaultLayout(actions);
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
    if (!drag || !layout) return;
    const cell = cellAt(e.clientX, e.clientY);
    if (cell !== null) layout = moveTo(layout, drag.action, cell);
    drag = null;
  }
</script>

<main class:editing>
  <div class="body">
    <header>
      <span class="led" class:on={led}></span>
      <span class="brand">REWIND</span>
      <button class="mode" onclick={toggleEdit}>{editing ? 'Terminé' : 'Disposer'}</button>
    </header>

    {#if editing}
      <p class="hint">Glissez une touche sur une autre case. <button class="reset" onclick={reset}>Par défaut</button></p>
    {/if}

    {#if layout}
      <div class="grid" style:--cols={layout.cols} style:--rows={layout.rows}>
        {#each Array(layout.cols * layout.rows) as _, i (i)}
          {@const action = byCell[i]}
          <div class="cell" data-cell={i} class:over={drag?.over === i}>
            {#if action && LOOKS[action]}
              {@const look = LOOKS[action]}
              {@const ch = action.startsWith('channel_') ? channels[Number(action.slice(8))] : undefined}
              <button
                class="key {look.tone}"
                class:logo={!!ch}
                class:down={pressed === action}
                class:lifted={drag?.action === action}
                onpointerdown={(e) => (editing ? dragStart(e, action) : (pressed = action))}
                onpointermove={dragMove}
                onpointerup={(e) => (editing ? dragEnd(e) : ((pressed = null), press(action)))}
                onpointercancel={() => ((pressed = null), (drag = null))}
                onpointerleave={() => !editing && (pressed = null)}
                aria-label={look.caption ? `${look.caption} ${look.label}` : look.label}
              >
                {#if ch}
                  <span class="logo-box"><ChannelLogo number={Number(action.slice(8))} name={ch.name} variant={ch.logo_style} /></span>
                {:else if action === 'tv_power'}
                  <svg class="power-ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v9M6.3 6.8a8 8 0 1 0 11.4 0" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" /></svg>
                  <span class="k-cap">{look.caption}</span>
                {:else}
                  <span class="k-label">{look.label}</span>
                  {#if look.caption}<span class="k-cap">{look.caption}</span>{/if}
                {/if}
              </button>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  </div>

  {#if drag && LOOKS[drag.action]}
    <div class="ghost key {LOOKS[drag.action].tone}" style:left="{drag.x}px" style:top="{drag.y}px">
      <span class="k-label">{LOOKS[drag.action].label}</span>
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
    background: #101012;
    overflow: hidden;
    overscroll-behavior: none;
    -webkit-user-select: none;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }
  main {
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
  /* The plastic body of the remote. */
  .body {
    width: 100%;
    max-width: 420px;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 14px 16px;
    box-sizing: border-box;
    border-radius: 28px 28px 40px 40px;
    background: linear-gradient(90deg, #232326 0%, #36363a 18%, #2c2c30 50%, #36363a 82%, #232326 100%);
    box-shadow:
      inset 0 2px 0 #4a4a50,
      inset 0 -3px 0 #141416,
      0 10px 30px rgba(0, 0, 0, 0.7);
  }
  header {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .led {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #4a0d0d;
    box-shadow: inset 0 1px 2px #000;
  }
  .led.on {
    background: #ff3030;
    box-shadow: 0 0 10px #ff3030;
  }
  .brand {
    flex: 1;
    color: #c9c9cf;
    font-size: 18px;
    letter-spacing: 0.4em;
  }
  .mode,
  .reset {
    font: 14px 'Remote Condensed', sans-serif;
    color: #ddd;
    background: #1a1a1d;
    border: 1px solid #555;
    border-radius: 12px;
    padding: 5px 12px;
  }
  .hint {
    margin: 0;
    color: #f3ec3a;
    font-size: 14px;
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
    gap: 8px;
  }
  .cell {
    min-height: 0;
    display: flex;
    border-radius: 14px;
  }
  .editing .cell {
    outline: 1px dashed #555;
  }
  .cell.over {
    outline: 2px solid #f3ec3a;
  }
  .key {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1px;
    padding: 0;
    border: 0;
    border-radius: 14px;
    color: #f2f2f2;
    font-family: inherit;
    cursor: pointer;
    background: linear-gradient(#5b5b62, #3d3d43);
    box-shadow:
      inset 0 2px 0 rgba(255, 255, 255, 0.25),
      inset 0 -3px 0 rgba(0, 0, 0, 0.35),
      0 3px 0 #111;
    transition: transform 0.05s;
  }
  .key.down {
    transform: translateY(2px);
    box-shadow:
      inset 0 2px 4px rgba(0, 0, 0, 0.5),
      0 1px 0 #111;
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
    font-size: clamp(16px, 4.2dvh, 30px);
    line-height: 1;
  }
  .k-cap {
    font-size: clamp(9px, 1.5dvh, 12px);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.75;
  }
  /* Channel keys show the channel's retro logo, like the TV grid. */
  .key.logo {
    padding: 3px;
    background: #111;
    overflow: hidden;
  }
  .logo-box {
    flex: 1;
    width: 100%;
    min-height: 0;
    display: block;
    border-radius: 11px;
    overflow: hidden;
    pointer-events: none;
  }
  .power-ic {
    width: clamp(18px, 4.4dvh, 32px);
    height: clamp(18px, 4.4dvh, 32px);
  }
  .key.power {
    background: linear-gradient(#e0403a, #a61d18);
    border-radius: 50%;
  }
  .key.number {
    background: linear-gradient(#e9e6dc, #bfbbb0);
    color: #1d1d1f;
  }
  .key.play {
    background: linear-gradient(#3a6fd8, #23479a);
  }
  .key.volume {
    background: linear-gradient(#f0a41f, #b8730b);
    color: #1d1d1f;
  }
  .key.alarm {
    background: linear-gradient(#2fb35a, #1a7a39);
  }
  .key.alarm .k-label {
    font-size: clamp(13px, 2.6dvh, 20px);
  }
  .key.light {
    background: linear-gradient(#6b5bb8, #463a82);
  }
  .ghost {
    position: fixed;
    z-index: 10;
    width: 72px;
    height: 56px;
    transform: translate(-50%, -60%) scale(1.15);
    pointer-events: none;
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.6);
  }
  .toast {
    position: fixed;
    left: 50%;
    bottom: calc(24px + env(safe-area-inset-bottom));
    transform: translateX(-50%);
    max-width: 90vw;
    padding: 10px 14px;
    border-radius: 12px;
    background: #f3ec3a;
    color: #111;
    font: 15px Verdana, sans-serif;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  }
</style>
