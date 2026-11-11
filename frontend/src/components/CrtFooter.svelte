<!-- Retro footer bar: shortcuts on the left, screen actions ([LABEL]) on the right. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  let { left, actions }: { left?: Snippet; actions?: Snippet } = $props();
</script>

<footer data-reveal>
  <span class="left">{#if left}{@render left()}{/if}</span>
  <span class="actions">{#if actions}{@render actions()}{/if}</span>
</footer>

<style>
  footer {
    display: flex;
    align-items: center;
    gap: 0 20px;
    padding: 12px var(--safe-x) var(--safe-y);
    background: var(--crt-bar-bg);
    border-top: 2px solid var(--crt-border);
    font-size: var(--fs-m);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--crt-dim);
    flex: 0 0 auto;
  }
  .left,
  .actions {
    display: flex;
    gap: 0 12px;
  }
  .actions {
    margin-left: auto;
  }
  footer :global(.navbtn) {
    color: var(--crt-text);
    text-transform: uppercase;
  }
  footer :global(.navbtn:hover) {
    text-decoration: underline;
  }
</style>
