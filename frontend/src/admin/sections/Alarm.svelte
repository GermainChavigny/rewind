<!--
  Alarm behaviour. A chime (on by default, several soft ones) is the safety
  net in case the video is silent, and is enough on its own: the alarm
  channel is optional. A timeline shows the whole alarm, up to its auto stop.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { onDestroy } from 'svelte';
  import { adminApi, type Cfg } from '../api';
  import { t } from '../../lib/i18n';
  import { CHIMES, chimeText, duration } from '../helpers';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();
  const STEPS = [5, 10, 15, 30];

  const a = $derived(cfg.alarm);
  const alarmChannel = $derived(cfg.channels.find((c: Cfg) => c.alarm));
  const hasChime = $derived(a.chime !== 'none');
  // The timeline spans the whole alarm, up to the automatic stop.
  const span = $derived(Math.max(1, a.max_duration_s));
  // The summary sentence is HTML (bold durations): the channel name is escaped.
  const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
  const pct = (s: number) => `${Math.min(100, (Math.max(0, s) / span) * 100)}%`;

  let player: HTMLAudioElement | null = null;
  let playing = $state<string | null>(null);
  let tvNote = $state('');

  function listen(id: string) {
    player?.pause();
    if (playing === id) {
      playing = null;
      return;
    }
    player = new Audio(`/audio/chimes/${id}.mp3`);
    player.onended = () => (playing = null);
    playing = id;
    player.play().catch(() => (playing = null));
  }

  async function listenOnTv() {
    tvNote = '';
    const { delivered } = await adminApi.tvEvent('chime', a.chime).catch(() => ({ delivered: 0 }));
    tvNote = delivered ? t('admin.alarm.tv_plays') : t('admin.alarm.tv_offline');
  }

  onDestroy(() => player?.pause());
</script>

<Window title={t('admin.alarm.title')}>
  {#snippet help()}
    <p>{@html t('admin.alarm.help1')}</p>
    <p>{@html t('admin.alarm.help2')}</p>
  {/snippet}

  <p class="sentence">
    {t('admin.alarm.s_on')}
    {#if hasChime}
      {@html t(a.sound_delay_s ? 'admin.alarm.s_chime_delay' : 'admin.alarm.s_chime', {
        delay: duration(a.sound_delay_s),
        ramp: duration(a.sound_ramp_s),
      })}
    {/if}
    {#if alarmChannel}
      {@html t('admin.alarm.s_channel', {
        name: esc(alarmChannel.name),
        delay: duration(a.video_delay_s),
        ramp: duration(a.video_ramp_s),
      })}
    {/if}
    {@html t('admin.alarm.s_stop', { max: duration(a.max_duration_s) })}
  </p>

  <div class="timeline" aria-hidden="true">
    {#if hasChime}
      <div class="track">
        <span class="t-label">{t('admin.alarm.chime')}</span>
        <span class="lane">
          <span class="wait" style:width={pct(a.sound_delay_s)}></span>
          <span class="ramp sound" style:width={pct(a.sound_ramp_s)}></span>
          <span class="full sound"></span>
        </span>
      </div>
    {/if}
    {#if alarmChannel}
      <div class="track">
        <span class="t-label">{t('alarm.channel')}</span>
        <span class="lane">
          <span class="wait" style:width={pct(a.video_delay_s)}></span>
          <span class="ramp image" style:width={pct(a.video_ramp_s)}></span>
          <span class="full image"></span>
        </span>
      </div>
    {/if}
    <div class="scale"><span>0</span><span>{t('admin.alarm.stop_at', { time: duration(span) })}</span></div>
  </div>

  {#if !hasChime && !alarmChannel}
    <p class="bad">{t('admin.alarm.nothing')}</p>
  {/if}
</Window>

<Window title={t('admin.alarm.chime')}>
  {#snippet help()}
    <p>{t('admin.alarm.chime_help')} <Glyph name="play" /> {t('admin.alarm.chime_help2')}</p>
  {/snippet}
  <div class="chimes">
    {#each CHIMES as id (id)}
      {@const c = { id, ...chimeText(id) }}
      <div class="chime" class:selected={a.chime === c.id}>
        <button class="pick" onclick={() => (a.chime = c.id)}>
          <span class="radio"></span>
          <span class="c-text"><strong>{c.label}</strong><small>{c.description}</small></span>
        </button>
        {#if c.id !== 'none'}
          <button class="play" onclick={() => listen(c.id)} aria-label={t('admin.alarm.listen', { name: c.label })}><Glyph name={playing === c.id ? 'stop' : 'play'} /></button>
        {/if}
      </div>
    {/each}
  </div>
  {#if hasChime}
    <button onclick={listenOnTv}>{t('admin.alarm.listen_tv')}</button>
    {#if tvNote}<p class="muted">{tvNote}</p>{/if}
  {/if}
</Window>

<Window title={t('admin.alarm.fine')}>
  <span class="label">{t('admin.alarm.step')}</span>
  <div class="steps">
    {#each STEPS as s (s)}
      <button class:selected={a.step_minutes === s} onclick={() => (a.step_minutes = s)}>{s} min</button>
    {/each}
  </div>

  {#if hasChime}
    <label><span>{t('admin.alarm.f_sound_delay', { time: duration(a.sound_delay_s) })}</span>
      <input type="range" min="0" max="600" step="10" bind:value={a.sound_delay_s} /></label>
    <label><span>{t('admin.alarm.f_sound_ramp', { time: duration(a.sound_ramp_s) })}</span>
      <input type="range" min="0" max="120" step="5" bind:value={a.sound_ramp_s} /></label>
  {/if}
  {#if alarmChannel}
    <label><span>{t('admin.alarm.f_video_delay', { time: duration(a.video_delay_s) })}</span>
      <input type="range" min="0" max="120" step="5" bind:value={a.video_delay_s} /></label>
    <label><span>{t('admin.alarm.f_video_ramp', { time: duration(a.video_ramp_s) })}</span>
      <input type="range" min="0" max="60" step="5" bind:value={a.video_ramp_s} /></label>
  {/if}
  <label><span>{t('admin.alarm.f_max', { time: duration(a.max_duration_s) })}</span>
    <input type="range" min="60" max="1800" step="60" bind:value={a.max_duration_s} /></label>
</Window>

<style>
  .timeline {
    margin: 12px 0 4px;
    padding: 8px;
    background: #000;
    border: 2px solid var(--ink);
  }
  .track {
    display: flex;
    height: 22px;
    margin-bottom: 6px;
    border: 1px solid #444;
  }
  .t-label {
    flex: 0 0 76px;
    padding-left: 4px;
    font: 14px/20px var(--cond);
    color: #fff;
    text-transform: uppercase;
    border-right: 1px solid #444;
  }
  .lane {
    flex: 1;
    display: flex;
  }
  .wait {
    background: repeating-linear-gradient(90deg, #222 0 3px, #000 3px 6px);
  }
  .ramp.sound {
    background: linear-gradient(90deg, #000, var(--yellow));
  }
  .full {
    flex: 1;
  }
  .full.sound {
    background: var(--yellow);
  }
  .ramp.image {
    background: linear-gradient(90deg, #000, #38c7e8);
  }
  .full.image {
    background: #38c7e8;
  }
  .scale {
    display: flex;
    justify-content: space-between;
    padding-left: 76px;
    font-size: 12px;
    color: #bbb;
  }
  .chimes {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 8px 0 12px;
  }
  .chime {
    display: flex;
    gap: 6px;
  }
  .pick {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    text-align: left;
  }
  .radio {
    flex: 0 0 auto;
    width: 20px;
    height: 20px;
    border: 2px solid var(--ink);
    border-radius: 50%;
    background: var(--field);
  }
  .selected .radio {
    background: radial-gradient(var(--ink) 40%, var(--field) 45%);
  }
  .selected .pick {
    background: var(--win-2);
  }
  .c-text {
    display: flex;
    flex-direction: column;
  }
  .c-text small {
    font: 12px Verdana, Geneva, sans-serif;
    color: var(--muted);
  }
  .play {
    width: 52px;
    padding: 0;
    font-size: 18px;
  }
  .steps {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 8px;
  }
  .steps button {
    padding: 8px 0;
  }
  .steps .selected {
    background: var(--sel);
    color: var(--sel-ink);
  }
</style>
