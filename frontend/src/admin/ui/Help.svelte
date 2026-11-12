<!--
  An inline "where do I find this?" link that unfolds a help note under a
  field. Hidden until asked for.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import type { Snippet } from 'svelte';

  let { label, children }: { label: string; children: Snippet } = $props();
  let open = $state(false);
</script>

<div class="help">
  <button class="link" aria-expanded={open} onclick={() => (open = !open)}>
    <Glyph name={open ? 'caret-down' : 'caret-right'} /> {label}
  </button>
  {#if open}
    <div class="note">{@render children()}</div>
  {/if}
</div>

<style>
  .help {
    margin: -6px 0 12px;
  }
  .note {
    margin-top: 6px;
    padding: 10px 12px;
    background: var(--panel);
    border: 2px solid var(--ink);
    font-size: 14px;
  }
  .note :global(p) {
    margin: 0 0 8px;
  }
  .note :global(p:last-child),
  .note :global(ol:last-child) {
    margin-bottom: 0;
  }
  .note :global(ol),
  .note :global(ul) {
    margin: 0 0 8px;
    padding-left: 20px;
  }
  .note :global(code) {
    padding: 0 3px;
    background: var(--field);
    border: 1px solid var(--lo);
  }
</style>
