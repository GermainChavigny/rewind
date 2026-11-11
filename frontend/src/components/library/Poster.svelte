<!-- Poster in an amber frame; a missing image leaves the empty frame (v1 .no-poster). -->
<script lang="ts">
  let { src, width = 108, ratio = 2 / 3 }: { src: string | null; width?: number; ratio?: number } =
    $props();
  let broken = $state(false);
  $effect(() => {
    void src;
    broken = false;
  });
</script>

<div class="poster" style:width="{width}px" style:aspect-ratio={ratio}>
  {#if src && !broken}
    <img {src} alt="" draggable="false" onerror={() => (broken = true)} />
  {/if}
</div>

<style>
  .poster {
    flex: 0 0 auto;
    align-self: center;
    background: var(--crt-panel);
    border: 2.3px solid var(--crt-accent);
    overflow: hidden;
  }
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
</style>
