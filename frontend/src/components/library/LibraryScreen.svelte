<!--
  Library (v1 MovieBrowser): list on the left, details on the right, all with
  the cursor. Movies / Series tabs (only when both exist), filter (unseen by
  default) and sort in the footer. Unfinished downloads come first, so this is
  also the downloads list.
-->
<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { api, posterUrl, type Media } from '../../lib/api';
  import { t } from '../../lib/i18n';
  import {
    episodeCode,
    formatTime,
    isActive,
    isReady,
    isWatched,
    library,
    playedRatio,
    statusInfo,
  } from '../../lib/library.svelte';
  import { reveal } from '../../lib/sound';
  import { tv } from '../../lib/tv.svelte';
  import CrtHeader from '../CrtHeader.svelte';
  import Bar from './Bar.svelte';
  import LibraryFooter from './LibraryFooter.svelte';
  import Poster from './Poster.svelte';

  const SORTS = ['default', 'title', 'recent', 'year', 'progress'] as const;
  const FILTERS = ['unseen', 'all', 'seen'] as const;

  let root: HTMLElement;
  let detail: HTMLElement | undefined = $state();
  let list: HTMLElement | undefined = $state();
  let tab = $state<'movies' | 'series'>('movies');
  let sort = $state<(typeof SORTS)[number]>('default');
  let filter = $state<(typeof FILTERS)[number]>('unseen');
  let selectedId = $state<string | null>(null);
  let confirming = $state(false);

  const hasMovies = $derived(library.movies.length > 0);
  const hasShows = $derived(library.shows.length > 0);
  const showTabs = $derived(hasMovies && hasShows);
  const currentTab = $derived(showTabs ? tab : hasShows && !hasMovies ? 'series' : 'movies');

  const byTitle = (a: Media, b: Media) => a.title.localeCompare(b.title, 'fr', { sensitivity: 'base' });

  const visible = $derived.by(() => {
    if (currentTab === 'series') {
      const shows = [...library.shows];
      if (sort === 'title') return shows.sort(byTitle);
      if (sort === 'year') return shows.sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
      return shows;
    }
    let items = library.movies;
    if (filter === 'seen') items = items.filter(isWatched);
    else if (filter === 'unseen') items = items.filter((m) => !isWatched(m));
    switch (sort) {
      case 'title':
        return [...items].sort(byTitle);
      case 'recent':
        return [...items].sort((a, b) => b.added_at - a.added_at);
      case 'year':
        return [...items].sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
      case 'progress':
        return [...items].sort((a, b) => playedRatio(b) - playedRatio(a));
      default:
        return items;
    }
  });

  const selected = $derived(
    visible.find((m) => m.id === selectedId) ?? visible[0] ?? null,
  );

  function select(id: string) {
    if (id === selected?.id) return;
    selectedId = id;
    confirming = false;
    void tick().then(() => {
      if (!detail) return;
      detail.scrollTop = 0;
      reveal(detail, ':scope > *');
    });
  }

  function remove(item: Media) {
    if (!confirming) {
      confirming = true;
      return;
    }
    confirming = false;
    void library.remove(item);
  }

  async function retry(item: Media) {
    await api.retry(item.id).catch(() => {});
    library.watchJobs();
    void library.load();
  }

  function play(item: Media) {
    const queue = library.movies.filter(isReady);
    tv.playMovie(item, queue, queue.findIndex((m) => m.id === item.id));
  }

  /** Series: resume the last played episode, or the next one once it is watched. */
  function resumeTarget(show: Media): { item: Media; verb: 'resume' | 'next' } | null {
    const last = library.lastPlayedEpisode(show.id);
    if (!last) return null;
    if (isWatched(last)) {
      const next = library.nextReadyEpisode(show.id, last.season!, last.episode!);
      if (next) return { item: next, verb: 'next' };
    }
    return { item: last, verb: 'resume' };
  }

  // Changing tab, filter or sort re-reveals the list (not on each catalog refresh).
  $effect(() => {
    void tab;
    void filter;
    void sort;
    void tick().then(() => list && reveal(list, '.row'));
  });

  const ownedCount = (show: Media) => library.readyEpisodes(show.id).length;

  onMount(() => {
    const focus = library.get(tv.libraryFocus);
    if (focus) {
      tab = focus.kind === 'series' ? 'series' : 'movies';
      if (focus.kind === 'movie') filter = 'all'; // a fresh download is "unseen" anyway
      selectedId = focus.id;
    }
    void tick().then(() => {
      reveal(root);
      root.querySelector('.row.active')?.scrollIntoView({ block: 'nearest' });
    });
  });
</script>

<div class="movie-screen" bind:this={root}>
  <CrtHeader title={t('lib.title')}>
    {#snippet meta()}
      {#if library.freeBytes}{t('lib.free', { size: (library.freeBytes / 1e9).toFixed(1) })}{/if}
    {/snippet}
  </CrtHeader>

  <div class="body">
    <div class="left">
      {#if showTabs}
        <div class="tabs" data-reveal>
          <button class:active={currentTab === 'movies'} onclick={() => (tab = 'movies')}>{t('lib.movies')}</button>
          <button class:active={currentTab === 'series'} onclick={() => (tab = 'series')}>{t('lib.series')}</button>
        </div>
      {/if}
      <div class="list" bind:this={list}>
        {#each visible as item (item.id)}
          {@const st = statusInfo(item)}
          <button
            class="row"
            class:active={item.id === selected?.id}
            class:busy={isActive(item)}
            class:error={item.status === 'error'}
            data-reveal
            onclick={() => select(item.id)}
          >
            <span class="main"><span class="caret">&gt;</span><span class="title">{item.title}</span></span>
            {#if item.kind === 'series'}
              <span class="status count">{t('lib.episodes_short', { owned: ownedCount(item), total: library.totalEpisodes(item) })}</span>
            {:else if isReady(item)}
              <Bar ratio={playedRatio(item)} height={13} />
            {:else}
              <span class="status">{st.label}</span>
            {/if}
          </button>
        {:else}
          {#if currentTab === 'series' ? !hasShows : !hasMovies}
            <div class="empty">{currentTab === 'series' ? t('lib.empty_series') : t('lib.empty')}</div>
          {/if}
        {/each}
      </div>
    </div>

    <div class="detail" class:empty-detail={!selected} bind:this={detail}>
      {#if !selected}
        {t('lib.select')}
      {:else if selected.kind === 'series'}
        {@const owned = ownedCount(selected)}
        {@const total = library.totalEpisodes(selected)}
        {@const target = resumeTarget(selected)}
        <Poster src={posterUrl(selected.id)} />
        <div class="d-title">{selected.title}</div>
        {#if selected.year}
          <div class="d-year">
            {selected.year}{#if selected.tmdb_status === 'Returning Series' || selected.tmdb_status === 'In Production'} · {t('lib.ongoing')}{/if}
          </div>
        {/if}
        <div class="d-prog">
          {t('lib.episodes_count', { owned, total })}
          <Bar ratio={total ? owned / total : 0} height={14} />
        </div>
        <div class="actions">
          {#if target}
            <button class="crt-btn primary" onclick={() => tv.playEpisode(selected.id, target.item.season!, target.item.episode!)}>
              {t(target.verb === 'next' ? 'lib.next_ep' : 'lib.resume_ep', { code: episodeCode(target.item.season, target.item.episode) })}
            </button>
          {/if}
          <button class="crt-btn" onclick={() => tv.openSeries(selected)}>{t('lib.episodes')}</button>
          <button class="crt-btn danger" class:active={confirming} onclick={() => remove(selected)}>
            {confirming ? t('lib.confirm') : t('lib.delete')}
          </button>
        </div>
        {#if selected.overview}<div class="overview">{selected.overview}</div>{/if}
      {:else}
        {@const ready = isReady(selected)}
        {@const st = statusInfo(selected)}
        <Poster src={posterUrl(selected.id)} />
        <div class="d-title">{selected.title}</div>
        {#if selected.year}<div class="d-year">{selected.year}</div>{/if}
        <div class="d-prog" class:error={selected.status === 'error'}>
          {#if ready}
            {#if selected.duration}{formatTime(selected.position)} / {formatTime(selected.duration)}{/if}
            <Bar ratio={playedRatio(selected)} height={14} />
          {:else}
            {st.full}
            <Bar ratio={st.ratio} phase={st.phase} height={14} />
          {/if}
        </div>
        <div class="actions">
          {#if ready}
            <button class="crt-btn primary" onclick={() => play(selected)}>
              {selected.position > 0 && !isWatched(selected) ? t('lib.resume') : t('lib.play')}
            </button>
          {:else if selected.status === 'error'}
            <button class="crt-btn" onclick={() => retry(selected)}>{t('lib.retry')}</button>
          {/if}
          <button class="crt-btn danger" class:active={confirming} onclick={() => remove(selected)}>
            {confirming ? t('lib.confirm') : t('lib.delete')}
          </button>
        </div>
        {#if selected.overview}<div class="overview">{selected.overview}</div>{/if}
      {/if}
    </div>
  </div>

  <LibraryFooter>
    {#snippet actions()}
      {#if currentTab === 'movies'}
        <button class="navbtn fixed" onclick={() => (filter = FILTERS[(FILTERS.indexOf(filter) + 1) % FILTERS.length])}>
          [{t(`filter.${filter}`)}]
        </button>
      {/if}
      <button class="navbtn fixed" onclick={() => (sort = SORTS[(SORTS.indexOf(sort) + 1) % SORTS.length])}>
        [{t(`sort.${sort}`)}]
      </button>
    {/snippet}
  </LibraryFooter>
</div>

<style>
  .body {
    flex: 1;
    display: flex;
    min-height: 0;
  }
  .left {
    flex: 1 1 66%;
    display: flex;
    flex-direction: column;
    min-height: 0;
    border-right: 3px solid var(--crt-border);
  }
  .tabs {
    display: flex;
    gap: 6px;
    padding: 4px var(--safe-x) 0;
  }
  .tabs button {
    border-bottom: 3px solid transparent;
    color: var(--crt-dim);
    font-size: var(--fs-m);
    text-transform: uppercase;
    padding: 3px 8px;
    text-shadow: var(--crt-shadow);
  }
  .tabs button.active {
    color: var(--crt-accent);
    border-bottom-color: var(--crt-accent);
  }
  .list {
    flex: 1;
    overflow-y: auto;
    padding: 6px 8px 6px var(--safe-x);
  }
  .row {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 30%;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
    text-align: left;
    border-bottom: 2px solid var(--crt-divider);
  }
  .row.active {
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    text-shadow: none;
    border-bottom-color: transparent;
  }
  .row.active :global(.crt-bar) {
    background: var(--crt-bg);
  }
  .row.active :global(.crt-bar > i) {
    background: #747aff;
  }
  .main {
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
  }
  .caret {
    display: none;
    font-size: var(--fs-l);
  }
  .row.active .caret {
    display: inline;
  }
  .title {
    font-size: var(--fs-l);
    line-height: 1.05;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .status {
    font-size: var(--fs-sm);
    text-align: right;
    white-space: nowrap;
    color: var(--crt-f3);
  }
  .row.active .status {
    color: var(--crt-accent-ink);
  }
  .row.error .status {
    color: var(--crt-alert);
  }
  .empty {
    padding: 40px 12px;
    font-size: var(--fs-l);
    color: var(--crt-dim);
    text-align: center;
  }
  .detail {
    flex: 1 1 34%;
    display: flex;
    flex-direction: column;
    padding: 12px var(--safe-x) 12px 14px;
    overflow-y: auto;
  }
  .detail > :global(*) {
    flex: 0 0 auto;
  }
  .detail.empty-detail {
    justify-content: center;
    text-align: center;
    color: var(--crt-dim);
  }
  .d-title {
    margin-top: 10px;
    font-size: var(--fs-l);
    color: var(--crt-accent);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    user-select: text;
  }
  .d-year {
    margin-top: 3px;
    font-size: var(--fs-m);
  }
  .d-prog {
    margin-top: 10px;
    font-size: var(--fs-m);
    word-break: break-word;
  }
  .d-prog :global(.crt-bar) {
    margin-top: 5px;
  }
  .d-prog.error {
    color: var(--crt-alert);
  }
  .actions {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 10px;
  }
  .actions .crt-btn {
    width: 100%;
    text-align: center;
  }
  .overview {
    margin-top: 10px;
    font-size: var(--fs-sm);
    line-height: 1.35;
  }
</style>
