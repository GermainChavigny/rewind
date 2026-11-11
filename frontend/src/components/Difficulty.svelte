<!--
  "TECHNICAL DIFFICULTIES — please stand by" card (used for every error), a
  nod to the broadcast cards of the 80s/90s: magenta-violet scanline stripes,
  chunky block title, script-like subtitle.
-->
<script lang="ts">
  import { t } from '../lib/i18n';

  let { message }: { message: string } = $props();
</script>

<div class="card">
  <div class="stripes"></div>
  <div class="text">
    <div class="title">{t('difficulties.title')}</div>
    <div class="standby">{t('difficulties.standby')}</div>
    <div class="message">{t(message)}</div>
  </div>
</div>

<style>
  .card {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: linear-gradient(#2a0a52, #8b1c8f 55%, #d23a9a);
  }
  .stripes {
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(
      to bottom,
      rgba(255, 255, 255, 0.16) 0 6px,
      rgba(0, 0, 0, 0) 6px 14px
    );
    mask-image: linear-gradient(to right, #000 0 30%, transparent 75%);
  }
  .text {
    position: relative;
    text-align: center;
    padding: 0 var(--safe-x);
  }
  .title {
    /* Chunky broadcast lettering with a stepped 3D extrusion (see ~/rewind-refs). */
    font-family: 'Arial Black', 'DejaVu Sans', 'Helvetica Neue', sans-serif;
    font-weight: 900;
    font-size: 54px;
    line-height: 0.92;
    letter-spacing: -2px;
    color: #fff;
    text-transform: uppercase;
    transform: scaleY(1.15);
    -webkit-font-smoothing: antialiased;
    text-shadow:
      1px 1px 0 #c9c3e8,
      2px 2px 0 #9a8fd0,
      3px 3px 0 #6a5aa8,
      4px 4px 0 #3d2a78,
      5px 5px 0 #2a0a52,
      7px 8px 0 rgba(0, 0, 0, 0.6);
  }
  .standby {
    margin-top: 22px;
    font-family: Georgia, 'DejaVu Serif', serif;
    font-style: italic;
    font-weight: bold;
    font-size: 40px;
    color: #fff;
    text-shadow: 3px 3px 0 #000;
  }
  .message {
    margin-top: 26px;
    font-size: var(--fs-m);
    color: var(--crt-text);
    text-transform: uppercase;
    text-shadow: var(--crt-shadow);
  }
</style>
