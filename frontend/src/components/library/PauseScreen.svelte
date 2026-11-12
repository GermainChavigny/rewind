<!--
  Shown while a movie is paused (v1 MovieControls): title, settings rows (each
  button cycles its values: format, audio language, subtitles), the clickable
  progress bar, [Resume]. Also shown at the end of the movie.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '../../lib/i18n';
  import { formatTime } from '../../lib/library.svelte';
  import { LANG_NAMES, movie } from '../../lib/movie.svelte';
  import { reveal } from '../../lib/sound';
  import LibraryFooter from './LibraryFooter.svelte';

  let root: HTMLElement;
  const ratio = $derived(movie.duration ? movie.time / movie.duration : 0);
  const audioLabel = $derived(movie.audioTracks.find((a) => a.index === movie.audioIndex)?.label ?? '—');

  function seek(e: MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    movie.seekRatio(Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)));
  }

  onMount(() => reveal(root));
</script>

<div class="movie-screen pause" bind:this={root}>
  <div class="head" data-reveal><span class="title">{movie.entry?.title ?? ''}</span></div>
  <div class="rows">
    <div class="row" data-reveal>
      <span class="label">{t('pause.format')}</span>
      <button class="crt-btn cycle" onclick={() => movie.setFit(movie.fit === 'contain' ? 'cover' : 'contain')}>
        {movie.fit === 'cover' ? '4:3' : '16:9'}
      </button>
    </div>
    {#if movie.audioTracks.length > 1}
      <div class="row" data-reveal>
        <span class="label">{t('pause.audio')}</span>
        <button class="crt-btn cycle" onclick={() => movie.cycleAudio()}>{audioLabel}</button>
      </div>
    {/if}
    {#if movie.subLangs.length}
      <div class="row" data-reveal>
        <span class="label">{t('pause.subtitles')}</span>
        <button class="crt-btn cycle" onclick={() => movie.cycleSubtitles()}>
          {LANG_NAMES[movie.subMode] ?? t('pause.none')}
        </button>
      </div>
    {/if}
  </div>
  <div class="seek" data-reveal>
    <span class="time">{formatTime(movie.time)} / {formatTime(movie.duration)}</span>
    <button class="crt-bar seekbar" aria-label="seek" onclick={seek}><i style:width="{ratio * 100}%"></i></button>
  </div>
  <LibraryFooter>
    {#snippet actions()}
      <button class="navbtn" onclick={() => movie.resume()}>[{t('pause.resume')}]</button>
    {/snippet}
  </LibraryFooter>
</div>

<style>
  .pause {
    z-index: 30;
    background: rgba(10, 23, 51, 0.94);
  }
  .head {
    padding: var(--safe-y) var(--safe-x) 30px;
  }
  .title {
    font-size: 23px;
    color: var(--crt-accent);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .rows {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 0 var(--safe-x);
  }
  .row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .label {
    flex: 0 0 216px;
    font-size: var(--fs-m);
    color: var(--crt-dim);
    text-transform: uppercase;
  }
  .cycle {
    min-width: 160px;
    text-align: center;
  }
  .seek {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 7px;
    padding: 0 var(--safe-x) var(--safe-y);
  }
  .time {
    font-size: var(--fs-m);
    text-align: center;
  }
  .seekbar {
    height: 32px;
    width: 100%;
  }
</style>
