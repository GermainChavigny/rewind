<!--
  The 720×576 stage, scaled into the 4:3 frame (see lib/stage.ts).
  `layer` sets the stacking order between stages (OSDs sit above the veil).
-->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { STAGE_H, STAGE_W } from '../lib/stage';
  import { viewport } from '../lib/viewport.svelte';

  let { layer, children }: { layer: number; children: Snippet } = $props();
  const g = $derived(viewport.geometry);
</script>

<div
  class="stage"
  style:z-index={layer}
  style:width="{STAGE_W}px"
  style:height="{STAGE_H}px"
  style:transform="translate({g.left}px, {g.top}px) scale({g.scaleX}, {g.scaleY})"
>
  {@render children()}
</div>

<style>
  .stage {
    position: fixed;
    left: 0;
    top: 0;
    transform-origin: 0 0;
    pointer-events: none; /* children opt in */
  }
  .stage > :global(*) {
    pointer-events: auto;
  }
</style>
