<!--
  Today's forecast, 90s cable weather channel style (v1 WeatherPopup): white
  badge, "<CITY> AREA · TODAY'S FORECAST" + clock, three blue panels
  (morning / afternoon / evening) on a violet→orange frame, lo/hi bar.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '../lib/i18n';
  import { reveal } from '../lib/sound';
  import { tv } from '../lib/tv.svelte';
  import Clock from './Clock.svelte';
  import WeatherIcon, { conditionKey } from './WeatherIcon.svelte';

  let root: HTMLElement;
  onMount(() => reveal(root));
  const w = $derived(tv.weather);
</script>

<div class="backdrop" role="presentation" onclick={() => tv.openScreen(null)} bind:this={root}>
  {#if w}
    <div class="frame" data-reveal>
      <div class="head" data-reveal>
        <span class="badge"><b>{t('weather.badge_top')}</b>{t('weather.badge')}<b>{t('weather.badge_bottom')}</b></span>
        <span class="title">
          {#if w.location}<span>{t('weather.area', { location: w.location })}</span><br />{/if}
          {t('weather.today')}
        </span>
        <span class="clock"><Clock part="time" /><span class="date"><Clock part="date" /></span></span>
      </div>
      <div class="panels">
        {#each w.periods as p (p.id)}
          <div class="panel" data-reveal>
            <div class="day">{t(`weather.${p.id}`)}</div>
            <div class="icon"><WeatherIcon code={p.code} size={79} /></div>
            <div class="cond">{t(conditionKey(p.code))}</div>
            <div class="temp">{p.temp}°</div>
          </div>
        {/each}
      </div>
      <div class="foot" data-reveal>
        <span>{t(conditionKey(w.day.code))}</span>
        <span class="lohi">{t('weather.lo')} <b>{w.day.lo}°</b> &nbsp; {t('weather.hi')} <b>{w.day.hi}°</b></span>
      </div>
    </div>
  {/if}
</div>

<style>
  .backdrop {
    position: absolute;
    inset: 0;
    z-index: 20;
    pointer-events: auto;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--safe-y) var(--safe-x);
    background: rgba(0, 0, 0, 0.62);
    --cur: hand;
  }
  .frame {
    width: 100%;
    max-width: 583px;
    padding: 22px;
    background: linear-gradient(#37167f, #f5660f);
    box-shadow: 0 0 0 2px #fff;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 3px 7px;
    color: #fff;
  }
  .badge {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    line-height: 1;
    padding: 4px 7px;
    background: #fff;
    color: #10328c;
    font-size: 18px;
    border-radius: 4px;
  }
  .badge b {
    font-size: 9px;
    font-weight: normal;
    letter-spacing: 0.7px;
  }
  .title {
    flex: 1;
    font-size: var(--fs-m);
    color: var(--crt-accent);
    text-transform: uppercase;
    line-height: 1.15;
    text-shadow: var(--crt-shadow);
  }
  .title span {
    color: #fff;
  }
  .clock {
    margin-left: auto;
    text-align: right;
    font-size: var(--fs-m);
    white-space: nowrap;
    text-shadow: var(--crt-shadow);
    text-transform: uppercase;
  }
  .date {
    display: block;
    color: #c4c4c4;
  }
  .panels {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
  }
  .panel {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    padding: 9px 4px;
    background: linear-gradient(#7f90ff, #0204fb);
    border: 7px double #fff;
    color: #fff;
  }
  .day {
    font-size: 20px;
    color: var(--crt-accent);
    text-transform: uppercase;
    text-shadow: var(--crt-shadow);
  }
  .icon {
    filter: drop-shadow(1.5px 1.5px 0 #000) drop-shadow(2px 2px 0 #000);
  }
  .cond {
    font-size: 18px;
    text-align: center;
    min-height: 33px;
    line-height: 1.1;
    text-shadow: var(--crt-shadow);
  }
  .temp {
    font-size: var(--fs-xxl);
    text-shadow: var(--crt-shadow);
  }
  .foot {
    display: flex;
    justify-content: space-between;
    padding: 6px 10px;
    background: #0a1330;
    color: #fff;
    font-size: 18px;
    text-transform: uppercase;
  }
  .lohi {
    color: var(--crt-dim);
  }
  .lohi b {
    font-weight: normal;
    color: var(--crt-accent);
  }
</style>
