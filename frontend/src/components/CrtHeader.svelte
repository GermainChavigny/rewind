<!--
  Retro set-top-box header: title (+ meta), then clock / weather / date on the
  right (click → weather popup) and the alarm indicator when it is armed
  (click → alarm settings).
-->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { tv } from '../lib/tv.svelte';
  import BellIcon from './BellIcon.svelte';
  import Clock from './Clock.svelte';
  import WeatherIcon from './WeatherIcon.svelte';

  let { title, meta }: { title: string; meta?: Snippet } = $props();
</script>

<header data-reveal>
  <span class="title">{title}</span>
  {#if meta}<span class="meta">{@render meta()}</span>{/if}
  <span class="right">
    {#if tv.modules.alarm && tv.alarm.enabled}
      <button class="alarm" onclick={() => tv.openAlarm()}><BellIcon size={16} />{tv.alarm.time}</button>
    {/if}
    <button class="clock" onclick={() => tv.openOverlay('weather')} disabled={!tv.weather}>
      <Clock part="time" />
      {#if tv.weather}<WeatherIcon code={tv.weather.code} size={22} />{/if}
      <Clock part="date" />
    </button>
  </span>
</header>

<style>
  header {
    display: flex;
    align-items: baseline;
    gap: 0 16px;
    padding: var(--safe-y) var(--safe-x) 10px;
    background: var(--crt-bar-bg);
    border-bottom: 2px solid var(--crt-border);
    text-transform: uppercase;
    letter-spacing: 0.7px;
    flex: 0 0 auto;
  }
  .title {
    font-size: var(--fs-xl);
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .meta {
    font-size: var(--fs-m);
    color: var(--crt-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .right {
    margin-left: auto;
    flex: 0 0 auto;
    white-space: nowrap;
    display: flex;
    align-items: baseline;
    gap: 14px;
    font-size: var(--fs-m);
  }
  .alarm {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--crt-f1);
  }
  .clock {
    display: inline-flex;
    align-items: baseline;
    gap: 8px;
    color: var(--crt-text);
    text-transform: uppercase;
  }
  .clock :global(svg) {
    align-self: center;
  }
</style>
