<!--
  Layers, bottom to top:
    video (full screen: intro, YouTube — 16:9 stays full screen)
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
  import { blip, wakeAudio } from './lib/sound';
  import { tv } from './lib/tv.svelte';

  let youtube: HTMLElement;

  onMount(() => {
    tv.attachYouTube(youtube);
    void tv.init();
  });

  function click(e: MouseEvent) {
    wakeAudio();
    if ((e.target as Element).closest('button')) blip('click');
  }
</script>

<svelte:window onkeydown={(e) => tv.onKey(e)} onclickcapture={click} />

<div class="video">
  <div class="youtube"><div bind:this={youtube}></div></div>
  <video class="intro" class:hidden={!tv.intro} src="/video/intro.webm" autoplay loop muted playsinline></video>
</div>

{#if tv.difficulty}<div class="blackout"></div>{/if}

<Stage layer={10}>
  <ChannelGrid />
  {#if tv.difficulty}<Difficulty message={tv.difficulty} />{/if}
  {#if tv.screen === 'alarm'}<AlarmScreen />{/if}
  {#if tv.screen === 'weather'}<WeatherPopup />{/if}
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
  .intro {
    width: 100%;
    height: 100%;
    object-fit: cover;
    background: #000;
  }
  .blackout {
    z-index: 5;
    background: #000;
  }
  .veil {
    z-index: 50;
    background: #000;
    pointer-events: none;
  }
</style>
