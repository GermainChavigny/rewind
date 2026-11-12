<!--
  "End of broadcast" card, shown while the computer turns off (power key of
  the phone remote): colour bars, the brand, a goodnight — like the closing
  card of an 80s channel before the snow.
-->
<script lang="ts">
  import { t } from '../../lib/i18n';
  import Brand from '../Brand.svelte';

  const BARS = ['#c0c0c0', '#c0c000', '#00c0c0', '#00c000', '#c000c0', '#c00000', '#0000c0'];
</script>

<div class="card">
  <div class="bars">
    {#each BARS as color (color)}<span style:background={color}></span>{/each}
  </div>
  <div class="label">
    <Brand size={36} />
    <div class="end">{t('shutdown.title')}</div>
    <div class="night">{t('shutdown.goodnight')}</div>
  </div>
</div>

<style>
  .card {
    position: absolute;
    inset: 0;
    background: #000;
    pointer-events: auto;
  }
  .bars {
    position: absolute;
    inset: 0 0 34% 0;
    display: flex;
  }
  .bars span {
    flex: 1;
  }
  .label {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 34%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: #000;
  }
  .end {
    font-size: var(--fs-xl);
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #fff;
    text-shadow: var(--crt-shadow);
  }
  .night {
    font-size: var(--fs-m);
    color: var(--crt-dim);
  }
</style>
