<!--
  Pixel-art cursor (v1 RetroCursor): the native cursor is hidden and an image
  follows the mouse, at a size that scales with the stage. Elements choose the
  image through the inherited CSS property `--cur` (arrow | hand). Hidden after
  3 s of inactivity and when the mouse leaves the window.
-->
<script lang="ts">
  import { viewport } from '../lib/viewport.svelte';

  const SIZE = 36; // stage px (v1: 5vw on 720)
  const SRC = 32; // source PNG size
  const CURSORS = {
    arrow: { src: '/cursors/cursor.png', hotspot: [0, 0] },
    hand: { src: '/cursors/pointer.png', hotspot: [15, 0] },
  } as const;

  let x = $state(0);
  let y = $state(0);
  let visible = $state(false);
  let kind = $state<'arrow' | 'hand'>('arrow');
  let lastEl: Element | null = null;
  let idle: ReturnType<typeof setTimeout>;

  const w = $derived(SIZE * viewport.geometry.scaleX);
  const h = $derived(SIZE * viewport.geometry.scaleY);
  const c = $derived(CURSORS[kind]);

  function move(e: MouseEvent) {
    x = e.clientX;
    y = e.clientY;
    const el = document.elementFromPoint(x, y);
    if (el !== lastEl) {
      lastEl = el;
      kind = el && getComputedStyle(el).getPropertyValue('--cur').trim() === 'hand' ? 'hand' : 'arrow';
    }
    visible = true;
    clearTimeout(idle);
    idle = setTimeout(() => (visible = false), 3000);
  }
</script>

<svelte:window onmousemove={move} />
<svelte:document onmouseout={(e) => !e.relatedTarget && (visible = false)} />

{#each Object.values(CURSORS) as pre (pre.src)}
  <link rel="preload" as="image" href={pre.src} />
{/each}

<div
  class="cursor"
  class:hidden={!visible}
  style:width="{w}px"
  style:height="{h}px"
  style:background-image="url({c.src})"
  style:transform="translate({x - (c.hotspot[0] / SRC) * w}px, {y - (c.hotspot[1] / SRC) * h}px)"
></div>

<style>
  .cursor {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 2000;
    pointer-events: none;
    image-rendering: pixelated;
    background-size: 100% 100%;
    background-repeat: no-repeat;
    will-change: transform;
  }
</style>
