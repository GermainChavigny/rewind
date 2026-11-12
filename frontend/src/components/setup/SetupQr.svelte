<!--
  Settings QR code: scanning it opens the settings page on the phone. Opened
  from the welcome screen (corner button or →), and by itself on the first
  start, when nothing is set up yet and the remote cannot be used. ← closes it.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../../lib/api';
  import { t } from '../../lib/i18n';
  import { tv } from '../../lib/tv.svelte';
  import Brand from '../Brand.svelte';
  import Glyph from '../Glyph.svelte';
  import QrCode from './QrCode.svelte';

  let url = $state<string | null>(null);
  let lan = $state(true);

  onMount(async () => {
    try {
      ({ url, lan } = await api.adminUrl());
    } catch {
      url = `${location.origin}/admin/`;
    }
  });
</script>

<div class="setup" role="presentation" onclick={(e) => e.target === e.currentTarget && tv.closeOverlay()}>
  <div class="panel">
    <div class="brand"><Brand size={34} /></div>
    <h1>{tv.firstRun ? t('setup.welcome') : t('setup.title')}</h1>
    <div class="body">
      <div class="qr">
        {#if url}<QrCode text={url} size={176} />{/if}
      </div>
      <div class="text">
        <p>{tv.firstRun ? t('setup.first_run') : t('setup.scan')}</p>
        {#if url}<p class="url">{url.replace(/^https?:\/\//, '')}</p>{/if}
        {#if !lan}<p class="warn">{t('setup.no_network')}</p>{/if}
      </div>
    </div>
    <button class="close" onclick={() => tv.closeOverlay()}>
      <Glyph name="left" size="14px" />
      {t('setup.close')}
    </button>
  </div>
</div>

<style>
  .setup {
    position: absolute;
    inset: 0;
    z-index: 45;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.55);
    pointer-events: auto;
  }
  .panel {
    width: 560px;
    padding: 18px 24px 14px;
    background: var(--crt-bg);
    border: 2px solid var(--crt-border);
    box-shadow: 6px 6px 0 #000;
    text-shadow: var(--crt-shadow);
  }
  .brand {
    display: flex;
    justify-content: center;
    text-shadow: none;
  }
  h1 {
    margin: 14px 0 12px;
    text-align: center;
    font-size: var(--fs-xl);
    font-weight: normal;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--crt-accent);
  }
  .body {
    display: flex;
    gap: 20px;
    align-items: center;
  }
  .qr {
    flex: 0 0 auto;
    box-sizing: content-box;
    width: 176px;
    height: 176px;
    border: 3px solid #fff;
    background: #fff;
  }
  .qr :global(svg) {
    display: block;
  }
  .text p {
    margin: 0 0 10px;
    font-size: var(--fs-m);
    line-height: 1.3;
  }
  .url {
    color: var(--crt-f3);
    font-size: var(--fs-s) !important;
    word-break: break-all;
  }
  .warn {
    color: var(--crt-alert);
  }
  .close {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 12px auto 0;
    padding: 4px 10px;
    font-size: var(--fs-s);
    text-transform: uppercase;
    color: var(--crt-dim);
    --cur: hand;
  }
  .close:hover {
    color: var(--crt-accent);
  }
</style>
