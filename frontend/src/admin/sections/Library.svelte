<!--
  Movies & series: one window per service (film info, subtitles, torrent
  search, Movie Advisor), each with a lamp and a "where do I find my key?" note.
-->
<script lang="ts">
  import type { Cfg } from '../api';
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

  function addAdvisor(kind: 'gemini' | 'openrouter' | 'groq') {
    const presets = {
      gemini: { name: 'Gemini', kind: 'gemini', base_url: null, model: 'gemini-2.5-flash' },
      openrouter: { name: 'OpenRouter', kind: 'openai', base_url: 'https://openrouter.ai/api/v1', model: 'openai/gpt-4o-mini' },
      groq: { name: 'Groq', kind: 'openai', base_url: 'https://api.groq.com/openai/v1', model: 'llama-3.3-70b-versatile' },
    }; // prettier-ignore
    cfg.advisor.push({ ...presets[kind], api_key: '', json_mode: true });
  }

  function slots(delta: number) {
    cfg.library.download_slots = Math.max(1, Math.min(10, cfg.library.download_slots + delta));
  }
</script>

<Window title="Vidéothèque">
  {#snippet help()}
    <p>
      La vidéothèque cherche des films et des séries, les télécharge sur le PC de la télé, ajoute les sous-titres et les
      prépare pour la télé. Elle s'ouvre avec la chaîne « Vidéothèque » (voir Chaînes).
    </p>
    <p>Chaque service ci-dessous a un voyant : vert quand il est prêt, orange s'il manque quelque chose.</p>
  {/snippet}
  <label class="check">
    <input type="checkbox" bind:checked={cfg.library.enabled} />
    <span>Activer les films et séries</span>
  </label>
  {#if cfg.library.enabled}
    <span class="label">Téléchargements en même temps</span>
    <div class="stepper">
      <button onclick={() => slots(-1)} aria-label="Moins">−</button>
      <strong>{cfg.library.download_slots}</strong>
      <button onclick={() => slots(1)} aria-label="Plus">+</button>
    </div>
  {/if}
</Window>

{#if cfg.library.enabled}
  <Window title="Fiches des films" lamp={lampOf(has(cfg.tmdb.api_key))}>
    {#snippet help()}
      <p>TMDB fournit les titres, affiches et résumés des films et séries. Le compte et la clé sont gratuits.</p>
    {/snippet}
    <Secret bind:value={cfg.tmdb.api_key} label="Clé TMDB" placeholder="Clé d'API (v3)" />
    <Help label="Où trouver ma clé TMDB ?">
      <ol>
        <li>Créez un compte sur <a href="https://www.themoviedb.org/signup" target="_blank" rel="noreferrer">themoviedb.org</a>.</li>
        <li>Ouvrez <a href="https://www.themoviedb.org/settings/api" target="_blank" rel="noreferrer">Paramètres → API</a> et demandez une clé « Developer » (usage personnel).</li>
        <li>Copiez la <strong>Clé d'API</strong> (la courte, pas le long « jeton d'accès »).</li>
      </ol>
    </Help>
  </Window>

  <Window title="Sous-titres" lamp={lampOf(has(cfg.opensubtitles.api_key))}>
    {#snippet help()}
      <p>
        Quand un film n'a pas de sous-titres, REWIND les cherche sur OpenSubtitles et les cale sur la vidéo. Sans clé,
        seuls les sous-titres déjà inclus dans les fichiers sont utilisés.
      </p>
    {/snippet}
    <Secret bind:value={cfg.opensubtitles.api_key} label="Clé API" />
    <Help label="Où trouver ma clé OpenSubtitles ?">
      <ol>
        <li>Créez un compte gratuit sur <a href="https://www.opensubtitles.com" target="_blank" rel="noreferrer">opensubtitles.com</a>.</li>
        <li>Ouvrez <a href="https://www.opensubtitles.com/consumers" target="_blank" rel="noreferrer">API consumers</a>, puis <strong>New consumer</strong>.</li>
        <li>Donnez-lui un nom (« REWIND ») et copiez la <strong>API key</strong>.</li>
      </ol>
      <p>L'identifiant et le mot de passe sont ceux de votre compte : ils servent à télécharger les sous-titres (nombre limité par jour).</p>
    </Help>
    <label><span>Identifiant</span><input bind:value={cfg.opensubtitles.username} autocapitalize="off" autocomplete="off" /></label>
    <Secret bind:value={cfg.opensubtitles.password} label="Mot de passe" password />
  </Window>

  <Window title="Recherche de films" lamp={lampOf(cfg.indexers.some((i: Cfg) => has(i.api_key)))}>
    {#snippet help()}
      <p>
        Jackett interroge les sites de torrents pour trouver les films. Il tourne sur le PC de la télé, à côté de
        REWIND.
      </p>
    {/snippet}
    {#each cfg.indexers as ix, i (i)}
      <div class="item">
        <label><span>Nom</span><input bind:value={ix.name} /></label>
        <label><span>Adresse de Jackett</span><input bind:value={ix.url} autocapitalize="off" inputmode="url" /></label>
        <Secret bind:value={ix.api_key} label="Clé API Jackett" />
        <Help label="Où trouver la clé Jackett ?">
          <ol>
            <li>Sur le téléphone, ouvrez <code>http://&lt;adresse de la télé&gt;:9117</code> (la même adresse que cette page, port 9117).</li>
            <li>La <strong>API Key</strong> est en haut à droite : copiez-la.</li>
            <li>Ajoutez des sites avec <strong>+ Add indexer</strong> si la liste est vide.</li>
          </ol>
          <p>Laissez l'adresse <code>http://127.0.0.1:9117</code> si Jackett est installé sur le même PC.</p>
        </Help>
        <label><span>Relancer Jackett s'il s'arrête</span><input bind:value={ix.systemd_unit} placeholder="jackett.service" autocapitalize="off" /></label>
        <Help label="À quoi ça sert ?">
          <p>
            Si Jackett ne répond plus, REWIND le relance tout seul avec ce service. Laissez <code>jackett.service</code>
            sauf installation particulière ; videz le champ pour ne jamais le relancer.
          </p>
        </Help>
        <button class="danger" onclick={() => cfg.indexers.splice(i, 1)}>Retirer</button>
      </div>
    {/each}
    <button onclick={addIndexer}>+ Ajouter Jackett</button>
  </Window>

  <Window title="Movie Advisor" lamp={lampOf(cfg.advisor.some((p: Cfg) => has(p.api_key)))}>
    {#snippet help()}
      <p>
        Le Movie Advisor propose trois films selon vos envies, grâce à une intelligence artificielle. Ajoutez un ou
        plusieurs fournisseurs : si le premier ne répond pas, REWIND essaie le suivant.
      </p>
      <p>Gemini (Google) est gratuit pour un usage personnel : c'est le plus simple.</p>
    {/snippet}
    {#each cfg.advisor as p, i (i)}
      <div class="item">
        <div class="row"><strong class="grow">{i + 1}. {p.name}</strong><button class="danger" onclick={() => cfg.advisor.splice(i, 1)}>Retirer</button></div>
        <Secret bind:value={p.api_key} label="Clé API" />
        {#if p.kind === 'gemini'}
          <Help label="Où trouver ma clé Gemini ?">
            <ol>
              <li>Ouvrez <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">aistudio.google.com/apikey</a> avec un compte Google.</li>
              <li>Touchez <strong>Create API key</strong> et copiez la clé.</li>
            </ol>
          </Help>
        {:else}
          <Help label="Où trouver ma clé ?">
            <ul>
              <li>OpenRouter : <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer">openrouter.ai/keys</a></li>
              <li>Groq : <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">console.groq.com/keys</a></li>
            </ul>
            <p>Tout service « compatible OpenAI » fonctionne : indiquez son adresse d'API ci-dessous.</p>
          </Help>
          <label><span>Adresse de l'API</span><input bind:value={p.base_url} autocapitalize="off" inputmode="url" /></label>
        {/if}
        <label><span>Modèle</span><input bind:value={p.model} autocapitalize="off" /></label>
      </div>
    {/each}
    <span class="label">Ajouter un fournisseur</span>
    <div class="row">
      <button onclick={() => addAdvisor('gemini')}>+ Gemini</button>
      <button onclick={() => addAdvisor('openrouter')}>+ OpenRouter</button>
      <button onclick={() => addAdvisor('groq')}>+ Groq</button>
    </div>
  </Window>
{/if}

<style>
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
  .item {
    margin: 10px 0;
    padding: 4px 10px 10px;
    background: var(--win-2);
    border: 2px solid var(--ink);
  }
</style>
