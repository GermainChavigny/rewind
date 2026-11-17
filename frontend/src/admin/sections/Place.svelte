<!--
  Interface language, and the weather place: search a city by name (Open-Meteo
  geocoding); coordinates by hand as a fallback.
-->
<script lang="ts">
  import Glyph from '../../components/Glyph.svelte';
  import { LANGUAGES, t } from '../../lib/i18n';
  import { adminApi, type Cfg, type Place } from '../api';
  import Help from '../ui/Help.svelte';
  import Icon from '../ui/Icon.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  let query = $state('');
  let results = $state<Place[] | null>(null);
  let searching = $state(false);
  let error = $state('');
  let manual = $state(false);

  const chosen = $derived(cfg.weather.latitude != null && cfg.weather.longitude != null);

  async function search(event?: Event) {
    event?.preventDefault();
    if (query.trim().length < 2) return;
    searching = true;
    error = '';
    try {
      results = await adminApi.geocode(query);
    } catch {
      results = null;
      error = t('admin.place.search_error');
    } finally {
      searching = false;
    }
  }

  function pick(p: Place) {
    cfg.weather.location_name = p.name;
    cfg.weather.latitude = p.latitude;
    cfg.weather.longitude = p.longitude;
    results = null;
    query = '';
  }

  function clear() {
    cfg.weather.location_name = null;
    cfg.weather.latitude = null;
    cfg.weather.longitude = null;
  }
</script>

<Window title={t('admin.language')}>
  <select bind:value={cfg.general.language} aria-label={t('admin.language')}>
    {#each LANGUAGES as l (l.id)}<option value={l.id}>{l.name}</option>{/each}
  </select>
  <p class="muted">{t('admin.language_hint')}</p>
</Window>

<Window title={t('admin.place.title')} lamp={chosen ? 'on' : 'todo'}>
  {#snippet help()}
    <p>{t('admin.place.help1')}</p>
    <p>{t('admin.place.help2')}</p>
  {/snippet}

  {#if chosen}
    <div class="place">
      <span class="pin"><Icon name="weather" size={34} /></span>
      <div class="grow">
        <strong>{cfg.weather.location_name || t('admin.place.chosen')}</strong>
        <div class="muted">{cfg.weather.latitude}, {cfg.weather.longitude}</div>
      </div>
      <button onclick={clear}>{t('admin.place.change')}</button>
    </div>
  {:else}
    <form class="row" onsubmit={search}>
      <input class="grow" bind:value={query} placeholder={t('admin.place.placeholder')} autocomplete="off" enterkeyhint="search" />
      <button class="primary" type="submit" disabled={searching}>{searching ? '…' : t('adv.search')}</button>
    </form>
    {#if error}<p class="bad">{error}</p>{/if}
    {#if results}
      {#if results.length}
        <ul class="results">
          {#each results as p (`${p.latitude},${p.longitude}`)}
            <li>
              <button onclick={() => pick(p)}>
                <strong>{p.name}</strong>
                <small>{p.detail}</small>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="muted">{t('admin.place.none')}</p>
      {/if}
    {/if}
  {/if}

  <button class="link" onclick={() => (manual = !manual)}><Glyph name={manual ? 'caret-down' : 'caret-right'} /> {t('admin.place.manual')}</button>
  {#if manual}
    <label><span>{t('admin.place.name')}</span><input bind:value={cfg.weather.location_name} placeholder={t('admin.place.name_placeholder')} /></label>
    <div class="two">
      <label><span>{t('admin.place.lat')}</span><input type="number" step="0.0001" inputmode="decimal" bind:value={cfg.weather.latitude} /></label>
      <label><span>{t('admin.place.lon')}</span><input type="number" step="0.0001" inputmode="decimal" bind:value={cfg.weather.longitude} /></label>
    </div>
    <Help label={t('admin.place.where')}>
      <p>{@html t('admin.place.where_text')}</p>
    </Help>
  {/if}
</Window>

<style>
  .place {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0;
    padding: 10px;
    background: var(--field);
    border: 2px solid var(--ink);
  }
  .pin {
    font-size: 26px;
  }
  .results {
    list-style: none;
    margin: 0 0 10px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .results button {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }
  .results small {
    font: 12px Verdana, Geneva, sans-serif;
    color: var(--muted);
  }
  .two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
</style>
