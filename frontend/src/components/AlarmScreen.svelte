<!--
  Alarm settings screen (new in v2 — v1 only had voice feedback): big time
  with ▲/▼ steppers (hours, and minutes by the configured step), on/off
  toggle, the alarm channel. Remote: ↑/↓ still shift the time while it is open.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '../lib/i18n';
  import { shiftTime } from '../lib/levels';
  import { reveal } from '../lib/sound';
  import { tv } from '../lib/tv.svelte';
  import CrtFooter from './CrtFooter.svelte';
  import CrtHeader from './CrtHeader.svelte';

  let root: HTMLElement;
  onMount(() => reveal(root));

  const step = $derived(tv.ui?.alarm.step_minutes ?? 10);
  const channel = $derived(tv.channels.find((c) => c.alarm));
  const [hh, mm] = $derived(tv.alarm.time.split(':'));

  function shift(minutes: number) {
    void tv.setAlarm({ time: shiftTime(tv.alarm.time, minutes), enabled: true });
  }
</script>

<div class="screen" bind:this={root}>
  <CrtHeader title={t('alarm.title')} />
  <main>
    <div class="clock" data-reveal>
      <div class="col">
        <button onclick={() => shift(60)}>▲</button>
        <span class="digits">{hh}</span>
        <button onclick={() => shift(-60)}>▼</button>
      </div>
      <span class="colon">:</span>
      <div class="col">
        <button onclick={() => shift(step)}>▲</button>
        <span class="digits">{mm}</span>
        <button onclick={() => shift(-step)}>▼</button>
      </div>
    </div>

    <div class="row" data-reveal>
      <span class="state" class:on={tv.alarm.enabled}>
        ● {tv.alarm.enabled ? t('alarm.on') : t('alarm.off')}
      </span>
      <button
        class="toggle"
        class:primary={!tv.alarm.enabled}
        onclick={() => tv.setAlarm({ ...tv.alarm, enabled: !tv.alarm.enabled })}
      >
        {tv.alarm.enabled ? t('alarm.toggle_off') : t('alarm.toggle_on')}
      </button>
    </div>

    {#if channel}
      <div class="row dim" data-reveal>{t('alarm.channel')} : {channel.number} · {channel.name}</div>
    {/if}
  </main>
  <CrtFooter>
    {#snippet actions()}
      <button class="navbtn" onclick={() => tv.openScreen(null)}>[{t('alarm.close')}]</button>
    {/snippet}
  </CrtFooter>
</div>

<style>
  .screen {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    background: var(--crt-bg);
  }
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 22px;
    padding: 0 var(--safe-x);
  }
  .clock {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 30px;
    background: var(--crt-panel);
    border: 2px solid var(--crt-border);
  }
  .col {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .col button {
    font-size: var(--fs-xl);
    color: var(--crt-accent);
    padding: 2px 30px;
  }
  .col button:hover {
    background: var(--crt-panel-2);
  }
  .digits,
  .colon {
    font-size: 110px; /* VCR digits: the blinking 12:00 of a 90s VCR */
    line-height: 1;
    color: #fff;
    text-shadow: var(--crt-shadow);
  }
  .colon {
    padding-bottom: 8px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 24px;
    font-size: var(--fs-l);
    text-transform: uppercase;
  }
  .dim {
    color: var(--crt-dim);
    font-size: var(--fs-m);
  }
  .state {
    color: var(--crt-dim);
  }
  .state.on {
    color: var(--crt-f1);
  }
  .toggle {
    min-width: 200px;
    padding: 8px 20px;
    border: 2px solid var(--crt-border);
    background: var(--crt-panel);
    text-transform: uppercase;
  }
  .toggle.primary {
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    border-color: var(--crt-accent);
  }
</style>
