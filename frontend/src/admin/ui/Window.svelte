<!--
  A bevelled grey window with a striped title bar (early-90s desktop). An
  optional `help` snippet adds a [?] box in the title bar that unfolds an
  explanation at the top of the window.
-->
<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    title,
    help,
    lamp,
    children,
  }: {
    title: string;
    help?: Snippet;
    lamp?: 'on' | 'todo' | 'off';
    children: Snippet;
  } = $props();

  let open = $state(false);
</script>

<section class="window">
  <header>
    <span class="stripes"></span>
    <h2>
      {#if lamp}<span class="lamp" class:on={lamp === 'on'} class:todo={lamp === 'todo'}></span>{/if}
      {title}
    </h2>
    <span class="stripes"></span>
    {#if help}
      <button class="help" aria-expanded={open} aria-label="Aide" onclick={() => (open = !open)}>?</button>
    {/if}
  </header>
  {#if help && open}
    <div class="explain">
      {@render help()}
      <button class="link" onclick={() => (open = false)}>Compris</button>
    </div>
  {/if}
  <div class="body">{@render children()}</div>
</section>

<style>
  .window {
    margin: 0 0 14px;
    background: var(--win);
    border: 2px solid var(--ink);
    box-shadow:
      inset 2px 2px 0 var(--hi),
      inset -2px -2px 0 var(--lo),
      5px 5px 0 rgba(0, 0, 0, 0.45);
  }
  header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 6px 5px 8px;
    border-bottom: 2px solid var(--ink);
  }
  .stripes {
    flex: 1;
    min-width: 12px;
    height: 13px;
    background: repeating-linear-gradient(180deg, var(--ink) 0 2px, transparent 2px 4px);
    opacity: 0.55;
  }
  h2 {
    margin: 0;
    font: 19px/1.1 var(--cond);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 75%;
  }
  .help {
    min-height: 30px;
    width: 30px;
    padding: 0;
    font-size: 17px;
  }
  .explain {
    margin: 8px 8px 0;
    padding: 10px 12px;
    background: var(--panel);
    border: 2px solid var(--ink);
    font-size: 14px;
  }
  .explain :global(p) {
    margin: 0 0 8px;
  }
  .explain :global(ol),
  .explain :global(ul) {
    margin: 0 0 8px;
    padding-left: 20px;
  }
  .body {
    padding: 4px 12px 12px;
  }
</style>
