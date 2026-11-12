<!--
  Alarm behaviour. A chime (on by default, several soft ones) is the safety
  net in case the video is silent, and is enough on its own: the alarm
  channel is optional. A timeline shows the whole alarm, up to its auto stop.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { onDestroy } from 'svelte';
  import { adminApi, type Cfg } from '../api';
  import { CHIMES, duration } from '../helpers';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();
  const STEPS = [5, 10, 15, 30];

  const a = $derived(cfg.alarm);
  const alarmChannel = $derived(cfg.channels.find((c: Cfg) => c.alarm));
  const hasChime = $derived(a.chime !== 'none');
  // The timeline spans the whole alarm, up to the automatic stop.
  const span = $derived(Math.max(1, a.max_duration_s));
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
    tvNote = delivered ? 'La télé joue la sonnerie.' : "La télé n'est pas connectée (est-elle allumée sur REWIND ?).";
  }

  onDestroy(() => player?.pause());
</script>

<Window title="Le réveil">
  {#snippet help()}
    <p>
      Réglez l'heure du réveil depuis la télé (sous la grille des chaînes) ou avec la télécommande. Ici, vous réglez
      <strong>comment</strong> il vous réveille : en douceur, la sonnerie d'abord, puis la chaîne.
    </p>
    <p>
      La sonnerie est une sécurité si la vidéo n'a pas de son. Elle suffit à elle seule : la chaîne du réveil est
      facultative (elle se choisit dans <strong>Chaînes</strong>).
    </p>
  {/snippet}

  <p class="sentence">
    À l'heure dite, la télé s'allume.
    {#if hasChime}La sonnerie monte en <strong>{duration(a.sound_ramp_s)}</strong>.{/if}
    {#if alarmChannel}
      « {alarmChannel.name} » arrive après <strong>{duration(a.video_delay_s)}</strong> et monte en
      <strong>{duration(a.video_ramp_s)}</strong>.
    {/if}
    Sans réponse, tout s'arrête après <strong>{duration(a.max_duration_s)}</strong>.
  </p>

  <div class="timeline" aria-hidden="true">
    {#if hasChime}
      <div class="track">
        <span class="t-label">Sonnerie</span>
        <span class="lane"><span class="ramp sound" style:width={pct(a.sound_ramp_s)}></span><span class="full sound"></span></span>
      </div>
    {/if}
    {#if alarmChannel}
      <div class="track">
        <span class="t-label">Chaîne</span>
        <span class="lane">
          <span class="wait" style:width={pct(a.video_delay_s)}></span>
          <span class="ramp image" style:width={pct(a.video_ramp_s)}></span>
          <span class="full image"></span>
        </span>
      </div>
    {/if}
    <div class="scale"><span>0</span><span>arrêt : {duration(span)}</span></div>
  </div>

  {#if !hasChime && !alarmChannel}
    <p class="bad">Ni sonnerie ni chaîne du réveil : le réveil ne fera rien.</p>
  {/if}
</Window>

<Window title="Sonnerie">
  {#snippet help()}
    <p>Des sonneries douces, qui montent progressivement. Touchez <Glyph name="play" /> pour écouter sur le téléphone.</p>
  {/snippet}
  <div class="chimes">
    {#each CHIMES as c (c.id)}
      <div class="chime" class:selected={a.chime === c.id}>
        <button class="pick" onclick={() => (a.chime = c.id)}>
          <span class="radio"></span>
          <span class="c-text"><strong>{c.label}</strong><small>{c.description}</small></span>
        </button>
        {#if c.id !== 'none'}
          <button class="play" onclick={() => listen(c.id)} aria-label="Écouter {c.label}"><Glyph name={playing === c.id ? 'stop' : 'play'} /></button>
        {/if}
      </div>
    {/each}
  </div>
  {#if hasChime}
    <button onclick={listenOnTv}>Écouter sur la télé</button>
    {#if tvNote}<p class="muted">{tvNote}</p>{/if}
  {/if}
</Window>

<Window title="Réglages fins">
  <span class="label">Pas des touches plus tôt / plus tard</span>
  <div class="steps">
    {#each STEPS as s (s)}
      <button class:selected={a.step_minutes === s} onclick={() => (a.step_minutes = s)}>{s} min</button>
    {/each}
  </div>

  {#if hasChime}
    <label><span>Montée de la sonnerie : {duration(a.sound_ramp_s)}</span>
      <input type="range" min="0" max="120" step="5" bind:value={a.sound_ramp_s} /></label>
  {/if}
  {#if alarmChannel}
    <label><span>La chaîne arrive après : {duration(a.video_delay_s)}</span>
      <input type="range" min="0" max="120" step="5" bind:value={a.video_delay_s} /></label>
    <label><span>Montée du son de la chaîne : {duration(a.video_ramp_s)}</span>
      <input type="range" min="0" max="60" step="5" bind:value={a.video_ramp_s} /></label>
  {/if}
  <label><span>Arrêt automatique après : {duration(a.max_duration_s)}</span>
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
