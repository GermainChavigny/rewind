<!--
  Compact multiple choice: the chosen items as removable tags, and a field
  that suggests the others as you type (accents and case ignored). Enter
  picks the first suggestion.
-->
<script lang="ts">
  import { fold } from '../helpers';

  let {
    value = $bindable(),
    options,
    max = Infinity,
    placeholder = 'Ajouter…',
    label,
  }: {
    value: string[];
    options: { id: string; name: string }[];
    max?: number;
    placeholder?: string;
    label: string;
  } = $props();

  let query = $state('');
  let open = $state(false);
  const nameOf = (id: string) => options.find((o) => o.id === id)?.name ?? id;
  const full = $derived(value.length >= max);
  const suggestions = $derived.by(() => {
    const q = fold(query.trim());
    return options
      .filter((o) => !value.includes(o.id))
      .filter((o) => !q || fold(o.name).includes(q) || o.id === q)
      .sort((a, b) => Number(!fold(a.name).startsWith(q)) - Number(!fold(b.name).startsWith(q)))
      .slice(0, 6);
  });

  function add(id: string) {
    if (full || value.includes(id)) return;
    value = [...value, id];
    query = '';
  }

  function remove(id: string) {
    value = value.filter((v) => v !== id);
  }

  function onkeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (suggestions[0]) add(suggestions[0].id);
    } else if (e.key === 'Backspace' && !query && value.length) {
      remove(value[value.length - 1]);
    } else if (e.key === 'Escape') {
      open = false;
    }
  }
</script>

<div class="picker">
  {#if value.length}
    <ul class="tags" aria-label={label}>
      {#each value as id (id)}
        <li class="tag">
          {nameOf(id)}
          <button class="x" onclick={() => remove(id)} aria-label="Retirer {nameOf(id)}">✕</button>
        </li>
      {/each}
    </ul>
  {/if}
  {#if !full}
    <div class="field">
      <input
        bind:value={query}
        {placeholder}
        aria-label={label}
        autocomplete="off"
        autocapitalize="off"
        spellcheck="false"
        onfocus={() => (open = true)}
        onblur={() => setTimeout(() => (open = false), 150)}
        oninput={() => (open = true)}
        {onkeydown}
      />
      {#if open && suggestions.length}
        <ul class="menu" role="listbox">
          {#each suggestions as o (o.id)}
            <li>
              <button role="option" aria-selected="false" onmousedown={(e) => e.preventDefault()} onclick={() => add(o.id)}>
                {o.name}
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</div>

<style>
  .picker {
    margin-bottom: 8px;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 0 8px;
    padding: 0;
    list-style: none;
  }
  .tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0 0 0 10px;
    font: 15px/1 var(--cond);
    letter-spacing: 0.03em;
    color: var(--sel-ink);
    background: var(--sel);
    border: 2px solid var(--ink);
  }
  .x {
    min-height: 34px;
    padding: 0 9px;
    font: 13px/1 Verdana, sans-serif;
    color: var(--sel-ink);
    background: none;
    border: 0;
    border-left: 2px solid var(--ink);
    border-radius: 0;
    box-shadow: none;
  }
  .field {
    position: relative;
  }
  .menu {
    position: absolute;
    left: 0;
    right: 0;
    top: 100%;
    z-index: 5;
    margin: 2px 0 0;
    padding: 0;
    list-style: none;
    background: var(--field);
    border: 2px solid var(--ink);
    box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.4);
  }
  .menu button {
    display: block;
    width: 100%;
    min-height: 40px;
    text-align: left;
    font: 15px Verdana, Geneva, sans-serif;
    background: none;
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }
  .menu li + li button {
    border-top: 1px solid #d6d6cf;
  }
  .menu button:hover,
  .menu button:focus {
    background: var(--sel);
    color: var(--sel-ink);
  }
</style>
