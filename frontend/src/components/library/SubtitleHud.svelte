<!--
  Live subtitle offset (v1 SubtitleHud), top right: appears when the mouse
  moves during playback, fades after 3 s idle (stays while hovered). The movie
  keeps playing, so the shift is judged live. ±0.1 s, per language, saved.
-->
<script lang="ts">
  import { t } from '../../lib/i18n';
  import { movie } from '../../lib/movie.svelte';

  let { awake }: { awake: boolean } = $props();
  let hovering = $state(false);
  // Hidden on the pause screen (it covers the picture), like v1.
  const shown = $derived(
    (awake || hovering) && movie.subMode !== 'off' && !movie.paused && !movie.ended,
  );

  function fmt(o: number): string {
    const v = Math.round(o * 10) / 10;
    return v > 0 ? `+${v.toFixed(1)}s` : v < 0 ? `−${Math.abs(v).toFixed(1)}s` : '0.0s';
  }
</script>

{#if shown}
  <div
    class="hud"
    role="group"
    onpointerenter={() => (hovering = true)}
    onpointerleave={() => (hovering = false)}
  >
    <span class="label">{t('subs.offset')}</span>
    <button class="crt-btn pm" onclick={() => movie.adjustOffset(-0.1)}>−</button>
    <span class="val">{fmt(movie.offset)}</span>
    <button class="crt-btn pm" onclick={() => movie.adjustOffset(0.1)}>+</button>
  </div>
{/if}

<style>
  .hud {
    position: absolute;
    z-index: 35;
    top: var(--safe-y);
    right: var(--safe-x);
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 12px;
    background: var(--crt-bar-bg);
    border: 2px solid var(--crt-border);
    pointer-events: auto;
    text-shadow: var(--crt-shadow);
  }
  .label {
    font-size: 18px;
    color: var(--crt-dim);
    text-transform: uppercase;
  }
  .pm {
    min-width: 36px;
    padding: 3px 0;
    font-size: 23px;
    line-height: 1;
  }
  .val {
    min-width: 64px;
    text-align: center;
    font-size: 20px;
    color: var(--crt-accent);
  }
</style>
