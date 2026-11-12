<!-- "21:07" and "11 NOV", from the shared 1 s clock (no year: room for the alarm). -->
<script lang="ts">
  import { t } from '../lib/i18n';
  import { tv } from '../lib/tv.svelte';

  let { part }: { part: 'time' | 'date' } = $props();
  const months = $derived(t('months').split(' '));
  const d = $derived(tv.now);
</script>

{#if part === 'time'}{String(d.getHours()).padStart(2, '0')}:{String(d.getMinutes()).padStart(2, '0')}{:else}{d.getDate()} {months[d.getMonth()]}{/if}
