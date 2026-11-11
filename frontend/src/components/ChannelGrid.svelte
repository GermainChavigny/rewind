<!--
  Channel selector (v1 #channels): 3×3 logo grid shown for a few seconds at
  boot and after each zap; the current channel pops out with a white frame.
  New in v2: a status strip under the grid (alarm, weather, clock) — the
  quick visual check of whether the alarm is armed; click it to set it.
-->
<script lang="ts">
  import { t } from '../lib/i18n';
  import { tv } from '../lib/tv.svelte';
  import BellIcon from './BellIcon.svelte';
  import Clock from './Clock.svelte';
  import WeatherIcon from './WeatherIcon.svelte';

  let hover = $state(false);
  const shown = $derived(tv.gridVisible || hover);
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
      {@const logo = ch.logo ? tv.logos[ch.logo] : null}
      <button
        class="tile"
        class:current={tv.current?.id === ch.id}
        onclick={() => tv.selectChannel(ch.number)}
      >
        {#if logo}
          <img src={logo} alt={ch.name} draggable="false" />
        {:else}
          <span class="fallback"><b>{ch.number}</b>{ch.name}</span>
        {/if}
        {#if logo && ch.show_name}<span class="name">{ch.name}</span>{/if}
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
      <button class="weather" onclick={() => tv.openScreen('weather')}>
        <WeatherIcon code={tv.weather.code} size={20} />
        {tv.weather.periods.find((p) => p.id === 'afternoon')?.temp ?? ''}°
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
  .tile img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .fallback {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 100%;
    padding: 4px;
    background: linear-gradient(var(--crt-panel-2), var(--crt-bg));
    color: #fff;
    font-size: var(--fs-m);
    text-transform: uppercase;
    text-align: center;
    text-shadow: var(--crt-shadow);
  }
  .fallback b {
    font-family: var(--crt-block);
    font-size: 44px;
    color: var(--crt-accent);
  }
  .name {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 2px 4px;
    background: rgba(0, 0, 0, 0.75);
    color: #fff;
    font-size: var(--fs-s);
    text-transform: uppercase;
    text-align: center;
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
