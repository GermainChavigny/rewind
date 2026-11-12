<!-- Segmented progress bar ("Connecting…" style). `value` from 0 to 1. -->
<script lang="ts">
  let { value, segments = 20 }: { value: number; segments?: number } = $props();
  const filled = $derived(Math.round(Math.max(0, Math.min(1, value)) * segments));
</script>

<div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(value * 100)}>
  {#each Array(segments) as _, i (i)}
    <span class:on={i < filled}></span>
  {/each}
</div>

<style>
  .bar {
    display: flex;
    gap: 2px;
    height: 22px;
    padding: 3px;
    background: var(--field);
    border: 2px solid var(--ink);
    box-shadow: inset 2px 2px 0 #9a9a92;
  }
  span {
    flex: 1;
  }
  span.on {
    background: var(--sel);
  }
</style>
