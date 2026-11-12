<!--
  Search results (v1 MovieDownloader). Movies: one row per release, with its
  reachability (… probing, ✓ reachable, X unreachable), size and seeders;
  "Download" queues it and opens the library. Series: TMDB shows; choosing one
  adds it to the library and opens its episodes.
-->
<script lang="ts">
  import { tick } from 'svelte';
  import { api, ApiError, type MovieResult, type ShowResult } from '../../lib/api';
  import { t } from '../../lib/i18n';
  import { library } from '../../lib/library.svelte';
  import { search } from '../../lib/search.svelte';
  import { reveal } from '../../lib/sound';
  import { tv } from '../../lib/tv.svelte';
  import CrtHeader from '../CrtHeader.svelte';
  import LibraryFooter from './LibraryFooter.svelte';
  import Poster from './Poster.svelte';

  let root: HTMLElement;
  let detail: HTMLElement | undefined = $state();
  let selected = $state(0);
  let busy = $state(false);
  let error = $state<string | null>(null);

  const isSeries = $derived(search.kind === 'series');
  const rows = $derived<(MovieResult | ShowResult)[]>(isSeries ? search.shows : search.sortedMovies);
  const current = $derived(rows[selected] ?? rows[0] ?? null);
  const canSwitch = $derived(library.features.search && library.features.series);

  // New results (or a new sort): back to the first row, with the retro reveal.
  let shownKey = '';
  $effect(() => {
    const key = `${search.kind}|${search.query}|${search.sort}|${rows.length}`;
    if (key === shownKey) return;
    shownKey = key;
    selected = 0;
    error = null;
    void tick().then(() => root && reveal(root));
  });

  function select(i: number) {
    selected = i;
    error = null;
    void tick().then(() => detail && reveal(detail, ':scope > *'));
  }

  function probeIcon(movie: MovieResult): { text: string; cls: string; title: string } | null {
    const hash = movie.torrent.hash;
    if (!hash) return null;
    const state = search.probe[hash];
    if (state === 'reachable') return { text: '✓', cls: 'ok', title: t('probe.ok') };
    if (state === 'unreachable') return { text: 'X', cls: 'ko', title: t('probe.ko') };
    return { text: '…', cls: 'pending', title: t('probe.pending') };
  }

  function subline(m: MovieResult): string {
    return [m.year, m.torrent.size_label, t('search.seeders', { n: m.torrent.seeders })]
      .filter(Boolean)
      .join(' · ');
  }

  async function download(m: MovieResult) {
    if (busy) return;
    busy = true;
    try {
      const { id } = await api.download({
        title: m.title,
        year: m.year,
        magnet: m.torrent.magnet,
        tmdb_id: m.tmdb_id,
        imdb_id: m.imdb_id,
        poster_url: m.poster_url,
        overview: m.overview,
      });
      tv.downloadStarted(id);
    } catch (err) {
      error = err instanceof ApiError && err.status === 409 ? t('search.exists') : t('search.failed');
    } finally {
      busy = false;
    }
  }

  async function manage(s: ShowResult) {
    if (busy) return;
    busy = true;
    try {
      const show = await api.addSeries(s.tmdb_id);
      await library.load();
      tv.openSeries(library.get(show.id) ?? show);
    } catch {
      error = t('search.failed');
    } finally {
      busy = false;
    }
  }
</script>

<div class="movie-screen flat results" bind:this={root}>
  <CrtHeader title={t('search.title')} />

  {#if search.message}
    <div class="message" data-reveal>{search.message}</div>
  {:else}
    <div class="body">
      <div class="list">
        {#each rows as row, i (i)}
          <button class="row" class:active={i === selected} data-reveal onclick={() => select(i)}>
            {#if !isSeries}
              {@const icon = probeIcon(row as MovieResult)}
              {#if icon}<span class="probe {icon.cls}" title={icon.title}>{icon.text}</span>{/if}
            {/if}
            <span class="r-main">
              <span class="r-title">{row.title}</span>
              <span class="r-sub">{isSeries ? (row.year ?? '') : subline(row as MovieResult)}</span>
            </span>
          </button>
        {/each}
      </div>

      <div class="detail" bind:this={detail}>
        {#if current}
          <Poster src={current.poster_url} />
          <div class="d-title">{current.title}</div>
          {#if current.year}<div class="d-year">{current.year}</div>{/if}
          {#if isSeries}
            <button class="crt-btn primary" disabled={busy} onclick={() => manage(current as ShowResult)}>
              {t('search.manage')}
            </button>
          {:else}
            {@const m = current as MovieResult}
            {@const icon = probeIcon(m)}
            <div class="d-specs">
              {[m.torrent.size_label, t('search.seeders', { n: m.torrent.seeders })].filter(Boolean).join(' · ')}
              {#if icon}<span class="probe {icon.cls}" title={icon.title}>{icon.text}</span>{/if}
            </div>
            <div class="d-release">{m.release}</div>
            <button class="crt-btn primary" disabled={busy} onclick={() => download(m)}>{t('search.download')}</button>
          {/if}
          {#if error}<div class="d-error">{error}</div>{/if}
          {#if current.overview}<div class="overview">{current.overview}</div>{/if}
        {/if}
      </div>
    </div>
  {/if}

  <LibraryFooter>
    {#snippet actions()}
      {#if canSwitch}
        <button class="navbtn" onclick={() => search.toggleKind()}>
          [{isSeries ? t('search.mode_series') : t('search.mode_movies')}]
        </button>
      {/if}
      {#if !isSeries}
        <button class="navbtn fixed" onclick={() => search.cycleSort()}>[{t(`sort.${search.sort}`)}]</button>
      {/if}
    {/snippet}
  </LibraryFooter>
</div>

<style>
  .message {
    flex: 1;
    padding: 12px var(--safe-x);
    font-size: var(--fs-m);
    color: var(--crt-dim);
  }
  .body {
    flex: 1;
    display: flex;
    min-height: 0;
  }
  .list {
    flex: 1 1 60%;
    overflow-y: auto;
    padding: 6px 8px 6px var(--safe-x);
    border-right: 3px solid var(--crt-border);
  }
  .row {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 8px;
    text-align: left;
    border-bottom: 2px solid var(--crt-divider);
  }
  .row.active {
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    text-shadow: none;
    border-bottom-color: transparent;
  }
  .r-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .r-title {
    font-size: var(--fs-l);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .r-sub {
    font-size: var(--fs-sm);
    color: var(--crt-dim);
    margin-top: 2px;
  }
  .row.active .r-sub {
    color: var(--crt-accent-ink);
  }
  .probe {
    flex: 0 0 auto;
    width: 22px;
    text-align: center;
    font-size: var(--fs-l);
  }
  .probe.ok {
    color: var(--crt-f1);
  }
  .probe.ko {
    color: var(--crt-alert);
  }
  .probe.pending {
    color: var(--crt-dim);
    animation: blink 1s steps(1) infinite;
  }
  .row.active .probe {
    color: var(--crt-accent-ink);
  }
  @keyframes blink {
    50% {
      opacity: 0.25;
    }
  }
  .detail {
    flex: 1 1 40%;
    display: flex;
    flex-direction: column;
    padding: 12px var(--safe-x) 12px 14px;
    overflow-y: auto;
  }
  .detail > :global(*) {
    flex: 0 0 auto;
  }
  .d-title {
    margin-top: 10px;
    font-size: var(--fs-l);
    color: var(--crt-accent);
    user-select: text;
  }
  .d-year {
    margin-top: 3px;
    font-size: var(--fs-m);
  }
  .d-specs {
    margin-top: 4px;
    font-size: 18px;
    color: var(--crt-f3);
  }
  .d-specs .probe {
    display: inline-block;
    margin-left: 6px;
  }
  .d-release {
    margin-top: 4px;
    font-size: var(--fs-s);
    color: var(--crt-dim);
    word-break: break-all;
  }
  .detail .crt-btn {
    margin-top: 10px;
    width: 100%;
    text-align: center;
  }
  .d-error {
    margin-top: 6px;
    font-size: var(--fs-sm);
    color: var(--crt-alert);
  }
  .overview {
    margin-top: 8px;
    font-size: var(--fs-sm);
    line-height: 1.35;
  }
</style>
