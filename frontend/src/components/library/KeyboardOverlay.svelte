<!--
  On-screen keyboard (v1 VirtualKeyboard), driven by the cursor with big keys.
  Serves the search (with the Movies / Series switch) and the advisor's
  keywords. A real keyboard also types (letters, space, backspace, enter): the
  remote's keys keep their TV meaning. The text lives in `tv.kbText`, so the
  phone remote's keyboard can write it too.
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import { t } from '../../lib/i18n';
  import { library } from '../../lib/library.svelte';
  import { reveal } from '../../lib/sound';
  import { tv } from '../../lib/tv.svelte';
  import CrtHeader from '../CrtHeader.svelte';
  import LibraryFooter from './LibraryFooter.svelte';

  const ROWS = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['a', 'z', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['q', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm'],
    ['w', 'x', 'c', 'v', 'b', 'n'],
  ];

  const forAdvisor = tv.keyboardFor === 'advisor';
  let root: HTMLElement;
  const canSwitch = $derived(library.features.search && library.features.series);

  function type(text: string) {
    tv.setKeyboardText(text);
  }

  function submit() {
    tv.submitKeyboard();
  }

  function cancel() {
    tv.closeOverlay();
  }

  /** Physical keyboard: typing keys only. */
  function onkeydown(e: KeyboardEvent) {
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    if (/^[a-z0-9]$/i.test(e.key)) type(tv.kbText + e.key.toLowerCase());
    else if (e.key === ' ') type(tv.kbText + ' ');
    else if (e.key === 'Backspace') type(tv.kbText.slice(0, -1));
    else if (e.key === 'Enter') submit();
    else if (e.key === 'Escape') cancel();
    else return;
    e.preventDefault();
    e.stopImmediatePropagation();
  }

  onMount(() => reveal(root));
</script>

<svelte:window {onkeydown} />

<div class="movie-screen flat keyboard" bind:this={root}>
  <CrtHeader title={forAdvisor ? t('adv.title') : t('kb.search_title')} />
  <div class="panel">
    <div class="top" data-reveal>
      <span class="prompt">{forAdvisor ? t('kb.advisor_prompt') : t('kb.search_prompt')}</span>
      {#if !forAdvisor && canSwitch}
        <button class="crt-btn kind" onclick={() => (tv.kbKind = tv.kbKind === 'series' ? 'movie' : 'series')}>
          {tv.kbKind === 'series' ? t('kb.series') : t('kb.movies')}
        </button>
      {/if}
    </div>
    <div class="display" data-reveal><span>{tv.kbText}</span><span class="caret">|</span></div>
    {#each ROWS as row, i (i)}
      <div class="keys" data-reveal>
        {#each row as key (key)}
          <button class="key" onclick={() => type(tv.kbText + key)}>{key}</button>
        {/each}
      </div>
    {/each}
    <div class="keys actions" data-reveal>
      <button class="key" onclick={() => type(tv.kbText + ' ')}>{t('kb.space')}</button>
      <button class="key" onclick={() => type(tv.kbText.slice(0, -1))}>{t('kb.back')}</button>
      <button class="key" onclick={() => type('')}>{t('kb.clear')}</button>
      <button class="key submit" onclick={submit}>{forAdvisor ? t('kb.ok') : t('kb.search_submit')}</button>
    </div>
  </div>
  <LibraryFooter>
    {#snippet actions()}
      <button class="navbtn" onclick={cancel}>[{t('nav.cancel')}]</button>
    {/snippet}
  </LibraryFooter>
</div>

<style>
  .keyboard {
    z-index: 40;
  }
  .panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 8px var(--safe-x);
  }
  .top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 4px;
  }
  .prompt {
    font-size: var(--fs-m);
    color: var(--crt-dim);
    text-transform: uppercase;
  }
  .kind {
    font-size: 18px;
    padding: 3px 10px;
  }
  .display {
    background: var(--crt-panel-2);
    border: 1.3px solid var(--crt-border);
    color: #fff;
    font-size: var(--fs-xl);
    min-height: 40px;
    padding: 6px 12px;
    margin-bottom: 12px;
    white-space: nowrap;
    overflow: hidden;
  }
  .caret {
    color: var(--crt-accent);
    animation: blink 1s step-start infinite;
  }
  @keyframes blink {
    50% {
      opacity: 0;
    }
  }
  .keys {
    display: flex;
    gap: 6px;
    margin-bottom: 6px;
  }
  .key {
    flex: 0 0 calc((100% - 9 * 6px) / 10);
    padding: 11px 0;
    font-size: 23px;
    border: 1.3px solid var(--crt-border);
    background: var(--crt-panel);
    text-transform: uppercase;
    text-shadow: var(--crt-shadow);
  }
  .key:hover {
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    border-color: var(--crt-accent);
    text-shadow: none;
  }
  .actions {
    margin-top: 10px;
  }
  .actions .key {
    flex: 2 1 0;
    font-size: var(--fs-m);
  }
  .actions .submit {
    flex-grow: 3;
    background: var(--crt-accent);
    color: var(--crt-accent-ink);
    border-color: var(--crt-accent);
    text-shadow: none;
  }
</style>
