<!--
  Settings button in the corner of the welcome screen (intro video, or the
  channel grid of a paused channel). Click it, or press → on the remote:
  the settings QR code opens.
-->
<script lang="ts">
  import { t } from '../../lib/i18n';
  import { tv } from '../../lib/tv.svelte';
  import Glyph from '../Glyph.svelte';
</script>

<button class="corner" onclick={() => tv.openOverlay('setup')} aria-label={t('setup.open')}>
  <Glyph name="gear" size="26px" />
  <span class="hint"><Glyph name="right" size="14px" /></span>
</button>

<style>
  .corner {
    position: absolute;
    top: var(--safe-y);
    right: var(--safe-x);
    z-index: 20;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 7px;
    border: 1.3px solid var(--crt-border);
    background: rgba(0, 12, 46, 0.75);
    color: var(--crt-text);
    pointer-events: auto;
    --cur: hand;
    filter: drop-shadow(2px 2px 0 #000);
  }
  .corner:hover {
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    border-color: var(--crt-accent);
  }
  .hint {
    display: flex;
    opacity: 0.7;
  }
</style>
