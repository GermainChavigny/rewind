<!-- Progress bar; `phase` colors it (download = cyan, convert = green, else amber). -->
<script lang="ts">
  let {
    ratio,
    phase = null,
    height = 12,
  }: { ratio: number; phase?: 'download' | 'convert' | null; height?: number } = $props();
  const pct = $derived(Math.round(Math.max(0, Math.min(1, ratio || 0)) * 100));
</script>

<span class="crt-bar {phase ?? ''}" style:height="{height}px"><i style:width="{pct}%"></i></span>
