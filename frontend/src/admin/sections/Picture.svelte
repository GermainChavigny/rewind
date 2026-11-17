<!--
  Picture and sound. Lip-sync: the TV shows a flash + beep test while the
  phone shifts the sound live. Outputs: picked from what the TV computer
  reports (video connectors and modes, audio ports), no names to type.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { onDestroy, onMount } from 'svelte';
  import { t } from '../../lib/i18n';
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
      testNote = t('admin.pic.not_connected');
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

<Window title={t('admin.pic.title')}>
  {#snippet help()}
    <p>{t('admin.pic.help')}</p>
  {/snippet}
  <label class="check">
    <input type="checkbox" bind:checked={cfg.display.crt_effects} />
    <span>{t('admin.pic.crt')}</span>
  </label>
</Window>

<Window title={t('admin.av.title')}>
  {#snippet help()}
    <p>{t('admin.av.help')}</p>
    <ol>
      <li>{@html t('admin.av.help1')}</li>
      <li>{t('admin.av.help2')}</li>
      <li>{@html t('admin.av.help3')}</li>
      <li>{t('admin.av.help4')}</li>
    </ol>
  {/snippet}

  <button class="test-btn" class:on={testing} onclick={toggleTest}>
    {#if testing}<Glyph name="stop" /> {t('admin.av.stop')}{:else}<Glyph name="play" /> {t('admin.av.start')}{/if}
  </button>
  {#if testNote}<p class="bad">{testNote}</p>{/if}

  <div class="offset">
    <button onclick={() => setOffset(cfg.audio.av_offset_ms - 20)} aria-label={t('admin.av.minus')}>− 20</button>
    <strong>{cfg.audio.av_offset_ms > 0 ? '+' : ''}{cfg.audio.av_offset_ms} ms</strong>
    <button onclick={() => setOffset(cfg.audio.av_offset_ms + 20)} aria-label={t('admin.av.plus')}>+ 20</button>
  </div>
  <input
    type="range"
    min="-500"
    max="500"
    step="10"
    value={cfg.audio.av_offset_ms}
    oninput={(e) => setOffset(Number(e.currentTarget.value))}
    aria-label={t('admin.av.offset')}
  />
  <p class="sentence">{avOffsetText(cfg.audio.av_offset_ms)}</p>
  {#if hw && !port}<p class="bad">{t('admin.av.no_port')}</p>{/if}
</Window>

<Window title={t('admin.out.title')}>
  {#snippet help()}
    <p>{t('admin.out.help1')}</p>
    <p>{@html t('admin.out.help2')}</p>
  {/snippet}
  {#if hwError}
    <p class="bad">{t('admin.out.error')}</p>
  {:else if !hw}
    <p class="muted">{t('admin.out.loading')}</p>
  {:else}
    <label>
      <span>{t('admin.out.video')}</span>
      <select bind:value={cfg.display.output}>
        <option value={null}>{t('admin.out.auto')}</option>
        {#each hw.displays as d (d.name)}
          <option value={d.name}>{d.name}{d.connected ? t('admin.out.connected') : t('admin.out.nothing')}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>{t('admin.out.mode')}</span>
      <select bind:value={cfg.display.mode}>
        <option value={null}>{t('admin.out.auto')}</option>
        {#each modes as m (m)}
          <option value={m}>{m}{m === '720x576' ? t('admin.out.pal') : m === '720x480' ? ' — NTSC' : ''}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>{t('admin.out.audio')}</span>
      <select bind:value={cfg.audio.output_port}>
        <option value={null}>{t('admin.out.auto')}</option>
        {#each hw.audio as p (p.card + p.name)}
          <option value={p.name}>{p.description} ({p.card_description}){p.available ? '' : t('admin.out.unplugged')}</option>
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
