<!--
  Alarm behaviour, shown as a timeline: the sound fades in, the picture comes
  after a delay and fades in too, everything stops after the max duration.
-->
<script lang="ts">
  import type { Cfg } from '../api';
  import { duration } from '../helpers';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();
  const STEPS = [5, 10, 15, 30];

  const a = $derived(cfg.alarm);
  // Timeline scale: the first two minutes (or the whole alarm if shorter).
  const span = $derived(Math.max(30, Math.min(a.max_duration_s, 120)));
  const pct = (s: number) => `${Math.min(100, (s / span) * 100)}%`;
  const alarmChannel = $derived(cfg.channels.find((c: Cfg) => c.alarm));
</script>

<Window title="Le réveil">
  {#snippet help()}
    <p>
      Réglez l'heure du réveil depuis la télé (sous la grille des chaînes) ou avec la télécommande. Ici, vous réglez
      <strong>comment</strong> il vous réveille : en douceur, le son d'abord, puis l'image.
    </p>
    <p>La chaîne du réveil se choisit dans <strong>Chaînes</strong>.</p>
  {/snippet}

  <p class="sentence">
    À l'heure dite, la télé s'allume{alarmChannel ? ` sur « ${alarmChannel.name} »` : ''}. Le son monte en
    <strong>{duration(a.sound_ramp_s)}</strong>. L'image arrive après <strong>{duration(a.video_delay_s)}</strong> et
    apparaît en <strong>{duration(a.video_ramp_s)}</strong>. Sans réponse, tout s'arrête après
    <strong>{duration(a.max_duration_s)}</strong>.
  </p>

  <div class="timeline" aria-hidden="true">
    <div class="track"><span class="t-label">Son</span><span class="ramp sound" style:width={pct(a.sound_ramp_s)}></span><span class="full sound"></span></div>
    <div class="track">
      <span class="t-label">Image</span>
      <span class="wait" style:width={pct(a.video_delay_s)}></span>
      <span class="ramp image" style:width={pct(a.video_ramp_s)}></span>
      <span class="full image"></span>
    </div>
    <div class="scale"><span>0</span><span>{duration(span)}</span></div>
  </div>

  {#if !alarmChannel}<p class="bad">Aucune chaîne du réveil : choisissez-en une dans « Chaînes ».</p>{/if}
</Window>

<Window title="Réglages fins">
  <span class="label">Pas des touches plus tôt / plus tard</span>
  <div class="steps">
    {#each STEPS as s (s)}
      <button class:selected={a.step_minutes === s} onclick={() => (a.step_minutes = s)}>{s} min</button>
    {/each}
  </div>

  <label><span>Montée du son : {duration(a.sound_ramp_s)}</span>
    <input type="range" min="0" max="120" step="5" bind:value={a.sound_ramp_s} /></label>
  <label><span>L'image arrive après : {duration(a.video_delay_s)}</span>
    <input type="range" min="0" max="120" step="5" bind:value={a.video_delay_s} /></label>
  <label><span>Apparition de l'image : {duration(a.video_ramp_s)}</span>
    <input type="range" min="0" max="60" step="5" bind:value={a.video_ramp_s} /></label>
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
    align-items: stretch;
    height: 22px;
    margin-bottom: 6px;
    border: 1px solid #444;
  }
  .t-label {
    flex: 0 0 56px;
    padding-left: 4px;
    font: 14px/20px var(--cond);
    color: #fff;
    text-transform: uppercase;
    border-right: 1px solid #444;
  }
  .wait {
    background: repeating-linear-gradient(90deg, #222 0 3px, #000 3px 6px);
  }
  .ramp.sound {
    background: linear-gradient(90deg, #000, var(--yellow));
  }
  .full.sound {
    flex: 1;
    background: var(--yellow);
  }
  .ramp.image {
    background: linear-gradient(90deg, #000, #38c7e8);
  }
  .full.image {
    flex: 1;
    background: #38c7e8;
  }
  .scale {
    display: flex;
    justify-content: space-between;
    padding-left: 56px;
    font-size: 12px;
    color: #bbb;
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
