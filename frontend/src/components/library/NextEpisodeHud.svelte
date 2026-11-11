<!--
  "Next episode" button (v1 NextEpisodeHud), bottom center, for an episode.
  Playing: appears on mouse move once the episode counts as watched. Paused or
  ended: always shown. Next ready → "▶ Next SxxEyy", else "☰ Episodes".
-->
<script lang="ts">
  import { t } from '../../lib/i18n';
  import { episodeCode } from '../../lib/library.svelte';
  import { movie } from '../../lib/movie.svelte';
  import { tv } from '../../lib/tv.svelte';

  let { awake }: { awake: boolean } = $props();
  let hovering = $state(false);
  const entry = $derived(movie.entry);
  const next = $derived(
    entry && movie.next?.kind === 'episode' && movie.next.parent_id === entry.parent_id ? movie.next : null,
  );
  const shown = $derived(
    entry?.kind === 'episode' && (movie.paused || movie.ended || ((awake || hovering) && movie.watchedNow)),
  );
</script>

{#if shown}
  <div class="hud" role="group" onpointerenter={() => (hovering = true)} onpointerleave={() => (hovering = false)}>
    {#if next}
      <button class="crt-btn primary" onclick={() => movie.playNext()}>
        {t('lib.next_ep', { code: episodeCode(next.season, next.episode) })}
      </button>
    {:else}
      <button class="crt-btn primary" onclick={() => tv.episodesOfCurrent()}>{t('next.episodes')}</button>
    {/if}
  </div>
{/if}

<style>
  .hud {
    position: absolute;
    z-index: 45;
    left: 50%;
    bottom: 64px;
    transform: translateX(-50%);
    pointer-events: auto;
  }
  .crt-btn {
    font-size: 22px;
    padding: 9px 22px;
    white-space: nowrap;
  }
</style>
