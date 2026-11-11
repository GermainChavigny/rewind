<!--
  90s TV volume OSD (v1): "VOLUME" + a bar made only of characters — bright
  green "|" up to the level, "-" for the rest. No background.
-->
<script lang="ts">
  import { t } from '../lib/i18n';
  import { VOLUME_STEPS } from '../lib/levels';
  import { tv } from '../lib/tv.svelte';
</script>

<div class="osd">
  <div class="label">{t('volume')}</div>
  <div class="bar">{'|'.repeat(tv.volumeStep)}{'-'.repeat(VOLUME_STEPS - tv.volumeStep)}</div>
</div>

<style>
  .osd {
    position: absolute;
    left: 50%;
    bottom: 69px; /* v1: 12vh */
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    gap: 3px;
    color: var(--crt-f1);
    text-shadow: var(--crt-shadow);
  }
  .label {
    font-family: var(--crt-block);
    font-size: 30px;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  .bar {
    font-size: 35px;
    line-height: 1;
    letter-spacing: 2.5px;
    white-space: pre;
  }
</style>
