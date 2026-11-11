<!--
  Movie Advisor (v1 MovieAdvisor). Criteria view: the critic's panel, Type and
  Keywords, the 8 criteria (each opens a picker; "Any" is always first),
  Surprise / Search. Recommendations view: 3 equal columns, each with Search
  (torrent search of the English title) and Forget (never suggested again).
-->
<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { advisor, CRITERIA, optionLabel } from '../../lib/advisor.svelte';
  import { t } from '../../lib/i18n';
  import { reveal } from '../../lib/sound';
  import { tv } from '../../lib/tv.svelte';
  import CrtHeader from '../CrtHeader.svelte';
  import LibraryFooter from './LibraryFooter.svelte';
  import Poster from './Poster.svelte';

  let root: HTMLElement;
  let pickerGrid: HTMLElement | undefined = $state();
  let photoBroken = $state(false);

  const picking = $derived(CRITERIA.find((c) => c.key === advisor.picker) ?? null);
  const left = $derived(advisor.recs.filter(Boolean).length);

  function openPicker(key: string) {
    advisor.picker = key;
    void tick().then(() => pickerGrid && reveal(pickerGrid, '.opt'));
  }

  function choose(value: string) {
    if (advisor.picker) advisor.values[advisor.picker] = value;
    advisor.picker = null;
  }

  async function run() {
    await advisor.run();
    await tick();
    reveal(root, '.rec > *');
  }

  onMount(() => reveal(root));
</script>

<div class="movie-screen" bind:this={root}>
  <CrtHeader title={t('adv.title')}>
    {#snippet meta()}{#if advisor.view === 'recs' && left}{t('adv.picks', { n: left })}{/if}{/snippet}
  </CrtHeader>

  {#if advisor.view === 'criteria'}
    <div class="criteria">
      <div class="critic" data-reveal>
        <div class="photo">
          {#if !photoBroken}<img src="/img/advisor-critic.gif" alt="" draggable="false" onerror={() => (photoBroken = true)} />{/if}
        </div>
        <div class="name">{t('adv.critic')}</div>
        <div class="role">{t('adv.role')}</div>
        <div class="quote">« {advisor.quote} »</div>
      </div>
      <div class="col">
        <div class="pair">
          <button class="crt-btn crit" data-reveal onclick={() => (advisor.kind = advisor.kind === 'series' ? 'movie' : 'series')}>
            <span class="c-name">{t('adv.type')}</span>
            <span class="c-val">{advisor.kind === 'series' ? t('adv.series') : t('adv.movies')}</span>
          </button>
          <button class="crt-btn crit" class:keywords={!!advisor.keywords} data-reveal onclick={() => tv.editKeywords()}>
            <span class="c-name">{t('adv.keywords')}</span>
            <span class="c-val">{advisor.keywords || optionLabel('Any')}</span>
          </button>
        </div>
        <div class="grid">
          {#each CRITERIA as c (c.key)}
            <button class="crt-btn crit" data-reveal onclick={() => openPicker(c.key)}>
              <span class="c-name">{t(`adv.c.${c.key}`)}</span>
              <span class="c-val">{optionLabel(advisor.values[c.key])}</span>
            </button>
          {/each}
        </div>
        <div class="go">
          <button class="crt-btn big" data-reveal onclick={() => advisor.surprise()}>{t('adv.surprise')}</button>
          <button class="crt-btn big primary" data-reveal onclick={run}>{t('adv.go')}</button>
        </div>
      </div>
    </div>
  {:else if advisor.message}
    <div class="message">{advisor.message}</div>
  {:else}
    <div class="recs">
      {#each advisor.recs as rec, i (i)}
        {#if rec}
          <div class="rec">
            <Poster src={rec.poster_url} width={115} />
            <div class="r-title">{rec.title}</div>
            <div class="r-year">{rec.year ?? ''}</div>
            <div class="r-acts">
              <button class="crt-btn primary" onclick={() => tv.searchFor(rec.query, rec.kind)}>{t('adv.search')}</button>
              <button class="crt-btn" onclick={() => advisor.forget(i)}>{t('adv.forget')}</button>
            </div>
            <div class="r-sum">{rec.summary}</div>
          </div>
        {:else}
          <div class="rec forgotten">{t('adv.forgotten')}</div>
        {/if}
      {/each}
    </div>
  {/if}

  {#if picking}
    <div class="modal" role="presentation" onclick={(e) => e.target === e.currentTarget && (advisor.picker = null)}>
      <div class="picker" class:compact={picking.options.length <= 4}>
        <div class="pk-head">{t(`adv.c.${picking.key}`)}</div>
        <div class="pk-grid" bind:this={pickerGrid}>
          {#each picking.options as opt (opt)}
            <button
              class="crt-btn opt"
              class:any={opt === 'Any'}
              class:active={opt === advisor.values[picking.key]}
              onclick={() => choose(opt)}
            >
              {optionLabel(opt)}
            </button>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <LibraryFooter>
    {#snippet actions()}
      {#if advisor.view === 'recs'}
        <button class="navbtn" onclick={() => (advisor.view = 'criteria')}>[{t('nav.back')}]</button>
      {/if}
    {/snippet}
  </LibraryFooter>
</div>

<style>
  .criteria {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 14px;
    padding: 9px var(--safe-x);
  }
  .critic {
    flex: 0 0 173px;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .photo {
    width: 100%;
    aspect-ratio: 1;
    border: 2.3px solid var(--crt-border);
    background: var(--crt-panel);
    overflow: hidden;
  }
  .photo img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    image-rendering: pixelated;
  }
  .name {
    margin-top: 7px;
    font-size: 20px;
    color: #fff;
  }
  .role {
    font-size: var(--fs-s);
    color: var(--crt-dim);
    text-transform: uppercase;
  }
  .quote {
    margin-top: 9px;
    padding-top: 7px;
    border-top: 2px solid var(--crt-divider);
    font-size: var(--fs-s);
    line-height: 1.35;
    color: var(--crt-f2);
    overflow: hidden;
  }
  .col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 7px;
  }
  .grid {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-auto-rows: 1fr;
    gap: 7px;
  }
  .crit {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 4px 7px;
    overflow: hidden;
    min-width: 0;
  }
  .c-name {
    font-size: var(--fs-s);
    color: var(--crt-dim);
  }
  .c-val {
    font-size: var(--fs-m);
    color: var(--crt-accent);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .keywords .c-val {
    text-transform: none;
  }
  .crit:hover .c-name,
  .crit:hover .c-val {
    color: var(--crt-accent-ink);
  }
  .go {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 7px;
  }
  .big {
    padding: 11px 0;
    font-size: 23px;
  }
  .message {
    flex: 1;
    padding: 12px var(--safe-x);
    font-size: var(--fs-m);
    color: var(--crt-dim);
  }
  .recs {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 11px;
    padding: 9px var(--safe-x);
  }
  .rec {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    min-height: 0;
    min-width: 0;
  }
  .rec.forgotten {
    justify-content: center;
    color: var(--crt-dim);
    font-size: var(--fs-sm);
  }
  .r-title {
    margin-top: 5px;
    height: 44px;
    font-size: 18px;
    line-height: 1.2;
    color: var(--crt-accent);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .r-year {
    font-size: var(--fs-sm);
    color: var(--crt-dim);
  }
  .r-acts {
    margin-top: 6px;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .r-acts .crt-btn {
    font-size: var(--fs-m);
    padding: 5px 0;
  }
  .r-sum {
    margin-top: 6px;
    font-size: var(--fs-s);
    line-height: 1.3;
    overflow: hidden;
  }
  .modal {
    position: absolute;
    inset: 0;
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--safe-y) var(--safe-x);
    background: rgba(0, 0, 0, 0.72);
  }
  .picker {
    --cols: 3;
    --row: 55px;
    width: 100%;
    max-height: 100%;
    display: flex;
    flex-direction: column;
    padding: 9px 10px;
    background: var(--crt-panel-2);
    border: 3px solid var(--crt-border);
  }
  .picker.compact {
    --cols: 2;
    --row: 63px;
  }
  .pk-head {
    font-size: 21px;
    color: var(--crt-accent);
    text-transform: uppercase;
    padding-bottom: 7px;
    margin-bottom: 8px;
    border-bottom: 2px solid var(--crt-border);
  }
  .pk-grid {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: grid;
    grid-template-columns: repeat(var(--cols), 1fr);
    grid-auto-rows: var(--row);
    gap: 6px;
  }
  .opt {
    padding: 0 4px;
    font-size: var(--fs-sm);
    overflow: hidden;
  }
  .opt.any {
    border-color: var(--crt-accent);
    color: var(--crt-accent);
    background: var(--crt-panel);
  }
  .opt.any:hover,
  .opt.active {
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    border-color: var(--crt-accent);
  }
</style>
