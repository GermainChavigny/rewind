<!--
  A secret field (API key, password). The server sends stored secrets masked;
  the field then shows empty with a "saved" hint, and sends the mask back
  unless something new is typed (the server keeps the stored value).
-->
<script lang="ts">
  import { untrack } from 'svelte';

  const MASK = '********';

  let {
    value = $bindable(),
    label,
    password = false,
    placeholder = '',
  }: { value: string; label: string; password?: boolean; placeholder?: string } = $props();

  // Whether a value was stored when the field appeared (it stays so until replaced).
  const wasSaved = untrack(() => value === MASK);
  let text = $state('');
  const saved = $derived(wasSaved && text === '');

  function onInput(e: Event & { currentTarget: HTMLInputElement }) {
    if (!wasSaved) {
      value = e.currentTarget.value;
      return;
    }
    text = e.currentTarget.value;
    value = text || MASK; // cleared again: keep the stored secret
  }
</script>

<label>
  <span>{label}{#if saved}<em> · enregistrée ✓</em>{/if}</span>
  <input
    type={password ? 'password' : 'text'}
    value={wasSaved ? text : value}
    oninput={onInput}
    placeholder={saved ? 'Tapez pour remplacer' : placeholder}
    autocapitalize="off"
    autocomplete="off"
    spellcheck="false"
  />
</label>

<style>
  em {
    font-style: normal;
    color: var(--ok);
    text-transform: none;
  }
</style>
