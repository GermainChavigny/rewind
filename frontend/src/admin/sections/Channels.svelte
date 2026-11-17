<!--
  Channels as the TV shows them: a 3×3 grid of retro logos. Tap one to edit
  it (name with live logo preview, style, content, alarm, position); empty
  tiles add a channel.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import ChannelLogo from '../../components/ChannelLogo.svelte';
  import { t } from '../../lib/i18n';
  import { type Cfg, slug } from '../api';
  import { playlistId } from '../helpers';
  import Help from '../ui/Help.svelte';
  import Icon from '../ui/Icon.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  let editing = $state<number | null>(null);
  let confirmDelete = $state(false);
  let editor: HTMLElement | undefined = $state();

  const ch = $derived(editing === null ? null : cfg.channels[editing]);

  function open(i: number) {
    editing = editing === i ? null : i;
    confirmDelete = false;
    queueMicrotask(() => editor?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }

  function add() {
    if (cfg.channels.length >= 9) return;
    const n = cfg.channels.length + 1;
    cfg.channels.push({
      id: uniqueId(`chaine-${n}`), name: t('admin.ch.default_name', { n }), logo_style: 1, kind: 'youtube',
      playlist_id: '', save_progress: true, alarm: false,
    }); // prettier-ignore
    open(n - 1);
  }

  function uniqueId(base: string, except?: Cfg): string {
    const taken = cfg.channels.filter((c: Cfg) => c !== except).map((c: Cfg) => c.id);
    let id = base;
    for (let n = 2; taken.includes(id); n++) id = `${base}-${n}`;
    return id;
  }

  function rename(c: Cfg) {
    // Only default ids follow the name; a channel keeps its id once customised
    // (its YouTube progress is stored under it).
    if (c.id.startsWith('chaine-')) c.id = uniqueId(slug(c.name), c);
  }

  function move(delta: number) {
    if (editing === null) return;
    const j = editing + delta;
    if (j < 0 || j >= cfg.channels.length) return;
    const list = cfg.channels;
    [list[editing], list[j]] = [list[j], list[editing]];
    editing = j;
  }

  function remove() {
    if (editing === null) return;
    cfg.channels.splice(editing, 1);
    editing = null;
    confirmDelete = false;
  }

  function setAlarm(on: boolean) {
    cfg.channels.forEach((c: Cfg, j: number) => (c.alarm = on && j === editing));
  }
</script>

<Window title={t('admin.ch.title')} lamp={cfg.channels.length ? 'on' : 'todo'}>
  {#snippet help()}
    <p>{t('admin.ch.help1')}</p>
    <p>{t('admin.ch.help2')}</p>
  {/snippet}

  <p class="muted">{t('admin.ch.tap')} {cfg.channels.length} / 9</p>
  <div class="grid">
    {#each Array(9) as _, i (i)}
      {@const c = cfg.channels[i]}
      {#if c}
        <button class="tile" class:editing={editing === i} onclick={() => open(i)} aria-label={t('admin.ch.tile', { n: i + 1, name: c.name })}>
          <ChannelLogo number={i + 1} name={c.name || ' '} variant={c.logo_style} />
          {#if c.alarm}<span class="badge" title={t('admin.ch.alarm')}><Icon name="alarm" size={18} /></span>{/if}
        </button>
      {:else if i === cfg.channels.length}
        <button class="tile empty" onclick={add} aria-label={t('admin.ch.add_label')}><span>+</span>{t('admin.ch.add')}</button>
      {:else}
        <div class="tile void"></div>
      {/if}
    {/each}
  </div>
</Window>

{#if ch && editing !== null}
  <div bind:this={editor}>
    <Window title={t('admin.ch.default_name', { n: editing + 1 })}>
      <label>
        <span>{t('admin.ch.name')}</span>
        <input bind:value={ch.name} onchange={() => rename(ch)} maxlength="24" placeholder={t('admin.ch.name_placeholder')} />
      </label>

      <span class="label">{t('admin.ch.style')}</span>
      <div class="styles">
        {#each [1, 2] as v (v)}
          <button class:selected={ch.logo_style === v} onclick={() => (ch.logo_style = v)} aria-label={t('admin.ch.style_n', { n: v })}>
            <ChannelLogo number={editing + 1} name={ch.name || ' '} variant={v} />
          </button>
        {/each}
      </div>

      <span class="label">{t('admin.ch.content')}</span>
      <div class="choices">
        <button class:selected={ch.kind === 'youtube'} onclick={() => (ch.kind = 'youtube')}>
          <span class="ic"><Glyph name="play" /> YouTube</span> <small>{t('admin.ch.youtube_hint')}</small>
        </button>
        <button class:selected={ch.kind === 'library'} onclick={() => (ch.kind = 'library')}>
          <span class="ic"><Icon name="library" size={20} /> {t('lib.title')}</span> <small>{t('admin.ch.library_hint')}</small>
        </button>
      </div>

      {#if ch.kind === 'youtube'}
        <label>
          <span>{t('admin.ch.playlist')}</span>
          <input
            value={ch.playlist_id ?? ''}
            oninput={(e) => (ch.playlist_id = playlistId(e.currentTarget.value))}
            placeholder={t('admin.ch.playlist_placeholder')}
            autocapitalize="off"
          />
        </label>
        <Help label={t('admin.ch.howto')}>
          <ol>
            <li>{@html t('admin.ch.howto1')}</li>
            <li>{@html t('admin.ch.howto2')}</li>
            <li>{@html t('admin.ch.howto3')}</li>
          </ol>
          <p>{@html t('admin.ch.howto4')}</p>
        </Help>
        <label class="check">
          <input type="checkbox" bind:checked={ch.save_progress} />
          <span>{t('admin.ch.resume')}</span>
        </label>
        <p class="muted hint">{t('admin.ch.resume_hint')}</p>
      {:else}
        <p class="muted">{t('admin.ch.library_text')}</p>
      {/if}

      <label class="check">
        <input type="checkbox" checked={ch.alarm} onchange={(e) => setAlarm(e.currentTarget.checked)} />
        <span>{t('admin.ch.alarm')}</span>
      </label>
      <p class="muted hint">{t('admin.ch.alarm_hint')}</p>

      <span class="label">{t('admin.ch.number')}</span>
      <div class="row">
        <button onclick={() => move(-1)} disabled={editing === 0}><Glyph name="left" /> {editing}</button>
        <strong class="num">{editing + 1}</strong>
        <button onclick={() => move(1)} disabled={editing === cfg.channels.length - 1}>{editing + 2} <Glyph name="right" /></button>
      </div>

      <div class="row foot">
        {#if confirmDelete}
          <span class="grow">{t('admin.ch.delete_q', { name: ch.name })}</span>
          <button onclick={() => (confirmDelete = false)}>{t('admin.no')}</button>
          <button class="danger" onclick={remove}>{t('admin.yes')}</button>
        {:else}
          <button class="danger" onclick={() => (confirmDelete = true)}>{t('lib.delete')}</button>
          <span class="grow"></span>
          <button class="primary" onclick={() => (editing = null)}>OK</button>
        {/if}
      </div>
    </Window>
  </div>
{/if}

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    padding: 6px;
    background: #000;
    border: 2px solid var(--ink);
  }
  .tile {
    position: relative;
    aspect-ratio: 1;
    padding: 0;
    min-height: 0;
    border: 3px solid #363636;
    border-radius: 0;
    background: #000;
    box-shadow: none;
    overflow: hidden;
  }
  .tile.editing {
    border-color: #fff;
  }
  .tile.empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--yellow);
    border-style: dashed;
    border-color: #777;
    font-size: 15px;
  }
  .tile.empty span {
    font-size: 34px;
    line-height: 1;
  }
  .void {
    border-color: #1a1a1a;
  }
  .badge {
    position: absolute;
    right: 2px;
    bottom: 2px;
    padding: 1px;
    line-height: 0;
    background: var(--yellow);
    border: 1px solid #000;
  }
  .ic {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .styles {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 4px 0 12px;
  }
  .styles button {
    aspect-ratio: 1;
    padding: 0;
    border: 4px solid var(--win);
    border-radius: 0;
    box-shadow: 0 0 0 2px var(--ink);
    background: #000;
    overflow: hidden;
  }
  .styles .selected {
    border-color: var(--sel);
  }
  .hint {
    margin: -6px 0 12px 40px;
  }
  .num {
    min-width: 44px;
    padding: 6px 0;
    text-align: center;
    font: 26px var(--cond);
    background: #000;
    color: var(--yellow);
    border: 2px solid var(--ink);
  }
  .foot {
    margin-top: 16px;
  }
</style>
