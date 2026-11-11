<!--
  Layers, bottom to top:
    video (full screen: intro, YouTube, movies — 16:9 stays full screen)
    stage (4:3 UI: channel grid, screens, technical difficulties)
    darkness veil (full screen)
    stage (OSDs stay readable above the veil)
    retro cursor
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import AlarmOsd from './components/AlarmOsd.svelte';
  import AlarmScreen from './components/AlarmScreen.svelte';
  import ChannelGrid from './components/ChannelGrid.svelte';
  import Difficulty from './components/Difficulty.svelte';
  import RetroCursor from './components/RetroCursor.svelte';
  import Stage from './components/Stage.svelte';
  import VolumeOsd from './components/VolumeOsd.svelte';
  import WeatherPopup from './components/WeatherPopup.svelte';
  import AdvisorScreen from './components/library/AdvisorScreen.svelte';
  import KeyboardOverlay from './components/library/KeyboardOverlay.svelte';
  import LibraryScreen from './components/library/LibraryScreen.svelte';
  import NextEpisodeHud from './components/library/NextEpisodeHud.svelte';
  import PauseScreen from './components/library/PauseScreen.svelte';
  import ResultsScreen from './components/library/ResultsScreen.svelte';
  import SeriesScreen from './components/library/SeriesScreen.svelte';
  import SubtitleHud from './components/library/SubtitleHud.svelte';
  import { movie } from './lib/movie.svelte';
  import { blip, wakeAudio } from './lib/sound';
  import { tv } from './lib/tv.svelte';

  let youtube: HTMLElement;
  let video: HTMLVideoElement;

  onMount(() => {
    tv.attachYouTube(youtube);
    tv.attachMovie(video);
    void tv.init();
  });

  // The movie plays with nothing on top: the HUDs wake up on mouse moves.
  const bare = $derived(movie.active && !tv.screen && !tv.overlay);
  let awake = $state(false);
  let idle: ReturnType<typeof setTimeout>;
  function moved() {
    if (!bare || movie.paused) return;
    awake = true;
    clearTimeout(idle);
    idle = setTimeout(() => (awake = false), 3000);
  }

  function click(e: MouseEvent) {
    wakeAudio();
    if ((e.target as Element).closest('button')) blip('click');
  }
</script>

<svelte:window onkeydown={(e) => tv.onKey(e)} onclickcapture={click} onmousemove={moved} />

<div class="video">
  <div class="youtube"><div bind:this={youtube}></div></div>
  <video class="intro" class:hidden={!tv.intro} src="/video/intro.webm" autoplay loop muted playsinline></video>
  <!-- svelte-ignore a11y_media_has_caption (tracks are added by lib/movie) -->
  <video class="movie" class:hidden={!movie.active} class:crop={movie.fit === 'cover'} bind:this={video} playsinline></video>
  <!-- Mouse events over <video> (and its letterbox bars) are unreliable: catch them. -->
  {#if movie.active}<div class="mouse-catch"></div>{/if}
</div>

{#if tv.difficulty}<div class="blackout"></div>{/if}
<!-- Paused: dim the video (and YouTube's own pause overlay) behind the channel grid. -->
<div class="pause-dim" class:on={tv.paused}></div>

<Stage layer={10}>
  <ChannelGrid />
  {#if tv.difficulty}<Difficulty message={tv.difficulty} />{/if}
  {#if tv.screen === 'alarm'}<AlarmScreen />{/if}
  {#if tv.screen === 'library'}<LibraryScreen />{/if}
  {#if tv.screen === 'results'}<ResultsScreen />{/if}
  {#if tv.screen === 'series' && tv.show}{#key tv.show.id}<SeriesScreen />{/key}{/if}
  {#if tv.screen === 'advisor'}<AdvisorScreen />{/if}
  {#if bare && (movie.paused || movie.ended)}<PauseScreen />{/if}
  {#if bare}
    <SubtitleHud awake={awake && !movie.paused} />
    <NextEpisodeHud {awake} />
  {/if}
  {#if tv.overlay === 'keyboard'}<KeyboardOverlay />{/if}
  {#if tv.overlay === 'weather'}<WeatherPopup />{/if}
</Stage>

<div class="veil" style:opacity={tv.darkness}></div>

<Stage layer={60}>
  {#if tv.osd === 'volume'}<VolumeOsd />{/if}
  {#if tv.osd === 'alarm' || tv.ringing}<AlarmOsd />{/if}
</Stage>

<RetroCursor />

<style>
  .video,
  .youtube,
  .intro,
  .movie,
  .blackout,
  .veil {
    position: fixed;
    inset: 0;
  }
  .video {
    z-index: 1;
    background: #000;
  }
  .youtube {
    pointer-events: none; /* no YouTube hover UI: the remote drives playback */
  }
  .youtube :global(iframe) {
    width: 100%;
    height: 100%;
    border: 0;
  }
  .intro,
  .movie {
    width: 100%;
    height: 100%;
    object-fit: cover;
    background: #000;
  }
  .movie {
    object-fit: contain; /* 16:9 letterbox; "4:3" crops (cover) */
  }
  .movie.crop {
    object-fit: cover;
  }
  .mouse-catch {
    position: fixed;
    inset: 0;
  }
  .blackout {
    z-index: 5;
    background: #000;
  }
  .pause-dim {
    position: fixed;
    inset: 0;
    z-index: 4;
    background: #000;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
  }
  .pause-dim.on {
    opacity: 0.7;
  }
  .veil {
    z-index: 50;
    background: #000;
    pointer-events: none;
  }
</style>
