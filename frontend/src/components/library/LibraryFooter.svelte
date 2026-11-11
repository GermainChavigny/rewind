<!--
  Footer shared by the movie screens: [VIDÉOTHÈQUE] [RECHERCHE] [ADVISOR]
  shortcuts on the left (only the configured ones), screen actions on the right.
-->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { t } from '../../lib/i18n';
  import { library } from '../../lib/library.svelte';
  import { tv } from '../../lib/tv.svelte';
  import CrtFooter from '../CrtFooter.svelte';

  let { actions }: { actions?: Snippet } = $props();
</script>

<CrtFooter {actions}>
  {#snippet left()}
    <button class="navbtn" onclick={() => tv.goLibrary()}><span class="sq lib">■</span> {t('nav.library')}</button>
    {#if library.features.search || library.features.series}
      <button class="navbtn" onclick={() => tv.goSearch()}><span class="sq search">■</span> {t('nav.search')}</button>
    {/if}
    {#if library.features.advisor}
      <button class="navbtn" onclick={() => tv.goAdvisor()}><span class="sq adv">■</span> {t('nav.advisor')}</button>
    {/if}
  {/snippet}
</CrtFooter>

<style>
  .sq {
    font-size: 0.85em;
  }
  .lib {
    color: var(--crt-accent);
  }
  .search {
    color: var(--crt-f1);
  }
  .adv {
    color: var(--crt-f3);
  }
</style>
