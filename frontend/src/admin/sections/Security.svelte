<!--
  Admin PIN with a big keypad: type the code, type it again to confirm. The
  new PIN goes into the config and is written with the next save.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { untrack } from 'svelte';
  import { t } from '../../lib/i18n';
  import type { Cfg } from '../api';
  import Icon from '../ui/Icon.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  type Stage = 'idle' | 'first' | 'confirm';
  let stage = $state<Stage>('idle');
  let entry = $state('');
  let first = $state('');
  let note = $state<{ ok: boolean; text: string } | null>(null);

  const active = $derived((cfg.admin.pin ?? '') !== '');
  const initial = untrack(() => cfg.admin.pin);
  const changed = $derived(cfg.admin.pin !== initial);

  function start() {
    stage = 'first';
    entry = '';
    note = null;
  }

  function press(d: string) {
    if (entry.length < 8) entry += d;
  }

  function ok() {
    if (entry.length < 4) {
      note = { ok: false, text: t('admin.sec.short') };
      return;
    }
    if (stage === 'first') {
      first = entry;
      entry = '';
      stage = 'confirm';
      note = null;
    } else if (entry === first) {
      cfg.admin.pin = entry;
      stage = 'idle';
      entry = first = '';
      note = { ok: true, text: t('admin.sec.ready') };
    } else {
      entry = first = '';
      stage = 'first';
      note = { ok: false, text: t('admin.sec.mismatch') };
    }
  }

  function removePin() {
    cfg.admin.pin = '';
    note = { ok: true, text: t('admin.sec.removed') };
  }
</script>

<Window title={t('admin.sec.title')} lamp={active ? 'on' : 'todo'}>
  {#snippet help()}
    <p>{t('admin.sec.help1')}</p>
    <p>{@html t('admin.sec.help2')}</p>
  {/snippet}

  {#if stage === 'idle'}
    <div class="state">
      <span class="big" class:off={!active}><Icon name="lock" size={40} /></span>
      <div>
        <strong>{active ? t('admin.sec.protected') : t('admin.sec.none')}</strong>
        <div class="muted">{active ? t('admin.sec.protected_hint') : t('admin.sec.none_hint')}</div>
      </div>
    </div>
    <div class="row">
      <button class="primary" onclick={start}>{active ? t('admin.sec.change') : t('admin.sec.choose')}</button>
      {#if active}<button class="danger" onclick={removePin}>{t('lib.delete')}</button>{/if}
    </div>
  {:else}
    <p class="prompt">{stage === 'first' ? t('admin.sec.type_new') : t('admin.sec.type_again')}</p>
    <div class="screen" aria-live="polite">
      {#each Array(Math.max(4, entry.length)) as _, i (i)}
        <span>{i < entry.length ? '●' : '_'}</span>
      {/each}
    </div>
    <div class="pad">
      {#each ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as d (d)}
        <button onclick={() => press(d)}>{d}</button>
      {/each}
      <button onclick={() => (entry = entry.slice(0, -1))} aria-label={t('admin.sec.erase')}><Glyph name="erase" size="22px" /></button>
      <button onclick={() => press('0')}>0</button>
      <button class="go" onclick={ok}>OK</button>
    </div>
    <div class="row"><button onclick={() => ((stage = 'idle'), (entry = first = ''))}>{t('nav.cancel')}</button></div>
  {/if}
  {#if note}<p class:ok={note.ok} class:bad={!note.ok}>{note.text}</p>{/if}
  {#if changed && stage === 'idle' && !note}<p class="ok">{t('admin.sec.pending')}</p>{/if}
</Window>

<style>
  .state {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 8px 0;
  }
  .big.off {
    opacity: 0.45;
  }
  .prompt {
    text-align: center;
    font: 18px var(--cond);
    text-transform: uppercase;
  }
  .screen {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin: 0 auto 12px;
    padding: 10px;
    max-width: 260px;
    background: #102a10;
    color: #5ff07a;
    font: 26px/1 'Admin Pixel', monospace;
    border: 2px solid var(--ink);
    box-shadow: inset 2px 2px 0 #000;
    text-shadow: 0 0 6px #2bd94f;
  }
  .pad {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    max-width: 260px;
    margin: 0 auto;
  }
  .pad button {
    min-height: 56px;
    font-size: 24px;
  }
  .pad .go {
    background: #2bb04a;
    color: #fff;
  }
</style>
