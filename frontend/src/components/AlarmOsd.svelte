<!--
  Alarm OSD, in the style of the volume OSD: shown when the alarm is set with
  the remote (and blinking while it rings). Click it to open the alarm screen.
-->
<script lang="ts">
  import { t } from '../lib/i18n';
  import { tv } from '../lib/tv.svelte';
  import BellIcon from './BellIcon.svelte';
</script>

<button class="osd" class:off={!tv.alarm.enabled} class:ringing={tv.ringing} onclick={() => tv.openScreen('alarm')}>
  <div class="label"><BellIcon size={26} /> {t('alarm')}</div>
  <div class="value">
    {#if tv.ringing}{t('alarm.ringing')}{:else}{tv.alarm.time}
      <span class="state">{tv.alarm.enabled ? t('alarm.on') : t('alarm.off')}</span>{/if}
  </div>
</button>

<style>
  .osd {
    position: absolute;
    left: 50%;
    bottom: 69px;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
    color: var(--crt-f1);
    text-shadow: var(--crt-shadow);
    text-align: left;
  }
  .osd.off {
    color: var(--crt-dim);
  }
  .label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--crt-block);
    font-size: 30px;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  .label :global(svg) {
    filter: drop-shadow(2px 2px 0 #000);
  }
  .value {
    font-size: 35px;
    line-height: 1;
    letter-spacing: 2.5px;
  }
  .state {
    margin-left: 12px;
    font-size: var(--fs-l);
    text-transform: uppercase;
  }
  .ringing {
    animation: blink 1s steps(1) infinite;
  }
  @keyframes blink {
    50% {
      opacity: 0;
    }
  }
</style>
