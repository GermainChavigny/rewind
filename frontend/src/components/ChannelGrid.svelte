<!--
  Channel selector (v1 #channels): 3×3 grid of retro logos (ChannelLogo) shown for a few seconds at
  boot and after each zap, and while the video is paused (new in v2); the
  current channel pops out with a white frame.
  New in v2: a status strip under the grid (alarm, weather, clock) — the
  quick visual check of whether the alarm is armed; click it to set it.
-->
<script lang="ts">
  import { t } from '../lib/i18n';
  import ChannelLogo from './ChannelLogo.svelte';
  import { movie } from '../lib/movie.svelte';
  import { tv } from '../lib/tv.svelte';
  import BellIcon from './BellIcon.svelte';
  import Clock from './Clock.svelte';
  import WeatherIcon from './WeatherIcon.svelte';

  let hover = $state(false);
  // Shown after a zap, while hovered, and while the video is paused — but
  // never over a full screen (alarm, weather, movie screens) or a movie.
  const shown = $derived(
    (tv.gridVisible || hover || tv.paused) && !tv.screen && !tv.overlay && !movie.active,
  );
</script>

<div
  class="grid-wrap"
  class:shown
  role="presentation"
  onpointerenter={() => (hover = tv.gridVisible || hover)}
  onpointerleave={() => (hover = false)}
>
  <div class="grid">
    {#each tv.channels as ch (ch.id)}
      <button
        class="tile"
        class:current={tv.current?.id === ch.id}
        onclick={() => tv.selectChannel(ch.number)}
      >
        <ChannelLogo number={ch.number} name={ch.name} variant={ch.logo_style} />
      </button>
    {/each}
  </div>

  <div class="status">
    {#if tv.modules.alarm}
      <button class="alarm" class:on={tv.alarm.enabled} onclick={() => tv.openScreen('alarm')}>
        <BellIcon />
        {tv.alarm.enabled ? tv.alarm.time : t('alarm.off')}
      </button>
    {/if}
    <span class="spacer"></span>
    {#if tv.weather}
      <button class="weather" onclick={() => tv.openOverlay('weather')}>
        <WeatherIcon code={tv.weather.code} size={20} />
        {tv.weather.periods[0]?.temp ?? ''}°
      </button>
    {/if}
    <span class="clock"><Clock part="time" /></span>
  </div>
</div>

<style>
  .grid-wrap {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 468px; /* v1: 65% of 720 */
    transform: translate(-50%, -50%) scale(0.95);
    opacity: 0;
    transition: all 0.2s;
    pointer-events: none;
    z-index: 10;
  }
  .grid-wrap.shown {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
    pointer-events: auto;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    background: #000;
  }
  .tile {
    position: relative;
    margin: 5px;
    border: 5px solid #363636;
    aspect-ratio: 1;
    background: #000;
    transition: all 0.2s;
    overflow: hidden;
  }
  .tile.current {
    border-color: #fff;
    transform: scale(1.1);
    z-index: 1;
  }
  .status {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 6px 10px 8px;
    background: #000;
    font-size: var(--fs-m);
    text-transform: uppercase;
    color: var(--crt-dim);
  }
  .status button,
  .clock {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .alarm.on {
    color: var(--crt-f1);
  }
  .spacer {
    flex: 1;
  }
  .clock {
    color: #fff;
  }
</style>
