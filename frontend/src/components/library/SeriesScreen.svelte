<!--
  A series (v1 SeriesPopup): season tabs + episode list on the left, episode
  details on the right (still, synopsis, state, action). Download an episode,
  a season or play an episode. Opens at the last watched episode.
  The season view is polled while the screen is open (download progress).
-->
<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import { api, type EpisodeView, type SeasonView } from '../../lib/api';
  import { t } from '../../lib/i18n';
  import { episodeCode, formatTime, library } from '../../lib/library.svelte';
  import { reveal } from '../../lib/sound';
  import { tv } from '../../lib/tv.svelte';
  import CrtHeader from '../CrtHeader.svelte';
  import Bar from './Bar.svelte';
  import LibraryFooter from './LibraryFooter.svelte';
  import Poster from './Poster.svelte';

  const POLL_MS = 1500;
  const ICONS = { ready: '▶', watched: '✓', downloading: '…', error: '!', missing: '+' } as const;

  const show = tv.show!;
  const seasons = (show.seasons ?? []).map((s) => s.season_number);
  let root: HTMLElement;
  let detail: HTMLElement | undefined = $state();
  let season = $state(
    tv.showAt.season && seasons.includes(tv.showAt.season) ? tv.showAt.season : (seasons[0] ?? 1),
  );
  let selectedEp = $state<number | null>(tv.showAt.episode ?? null);
  let view = $state<SeasonView | null>(null);
  let failed = $state(false);
  let notice = $state<string | null>(null);
  let requested = $state(new Set<string>()); // clicked, waiting for the server state
  let confirmEp = $state<number | null>(null);
  let confirmSeason = $state(false);
  let scrollToSelected = tv.showAt.episode != null;
  let timer: ReturnType<typeof setInterval>;

  const episodes = $derived(view?.season === season ? view.episodes : []);
  const current = $derived(episodes.find((e) => e.episode === selectedEp) ?? episodes[0] ?? null);

  function stateOf(e: EpisodeView): EpisodeView['state'] {
    return e.state === 'missing' && requested.has(`${season}x${e.episode}`) ? 'downloading' : e.state;
  }

  function noticeText(code: string | null): string | null {
    if (!code) return null;
    const key = `series.notice.${code}`;
    const text = t(key);
    return text === key ? code : text;
  }

  async function load() {
    const n = season;
    try {
      const v = await api.season(show.id, n);
      if (n !== season) return; // season changed meanwhile
      view = v;
      failed = false;
      notice = noticeText(v.notice);
      if (scrollToSelected) {
        scrollToSelected = false;
        await tick();
        root.querySelector('.ep.active')?.scrollIntoView({ block: 'center' });
      }
    } catch {
      if (n === season) failed = true;
    }
  }

  function selectSeason(n: number) {
    if (n === season) return;
    season = n;
    selectedEp = null;
    view = null;
    confirmEp = null;
    confirmSeason = false;
    void load();
  }

  function selectEpisode(n: number) {
    if (n !== selectedEp) confirmEp = null;
    selectedEp = n;
    void tick().then(() => detail && reveal(detail, ':scope > *'));
  }

  function download(scope: 'episode' | 'season', episode?: number) {
    notice = t('series.notice.searching');
    if (episode != null) requested = new Set(requested).add(`${season}x${episode}`);
    api.downloadSeries(show.id, scope, season, episode).then(
      () => library.watchJobs(),
      (err: Error) => (notice = err.message),
    );
  }

  async function deleteEpisode(e: EpisodeView) {
    if (confirmEp !== e.episode) {
      confirmEp = e.episode;
      return;
    }
    confirmEp = null;
    await api.deleteMedia(e.id).catch((err: Error) => (notice = err.message));
    await Promise.all([load(), library.load()]);
  }

  async function deleteSeason() {
    if (!confirmSeason) {
      confirmSeason = true;
      return;
    }
    confirmSeason = false;
    await api.deleteSeason(show.id, season).catch((err: Error) => (notice = err.message));
    await Promise.all([load(), library.load()]);
  }

  function phaseLabel(e: EpisodeView): string {
    const pct = `${Math.round(e.progress * 100)}%`;
    if (e.phase === 'transcoding') return t('lib.converting', { pct });
    if (e.phase === 'downloading') return t('lib.downloading', { pct });
    if (e.phase === 'fetching-subs') return t('lib.subtitles');
    return t('lib.queued');
  }

  onMount(() => {
    void load().then(() => reveal(root));
    timer = setInterval(() => void load(), POLL_MS);
  });
  onDestroy(() => clearInterval(timer));
</script>

<div class="movie-screen flat" bind:this={root}>
  <CrtHeader title={show.title} />
  <div class="body">
    <div class="left">
      <div class="seasons" data-reveal>
        {#each seasons as n (n)}
          <button class:active={n === season} onclick={() => selectSeason(n)}>S{n}</button>
        {/each}
      </div>
      <div class="episodes">
        {#if !view && !failed}
          <div class="msg">{t('series.loading')}</div>
        {:else if failed && !episodes.length}
          <div class="msg">{t('series.unavailable')}</div>
        {:else if !episodes.length}
          <div class="msg">{t('series.no_episodes')}</div>
        {/if}
        {#each episodes as e (e.episode)}
          {@const st = stateOf(e)}
          {@const seen = st === 'ready' && e.watched}
          <button
            class="ep {st}"
            class:watched={seen}
            class:converting={st === 'downloading' && e.phase === 'transcoding'}
            class:active={e.episode === current?.episode}
            onclick={() => selectEpisode(e.episode)}
          >
            <span class="ep-state">{st === 'downloading' ? `${Math.round(e.progress * 100)}%` : ICONS[seen ? 'watched' : st]}</span>
            <span class="ep-num">E{String(e.episode).padStart(2, '0')}</span>
            <span class="ep-title">{e.title ?? ''}</span>
          </button>
        {/each}
      </div>
    </div>

    <div class="detail" class:empty-detail={!current} bind:this={detail}>
      {#if !current}
        {t('series.select')}
      {:else}
        {@const st = stateOf(current)}
        {@const seen = st === 'ready' && current.watched}
        <Poster src={current.still} width={190} ratio={16 / 9} />
        <div class="d-num">{episodeCode(season, current.episode)}</div>
        <div class="d-title">{current.title ?? ''}</div>
        {#if st === 'downloading'}
          {@const conv = current.phase === 'transcoding'}
          <div class="d-state {conv ? 'converting' : 'downloading'}">{phaseLabel(current)}</div>
          <Bar ratio={current.progress} phase={conv ? 'convert' : 'download'} height={14} />
        {:else if st === 'ready'}
          <div class="d-state {seen ? 'watched' : 'ready'}">
            {ICONS[seen ? 'watched' : 'ready']} {t(`series.state.${seen ? 'watched' : 'ready'}`)}
          </div>
          {#if current.duration}<div class="d-time">{formatTime(current.position)} / {formatTime(current.duration)}</div>{/if}
          <Bar ratio={current.duration ? current.position / current.duration : 0} height={14} />
        {:else}
          <div class="d-state {st}">{ICONS[st]} {t(`series.state.${st}`)}</div>
        {/if}
        <div class="d-actions">
          {#if st === 'ready'}
            <button class="crt-btn primary" onclick={() => tv.playEpisode(show.id, season, current.episode)}>▶ {t('lib.play')}</button>
          {:else if st !== 'downloading' && library.features.series}
            <button class="crt-btn" onclick={() => download('episode', current.episode)}>{t('series.dl_episode')}</button>
          {/if}
          {#if st === 'ready' || st === 'error'}
            <button class="crt-btn danger" class:active={confirmEp === current.episode} onclick={() => deleteEpisode(current)}>
              {confirmEp === current.episode ? t('lib.confirm') : t('lib.delete')}
            </button>
          {/if}
        </div>
        {#if current.overview}<div class="overview">{current.overview}</div>{/if}
      {/if}
    </div>
  </div>

  {#if notice}<div class="notice">{notice}</div>{/if}
  <div class="season-actions" data-reveal>
    {#if library.features.series}
      <button class="crt-btn" onclick={() => download('season')}>{t('series.dl_season')}</button>
    {/if}
    <button class="crt-btn danger" class:active={confirmSeason} onclick={deleteSeason}>
      {confirmSeason ? t('lib.confirm') : t('series.del_season')}
    </button>
  </div>

  <LibraryFooter>
    {#snippet actions()}
      <button class="navbtn" onclick={() => tv.goLibrary(show.id)}>[{t('nav.back')}]</button>
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
    flex: 1 1 58%;
    display: flex;
    flex-direction: column;
    min-height: 0;
    border-right: 3px solid var(--crt-border);
  }
  .seasons {
    display: flex;
    gap: 4px;
    padding: 6px 8px 4px var(--safe-x);
    overflow-x: auto;
    flex: 0 0 auto;
  }
  .seasons button {
    flex: 0 0 auto;
    padding: 3px 9px;
    font-size: var(--fs-m);
    color: var(--crt-dim);
    border: 1.3px solid var(--crt-divider);
    text-shadow: var(--crt-shadow);
  }
  .seasons button.active {
    color: var(--crt-accent-ink);
    background: var(--crt-accent);
    border-color: var(--crt-accent);
    text-shadow: none;
  }
  .episodes {
    flex: 1;
    overflow-y: auto;
    padding: 2px 8px 6px var(--safe-x);
  }
  .msg {
    padding: 20px 4px;
    color: var(--crt-dim);
    font-size: var(--fs-m);
  }
  .ep {
    width: 100%;
    display: flex;
    align-items: center;
    padding: 5px 6px;
    font-size: var(--fs-m);
    text-align: left;
    border-bottom: 2px solid var(--crt-divider);
  }
  .ep-state {
    flex: 0 0 44px;
  }
  .ep-num {
    flex: 0 0 52px;
    color: var(--crt-dim);
  }
  .ep-title {
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .ep.ready .ep-state {
    color: var(--crt-f1);
  }
  .ep.downloading {
    color: var(--crt-dim);
  }
  .ep.downloading .ep-state {
    color: var(--crt-f3);
  }
  .ep.converting .ep-state {
    color: var(--crt-f1);
  }
  .ep.watched .ep-state,
  .ep.watched .ep-title,
  .ep.missing .ep-title {
    color: var(--crt-dim);
  }
  .ep.missing .ep-state {
    color: var(--crt-accent);
  }
  .ep.error .ep-state {
    color: var(--crt-alert);
  }
  .ep.active,
  .ep.active span {
    background: var(--crt-accent);
    color: var(--crt-accent-ink) !important;
    text-shadow: none;
  }
  .detail {
    flex: 1 1 42%;
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 10px var(--safe-x) 8px 14px;
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
  .d-num {
    margin-top: 4px;
    color: var(--crt-dim);
    font-size: var(--fs-sm);
  }
  .d-title {
    color: var(--crt-accent);
    font-size: var(--fs-l);
  }
  .d-state {
    font-size: var(--fs-sm);
  }
  .d-state.ready {
    color: var(--crt-f1);
  }
  .d-state.watched {
    color: var(--crt-dim);
  }
  .d-state.downloading {
    color: var(--crt-f3);
  }
  .d-state.converting {
    color: var(--crt-f1);
  }
  .d-state.missing {
    color: var(--crt-accent);
  }
  .d-state.error {
    color: var(--crt-alert);
  }
  .d-time {
    color: var(--crt-dim);
    font-size: var(--fs-s);
  }
  .d-actions {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-top: 5px;
  }
  .d-actions .crt-btn {
    width: 100%;
    text-align: center;
    font-size: var(--fs-m);
  }
  .overview {
    margin-top: 6px;
    font-size: var(--fs-sm);
    line-height: 1.35;
  }
  .notice {
    padding: 4px var(--safe-x);
    font-size: var(--fs-sm);
    color: var(--crt-f2);
    border-top: 2px solid var(--crt-divider);
  }
  .season-actions {
    display: flex;
    gap: 8px;
    padding: 6px var(--safe-x);
    border-top: 2px solid var(--crt-divider);
  }
  .season-actions .crt-btn {
    flex: 1 1 0;
    text-align: center;
    font-size: var(--fs-m);
  }
</style>
