<!-- Weather place: search a city by name (Open-Meteo geocoding); coordinates by hand as a fallback. -->
<script lang="ts">
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
      error = 'Recherche impossible pour le moment. Vérifiez la connexion Internet de la télé.';
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

<Window title="Votre ville" lamp={chosen ? 'on' : 'todo'}>
  {#snippet help()}
    <p>
      La télé affiche la météo du jour et des prochaines heures (bouton météo sous la grille des chaînes). Les
      prévisions viennent d'Open-Meteo : gratuit, sans compte ni clé.
    </p>
    <p>Sans ville, la météo est simplement masquée.</p>
  {/snippet}

  {#if chosen}
    <div class="place">
      <span class="pin"><Icon name="weather" size={34} /></span>
      <div class="grow">
        <strong>{cfg.weather.location_name || 'Lieu choisi'}</strong>
        <div class="muted">{cfg.weather.latitude}, {cfg.weather.longitude}</div>
      </div>
      <button onclick={clear}>Changer</button>
    </div>
  {:else}
    <form class="row" onsubmit={search}>
      <input class="grow" bind:value={query} placeholder="Tapez votre ville…" autocomplete="off" enterkeyhint="search" />
      <button class="primary" type="submit" disabled={searching}>{searching ? '…' : 'Chercher'}</button>
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
        <p class="muted">Aucune ville trouvée. Essayez l'orthographe exacte ou une ville voisine.</p>
      {/if}
    {/if}
  {/if}

  <button class="link" onclick={() => (manual = !manual)}>{manual ? '▾' : '▸'} Coordonnées à la main</button>
  {#if manual}
    <label><span>Nom affiché</span><input bind:value={cfg.weather.location_name} placeholder="Tours" /></label>
    <div class="two">
      <label><span>Latitude</span><input type="number" step="0.0001" inputmode="decimal" bind:value={cfg.weather.latitude} /></label>
      <label><span>Longitude</span><input type="number" step="0.0001" inputmode="decimal" bind:value={cfg.weather.longitude} /></label>
    </div>
    <Help label="Où trouver ces nombres ?">
      <p>
        Dans Google Maps, appuyez longuement sur votre maison : les deux nombres apparaissent en haut (par exemple
        <code>47.3941, 0.6848</code>). Le premier est la latitude, le second la longitude.
      </p>
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
