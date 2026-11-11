<!-- Alarm bell (pixel-ish SVG, inherits currentColor). -->
<script lang="ts">
  let { size = 18 }: { size?: number } = $props();
</script>

<svg viewBox="0 0 16 16" width={size} height={size} fill="currentColor" aria-hidden="true">
  <path d="M7 1h2v1.2A4.5 4.5 0 0 1 12.5 6.6V10l1.5 2v1H2v-1l1.5-2V6.6A4.5 4.5 0 0 1 7 2.2z" />
  <path d="M6 14h4a2 2 0 0 1-4 0z" />
</svg>
