<!--
  Movies & series: one window per service (film info, subtitles, torrent
  search, Movie Advisor), each with a lamp and a "where do I find my key?" note.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { t } from '../../lib/i18n';
  import { adminApi, type Cfg } from '../api';
  import {
    languageName,
    MAX_SUBTITLE_LANGUAGES,
    phoneUrl,
    presetOf,
    PROVIDERS,
    type ProviderPreset,
    SUBTITLE_CODES,
  } from '../helpers';
  import TagPicker from '../ui/TagPicker.svelte';
  import TestButton from '../ui/TestButton.svelte';
  import Help from '../ui/Help.svelte';
  import Secret from '../ui/Secret.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  const has = (v: string | null | undefined) => !!v && v.length > 0;
  const lampOf = (ok: boolean) => (ok ? 'on' : 'todo') as 'on' | 'todo';

  function addIndexer() {
    cfg.indexers.push({
      name: 'Jackett', url: 'http://127.0.0.1:9117', api_key: '', indexer: 'all',
      min_seeders: 1, max_size_gb: 6, timeout_s: 30, systemd_unit: 'jackett.service',
    }); // prettier-ignore
  }

  function addAdvisor(pr: ProviderPreset) {
    cfg.advisor.push({ name: pr.name, kind: pr.kind, base_url: pr.base_url, model: pr.model, api_key: '', json_mode: true });
  }

  function addCustom() {
    cfg.advisor.push({ name: t('admin.lib.my_ai'), kind: 'openai', base_url: 'https://', model: '', api_key: '', json_mode: true });
  }

  let models = $state<Record<number, string[]>>({});
  let modelError = $state<Record<number, string>>({});
  let loadingModels = $state<number | null>(null);

  async function loadModels(i: number) {
    loadingModels = i;
    modelError[i] = '';
    try {
      models[i] = await adminApi.models(i, cfg);
      if (!models[i].length) modelError[i] = t('admin.lib.no_models');
    } catch {
      modelError[i] = t('admin.lib.models_error');
    } finally {
      loadingModels = null;
    }
  }

  // Subtitle languages kept with each film (backend SUBTITLE_LANGUAGES), by name.
  const SUB_LANGS = $derived(
    SUBTITLE_CODES.map((id) => ({ id, name: languageName(id, cfg.general.language) })).sort((a, b) =>
      a.name.localeCompare(b.name, cfg.general.language),
    ),
  );
  // Empty list = the interface language (backend Config.subtitle_languages).
  const uiLanguage = $derived(cfg.general.language.split('-')[0].toLowerCase());

  function slots(delta: number) {
    cfg.library.download_slots = Math.max(1, Math.min(10, cfg.library.download_slots + delta));
  }
</script>

<Window title={t('lib.title')}>
  {#snippet help()}
    <p>{t('admin.lib.help1')}</p>
    <p>{t('admin.lib.help2')}</p>
  {/snippet}
  <label class="check">
    <input type="checkbox" bind:checked={cfg.library.enabled} />
    <span>{t('admin.lib.enable')}</span>
  </label>
  {#if cfg.library.enabled}
    <span class="label">{t('admin.lib.slots')}</span>
    <div class="stepper">
      <button onclick={() => slots(-1)} aria-label={t('admin.lib.less')}>−</button>
      <strong>{cfg.library.download_slots}</strong>
      <button onclick={() => slots(1)} aria-label={t('admin.lib.more')}>+</button>
    </div>
    <label class="check">
      <input type="checkbox" bind:checked={cfg.library.announce_ready} />
      <span>{t('admin.lib.announce')}</span>
    </label>
  {/if}
</Window>

{#if cfg.library.enabled}
  <Window title={t('admin.lib.tmdb_title')} lamp={lampOf(has(cfg.tmdb.api_key))}>
    {#snippet help()}
      <p>{t('admin.lib.tmdb_help')}</p>
    {/snippet}
    <Secret bind:value={cfg.tmdb.api_key} label={t('admin.lib.tmdb_key')} placeholder={t('admin.lib.tmdb_placeholder')} />
    <Help label={t('admin.lib.tmdb_where')}>
      <ol>
        <li>{@html t('admin.lib.tmdb_where1')}</li>
        <li>{@html t('admin.lib.tmdb_where2')}</li>
        <li>{@html t('admin.lib.tmdb_where3')}</li>
      </ol>
    </Help>
    <TestButton run={() => adminApi.check('tmdb', cfg)} />
  </Window>

  <Window title={t('pause.subtitles')} lamp={lampOf(has(cfg.opensubtitles.api_key))}>
    {#snippet help()}
      <p>{t('admin.lib.subs_help')}</p>
    {/snippet}
    <span class="label">{t('admin.lib.subs_langs')}</span>
    <TagPicker
      bind:value={cfg.opensubtitles.languages}
      options={SUB_LANGS}
      max={MAX_SUBTITLE_LANGUAGES}
      label={t('admin.lib.subs_langs')}
      placeholder={t('admin.lib.subs_add')}
    />
    <p class="muted">
      {#if cfg.opensubtitles.languages.length}
        {t('admin.lib.subs_kept', { max: MAX_SUBTITLE_LANGUAGES })}
      {:else if SUBTITLE_CODES.includes(uiLanguage)}
        {t('admin.lib.subs_ui', { name: languageName(uiLanguage, cfg.general.language) })}
      {:else}
        {t('admin.lib.subs_none')}
      {/if}
    </p>
    <Secret bind:value={cfg.opensubtitles.api_key} label={t('admin.lib.api_key')} />
    <Help label={t('admin.lib.os_where')}>
      <ol>
        <li>{@html t('admin.lib.os_where1')}</li>
        <li>{@html t('admin.lib.os_where2')}</li>
        <li>{@html t('admin.lib.os_where3')}</li>
      </ol>
      <p>{t('admin.lib.os_account')}</p>
    </Help>
    <label><span>{t('admin.lib.username')}</span><input bind:value={cfg.opensubtitles.username} autocapitalize="off" autocomplete="off" /></label>
    <Secret bind:value={cfg.opensubtitles.password} label={t('admin.lib.password')} password />
    <TestButton run={() => adminApi.check('opensubtitles', cfg)} />
  </Window>

  <Window title={t('admin.lib.search_title')} lamp={lampOf(cfg.indexers.some((i: Cfg) => has(i.api_key)))}>
    {#snippet help()}
      <p>{@html t('admin.lib.jackett_help')}</p>
    {/snippet}
    {#each cfg.indexers as ix, i (i)}
      <div class="item">
        <label><span>{t('admin.lib.name')}</span><input bind:value={ix.name} /></label>
        <label><span>{t('admin.lib.jackett_url')}</span><input bind:value={ix.url} autocapitalize="off" inputmode="url" /></label>
        <Secret bind:value={ix.api_key} label={t('admin.lib.jackett_key')} />
        <a class="open-jackett" href={phoneUrl(ix.url, location.hostname)} target="_blank" rel="noreferrer">
          <Glyph name="external" /> {t('admin.lib.jackett_open')}
        </a>
        <Help label={t('admin.lib.sites')}>
          <ol>
            <li>{@html t('admin.lib.sites1')}</li>
            <li>{@html t('admin.lib.sites2')}</li>
            <li>{@html t('admin.lib.sites3')}</li>
          </ol>
        </Help>
        <Help label={t('admin.lib.jkey_where')}>
          <ol>
            <li>
              {t('admin.lib.jkey_where1')}
              <a href={phoneUrl(ix.url, location.hostname)} target="_blank" rel="noreferrer">{phoneUrl(ix.url, location.hostname)}</a>
              {t('admin.lib.new_tab')}
            </li>
            <li>{@html t('admin.lib.jkey_where2')}</li>
            <li>{@html t('admin.lib.jkey_where3')}</li>
          </ol>
          <p>{@html t('admin.lib.jkey_note')}</p>
        </Help>
        <label><span>{t('admin.lib.unit')}</span><input bind:value={ix.systemd_unit} placeholder="jackett.service" autocapitalize="off" /></label>
        <Help label={t('admin.lib.what_for')}>
          <p>{@html t('admin.lib.unit_help')}</p>
        </Help>
        <TestButton run={() => adminApi.check('indexer', cfg, i)} />
        <button class="danger" onclick={() => cfg.indexers.splice(i, 1)}>{t('admin.lib.remove')}</button>
      </div>
    {/each}
    <button onclick={addIndexer}>+ {t('admin.lib.add_jackett')}</button>
  </Window>

  <Window title="Movie Advisor" lamp={lampOf(cfg.advisor.some((p: Cfg) => has(p.api_key) || !presetOf(p)?.keyUrl))}>
    {#snippet help()}
      <p>{t('admin.lib.adv_help1')}</p>
      <p>{@html t('admin.lib.adv_help2')}</p>
    {/snippet}
    {#each cfg.advisor as p, i (i)}
      {@const preset = presetOf(p)}
      <div class="item">
        <div class="row">
          <strong class="grow">{i + 1}. {p.name}</strong>
          <button class="danger" onclick={() => cfg.advisor.splice(i, 1)}>{t('admin.lib.remove')}</button>
        </div>
        {#if preset}<p class="muted">{t(preset.note)}</p>{/if}
        {#if !preset || preset.keyUrl}
          <Secret bind:value={p.api_key} label={t('admin.lib.api_key')} />
        {/if}
        {#if preset?.keyUrl}
          <Help label={t('admin.lib.key_where', { name: preset.name })}>
            <ol>
              <li>{t('admin.lib.key_where1a')} <a href={preset.keyUrl} target="_blank" rel="noreferrer">{preset.keyUrl.replace('https://', '')}</a> {t('admin.lib.key_where1b')}</li>
              <li>{t('admin.lib.key_where2')}</li>
              <li>{@html t('admin.lib.key_where3')}</li>
            </ol>
          </Help>
        {:else if preset}
          <Help label={t('admin.lib.ollama')}>
            <p>{@html t('admin.lib.ollama_help')}</p>
          </Help>
        {/if}
        {#if !preset}
          <label><span>{t('admin.lib.api_url')}</span><input bind:value={p.base_url} autocapitalize="off" inputmode="url" /></label>
        {/if}
        <label>
          <span>{t('admin.lib.model')}</span>
          {#if models[i]?.length}
            <select bind:value={p.model}>
              {#if !models[i].includes(p.model)}<option value={p.model}>{p.model}</option>{/if}
              {#each models[i] as m (m)}<option value={m}>{m}</option>{/each}
            </select>
          {:else}
            <input bind:value={p.model} autocapitalize="off" />
          {/if}
        </label>
        <div class="row">
          <button onclick={() => loadModels(i)} disabled={loadingModels === i}>
            {#if loadingModels === i}{t('series.loading')}{:else}<Glyph name="refresh" /> {t('admin.lib.models')}{/if}
          </button>
          {#if modelError[i]}<span class="bad">{modelError[i]}</span>{/if}
        </div>
        <TestButton run={() => adminApi.check('advisor', cfg, i)} />
      </div>
    {/each}
    <span class="label">{t('admin.lib.add_provider')}</span>
    <div class="presets">
      {#each PROVIDERS as pr (pr.id)}
        <button onclick={() => addAdvisor(pr)}><strong>+ {pr.name}</strong><small>{t(pr.note)}</small></button>
      {/each}
      <button onclick={addCustom}><strong>+ {t('admin.lib.other')}</strong><small>{t('admin.lib.other_hint')}</small></button>
    </div>
  </Window>
{/if}

<style>
  .open-jackett {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-height: 44px;
    margin: 10px 0;
    padding: 8px 16px;
    border: 2px solid var(--ink);
    border-radius: 3px;
    background: var(--win);
    color: var(--ink);
    font: 17px/1.1 var(--cond);
    text-decoration: none;
    box-shadow:
      inset 2px 2px 0 var(--hi),
      inset -2px -2px 0 var(--lo);
  }
  .stepper {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  .stepper strong {
    min-width: 60px;
    padding: 6px 0;
    text-align: center;
    font: 24px var(--cond);
    background: #000;
    color: var(--yellow);
    border: 2px solid var(--ink);
  }
  .stepper button {
    width: 52px;
    font-size: 22px;
  }
  .presets {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .presets button {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
    padding: 8px 10px;
  }
  .presets small {
    font: 11px Verdana, Geneva, sans-serif;
    color: var(--muted);
  }
  .item {
    margin: 10px 0;
    padding: 4px 10px 10px;
    background: var(--win-2);
    border: 2px solid var(--ink);
  }
</style>
