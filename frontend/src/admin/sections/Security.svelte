<!--
  Admin PIN with a big keypad: type the code, type it again to confirm. The
  new PIN goes into the config and is written with the next save.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { untrack } from 'svelte';
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
      note = { ok: false, text: 'Au moins 4 chiffres.' };
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
      note = { ok: true, text: 'Nouveau code prêt. Enregistrez pour l\'activer.' };
    } else {
      entry = first = '';
      stage = 'first';
      note = { ok: false, text: 'Les deux codes ne correspondent pas. Recommencez.' };
    }
  }

  function removePin() {
    cfg.admin.pin = '';
    note = { ok: true, text: 'Le code sera supprimé à l\'enregistrement.' };
  }
</script>

<Window title="Protection" lamp={active ? 'on' : 'todo'}>
  {#snippet help()}
    <p>
      Le code protège ces réglages : sans lui, n'importe qui connecté à votre Wi-Fi peut les modifier. La télé, elle,
      ne demande jamais le code.
    </p>
    <p>
      Code oublié ? Sur le PC de la télé, effacez la ligne <code>pin</code> de la rubrique <code>[admin]</code> du
      fichier <code>~/.config/rewind/config.toml</code> et enregistrez : c'est pris en compte aussitôt.
    </p>
  {/snippet}

  {#if stage === 'idle'}
    <div class="state">
      <span class="big" class:off={!active}><Icon name="lock" size={40} /></span>
      <div>
        <strong>{active ? 'Réglages protégés' : 'Aucun code'}</strong>
        <div class="muted">{active ? 'Le code est demandé sur chaque téléphone.' : 'Conseillé : choisissez un code de 4 à 8 chiffres.'}</div>
      </div>
    </div>
    <div class="row">
      <button class="primary" onclick={start}>{active ? 'Changer le code' : 'Choisir un code'}</button>
      {#if active}<button class="danger" onclick={removePin}>Supprimer</button>{/if}
    </div>
  {:else}
    <p class="prompt">{stage === 'first' ? 'Tapez le nouveau code' : 'Tapez-le encore une fois'}</p>
    <div class="screen" aria-live="polite">
      {#each Array(Math.max(4, entry.length)) as _, i (i)}
        <span>{i < entry.length ? '●' : '_'}</span>
      {/each}
    </div>
    <div class="pad">
      {#each ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as d (d)}
        <button onclick={() => press(d)}>{d}</button>
      {/each}
      <button onclick={() => (entry = entry.slice(0, -1))} aria-label="Effacer"><Glyph name="erase" size="22px" /></button>
      <button onclick={() => press('0')}>0</button>
      <button class="go" onclick={ok}>OK</button>
    </div>
    <div class="row"><button onclick={() => ((stage = 'idle'), (entry = first = ''))}>Annuler</button></div>
  {/if}
  {#if note}<p class:ok={note.ok} class:bad={!note.ok}>{note.text}</p>{/if}
  {#if changed && stage === 'idle' && !note}<p class="ok">Modification prête : enregistrez pour l'appliquer.</p>{/if}
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
