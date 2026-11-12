<!--
  Picture and sound. Lip-sync: the TV shows a flash + beep test while the
  phone shifts the sound live. Outputs: picked from what the TV computer
  reports (video connectors and modes, audio ports), no names to type.
-->
<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { adminApi, type Cfg, type Hardware } from '../api';
  import { avOffsetText, liveAudio } from '../helpers';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  let hw = $state<Hardware | null>(null);
  let hwError = $state(false);
  let testing = $state(false);
  let testNote = $state('');
  let applyTimer: ReturnType<typeof setTimeout> | undefined;
  let stopTimer: ReturnType<typeof setTimeout> | undefined;

  const display = $derived(hw?.displays.find((d) => d.name === cfg.display.output) ?? null);
  const modes = $derived(display?.modes ?? hw?.displays.find((d) => d.connected)?.modes ?? []);
  // The port the offset applies to: the chosen one, else the first plugged-in output.
  const port = $derived(cfg.audio.output_port || hw?.audio.find((p) => p.available)?.name || null);

  onMount(async () => {
    try {
      hw = await adminApi.hardware();
    } catch {
      hwError = true;
    }
  });

  function setOffset(ms: number) {
    cfg.audio.av_offset_ms = Math.max(-2000, Math.min(2000, Math.round(ms)));
    // Applied live so the test on the TV shows the effect at once (saved later).
    clearTimeout(applyTimer);
    applyTimer = setTimeout(() => {
      if (!port) return;
      liveAudio.port = port;
      void adminApi.avOffset(port, cfg.audio.av_offset_ms).catch(() => {});
    }, 250);
  }

  async function toggleTest() {
    if (testing) return stopTest();
    const { delivered } = await adminApi.tvEvent('avtest').catch(() => ({ delivered: 0 }));
    if (!delivered) {
      testNote = "La télé n'est pas connectée : allumez-la sur REWIND v2.";
      return;
    }
    testing = true;
    testNote = '';
    if (port) void adminApi.avOffset(port, cfg.audio.av_offset_ms).catch(() => {});
    stopTimer = setTimeout(() => (testing = false), 60_000);
  }

  function stopTest() {
    testing = false;
    clearTimeout(stopTimer);
    void adminApi.tvEvent('avtest_stop').catch(() => {});
  }

  onDestroy(() => {
    clearTimeout(applyTimer);
    if (testing) stopTest();
  });
</script>

<Window title="Image">
  {#snippet help()}
    <p>
      Les effets cathodiques imitent un vieux téléviseur : lignes de balayage, léger flou, coins arrondis. Sur une vraie
      télé cathodique, vous pouvez les couper, l'écran s'en charge déjà.
    </p>
  {/snippet}
  <label class="check">
    <input type="checkbox" bind:checked={cfg.display.crt_effects} />
    <span>Effets « écran cathodique »</span>
  </label>
</Window>

<Window title="Son synchronisé">
  {#snippet help()}
    <p>
      Avec certains branchements (adaptateur HDMI → péritel par exemple), l'image arrive en retard sur le son. Pour
      régler :
    </p>
    <ol>
      <li>Touchez <strong>Lancer le test</strong> : la télé affiche un flash avec un bip, chaque seconde.</li>
      <li>Regardez la télé : le bip doit tomber pile sur le flash.</li>
      <li>Bip <strong>avant</strong> le flash : retardez le son (+). Bip <strong>après</strong> : avancez-le (−).</li>
      <li>Le changement s'entend tout de suite. Enregistrez quand c'est bon.</li>
    </ol>
  {/snippet}

  <button class="test-btn" class:on={testing} onclick={toggleTest}>
    {testing ? '■ Arrêter le test' : '▶ Lancer le test sur la télé'}
  </button>
  {#if testNote}<p class="bad">{testNote}</p>{/if}

  <div class="offset">
    <button onclick={() => setOffset(cfg.audio.av_offset_ms - 20)} aria-label="Avancer le son de 20 ms">− 20</button>
    <strong>{cfg.audio.av_offset_ms > 0 ? '+' : ''}{cfg.audio.av_offset_ms} ms</strong>
    <button onclick={() => setOffset(cfg.audio.av_offset_ms + 20)} aria-label="Retarder le son de 20 ms">+ 20</button>
  </div>
  <input
    type="range"
    min="-500"
    max="500"
    step="10"
    value={cfg.audio.av_offset_ms}
    oninput={(e) => setOffset(Number(e.currentTarget.value))}
    aria-label="Décalage du son"
  />
  <p class="sentence">{avOffsetText(cfg.audio.av_offset_ms)}</p>
  {#if hw && !port}<p class="bad">Aucune sortie son branchée : choisissez-en une dans Branchements.</p>{/if}
</Window>

<Window title="Branchements">
  {#snippet help()}
    <p>Les choix viennent du PC de la télé : seules ses vraies sorties sont proposées.</p>
    <p>
      Pour une télé cathodique française (PAL), choisissez la définition <strong>720x576</strong>. L'image change au
      prochain démarrage de la télé ; le son, tout de suite.
    </p>
  {/snippet}
  {#if hwError}
    <p class="bad">Impossible de lire les sorties du PC.</p>
  {:else if !hw}
    <p class="muted">Lecture des sorties du PC…</p>
  {:else}
    <label>
      <span>Sortie vidéo</span>
      <select bind:value={cfg.display.output}>
        <option value={null}>Automatique</option>
        {#each hw.displays as d (d.name)}
          <option value={d.name}>{d.name}{d.connected ? ' — branchée' : ' — rien de branché'}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>Définition</span>
      <select bind:value={cfg.display.mode}>
        <option value={null}>Automatique</option>
        {#each modes as m (m)}
          <option value={m}>{m}{m === '720x576' ? ' — télé cathodique (PAL)' : m === '720x480' ? ' — NTSC' : ''}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>Sortie son</span>
      <select bind:value={cfg.audio.output_port}>
        <option value={null}>Automatique</option>
        {#each hw.audio as p (p.card + p.name)}
          <option value={p.name}>{p.description} ({p.card_description}){p.available ? '' : ' — non branchée'}</option>
        {/each}
      </select>
    </label>
  {/if}
</Window>

<style>
  .test-btn {
    width: 100%;
    min-height: 56px;
    margin: 8px 0;
    background: #2bb04a;
    color: #fff;
    font-size: 19px;
  }
  .test-btn.on {
    background: var(--bad);
  }
  .offset {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin: 8px 0 4px;
  }
  .offset strong {
    flex: 1;
    text-align: center;
    padding: 6px 0;
    font: 24px var(--cond);
    background: #000;
    color: var(--yellow);
    border: 2px solid var(--ink);
  }
</style>
