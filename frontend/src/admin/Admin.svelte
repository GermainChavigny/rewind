<!--
  Phone admin (served at /admin/). First run: a setup wizard walks through
  the essentials. Afterwards, one screen per settings section. Every save
  writes the whole config; masked secrets are sent back as they came and the
  server keeps the stored value.
-->
<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { adminApi, type Cfg, NeedsPin, type Logo, rememberPin, slug, type Status } from './api';

  type Section =
    | 'place' | 'tv' | 'channels' | 'remote' | 'picture' | 'alarm' | 'library' | 'security';

  const SECTIONS: { id: Section; label: string }[] = [
    { id: 'channels', label: 'Chaînes' },
    { id: 'remote', label: 'Télécommande' },
    { id: 'tv', label: 'Télé (prise)' },
    { id: 'place', label: 'Météo' },
    { id: 'picture', label: 'Image et son' },
    { id: 'alarm', label: 'Réveil' },
    { id: 'library', label: 'Films et séries' },
    { id: 'security', label: 'Code PIN' },
  ];
  const WIZARD: { id: Section; label: string }[] = [
    { id: 'place', label: 'Où êtes-vous ?' },
    { id: 'tv', label: 'La télé' },
    { id: 'channels', label: 'Les chaînes' },
    { id: 'remote', label: 'La télécommande' },
    { id: 'security', label: 'Code PIN' },
  ];
  const ACTIONS: Record<string, string> = {
    channel_1: 'Chaîne 1', channel_2: 'Chaîne 2', channel_3: 'Chaîne 3', channel_4: 'Chaîne 4',
    channel_5: 'Chaîne 5', channel_6: 'Chaîne 6', channel_7: 'Chaîne 7', channel_8: 'Chaîne 8',
    channel_9: 'Chaîne 9', alarm_toggle: 'Réveil on/off', alarm_later: 'Réveil +10 min',
    alarm_earlier: 'Réveil −10 min', tv_power: 'Télé on/off (Mute)', play_pause: 'Lecture / pause',
    next: 'Suivant', previous: 'Précédent', seek_forward: 'Avancer 15 s', seek_backward: 'Reculer 15 s',
    volume_up: 'Volume +', volume_down: 'Volume −', darker: 'Plus sombre', brighter: 'Plus clair',
  }; // prettier-ignore

  let status = $state<Status | null>(null);
  let cfg = $state<Cfg | null>(null);
  let logos = $state<Logo[]>([]);
  let section = $state<Section | null>(null);
  let wizard = $state(false);
  let step = $state(0);
  let needPin = $state(false);
  let pinInput = $state('');
  let message = $state<{ ok: boolean; text: string } | null>(null);
  let busy = $state(false);
  let learning = $state<string | null>(null);
  let learnTimer: ReturnType<typeof setInterval> | undefined;
  let logoFor = $state<number | null>(null);

  const wizardSection = $derived(WIZARD[step]?.id ?? null);
  const current = $derived(wizard ? wizardSection : section);

  async function load() {
    try {
      [status, cfg] = await Promise.all([adminApi.status(), adminApi.config()]);
      logos = await adminApi.logos().catch(() => []);
      needPin = false;
      if (status.first_run) wizard = true;
    } catch (err) {
      if (err instanceof NeedsPin) needPin = true;
      else message = { ok: false, text: (err as Error).message };
    }
  }

  function unlock() {
    rememberPin(pinInput);
    pinInput = '';
    void load();
  }

  async function save(next = true): Promise<boolean> {
    if (!cfg) return false;
    applyPin(); // a PIN typed in the security section (or the wizard) is saved with the rest
    busy = true;
    message = null;
    try {
      cfg = await adminApi.save(cfg);
      status = await adminApi.status();
      message = { ok: true, text: 'Enregistré.' };
      if (wizard && next) step = Math.min(step + 1, WIZARD.length - 1);
      return true;
    } catch (err) {
      if (err instanceof NeedsPin) needPin = true;
      else message = { ok: false, text: (err as Error).message };
      return false;
    } finally {
      busy = false;
    }
  }

  async function finishWizard() {
    await adminApi.completeSetup().catch(() => {});
    status = await adminApi.status().catch(() => status);
    wizard = false;
    section = null;
  }

  // --- channels -----------------------------------------------------------------------

  function addChannel() {
    if (!cfg || cfg.channels.length >= 9) return;
    const n = cfg.channels.length + 1;
    cfg.channels.push({
      id: `chaine-${n}`, name: `Chaîne ${n}`, show_name: false, logo: null, kind: 'youtube',
      playlist_id: '', save_progress: true, alarm: false,
    }); // prettier-ignore
  }

  function removeChannel(i: number) {
    cfg!.channels.splice(i, 1);
    logoFor = null;
  }

  function moveChannel(i: number, delta: number) {
    const list = cfg!.channels;
    const j = i + delta;
    if (j < 0 || j >= list.length) return;
    [list[i], list[j]] = [list[j], list[i]];
  }

  function renameChannel(ch: Cfg) {
    // Only default ids follow the name; a channel keeps its id once it is customised.
    if (!ch.id.startsWith('chaine-')) return;
    const base = slug(ch.name);
    const taken = cfg!.channels.filter((c: Cfg) => c !== ch).map((c: Cfg) => c.id);
    let id = base;
    for (let n = 2; taken.includes(id); n++) id = `${base}-${n}`;
    ch.id = id;
  }

  function setAlarm(i: number) {
    cfg!.channels.forEach((c: Cfg, j: number) => (c.alarm = j === i && !c.alarm));
  }

  // --- remote learning ------------------------------------------------------------------

  async function learn(action: string) {
    if (learning) return;
    learning = action;
    message = null;
    try {
      await adminApi.startLearn(action);
    } catch (err) {
      learning = null;
      message = { ok: false, text: (err as Error).message };
      return;
    }
    learnTimer = setInterval(async () => {
      const state = await adminApi.learnState().catch(() => null);
      if (!state) return;
      if (state.key && learning) {
        const keys: string[] = cfg!.remote.keys[action] ?? [];
        cfg!.remote.keys[action] = [state.key, ...keys.filter((k) => k !== state.key)];
        stopLearning();
        message = { ok: true, text: `« ${state.key} » attribué. Pensez à enregistrer.` };
      } else if (!state.waiting && !state.key) {
        stopLearning();
        message = { ok: false, text: 'Aucune touche reçue. Réessayez.' };
      }
    }, 1000);
  }

  function stopLearning() {
    clearInterval(learnTimer);
    learning = null;
    void adminApi.cancelLearn().catch(() => {});
  }

  function removeKey(action: string, key: string) {
    cfg!.remote.keys[action] = cfg!.remote.keys[action].filter((k: string) => k !== key);
  }

  // --- helpers ------------------------------------------------------------------------

  const logoName = (id: string | null) => (id ? (logos.find((l) => l.id === id)?.id ?? id).replace('custom:', '') : 'Aucun');
  const logoUrl = (id: string | null) => logos.find((l) => l.id === id)?.url ?? null;

  function addIndexer() {
    cfg!.indexers.push({ name: 'Jackett', url: 'http://127.0.0.1:9117', api_key: '', indexer: 'all', min_seeders: 1, max_size_gb: 6, timeout_s: 30, systemd_unit: null });
  }
  function addAdvisor() {
    cfg!.advisor.push({ name: 'Gemini', kind: 'gemini', base_url: null, api_key: '', model: 'gemini-2.5-flash', json_mode: true });
  }

  let pinNew = $state('');
  let pinRemove = $state(false);
  function applyPin() {
    if (!cfg) return;
    if (pinRemove) cfg.admin.pin = '';
    else if (pinNew.trim()) cfg.admin.pin = pinNew.trim();
    // This browser keeps working after the change, without asking again.
    if (pinRemove || pinNew.trim()) rememberPin(pinRemove ? '' : pinNew.trim());
    pinNew = '';
    pinRemove = false;
  }

  onMount(load);
  onDestroy(() => clearInterval(learnTimer));
</script>

<main>
  <header>
    <strong>REWIND</strong>
    <span class="muted">Réglages{status ? ` · v${status.version}` : ''}</span>
  </header>

  {#if needPin}
    <section class="card">
      <h2>Code PIN</h2>
      <p class="muted">Entrez le code PIN de l'administration.</p>
      <input type="password" inputmode="numeric" bind:value={pinInput} placeholder="Code PIN" />
      <button class="primary" onclick={unlock}>Entrer</button>
    </section>
  {:else if !cfg}
    <p class="muted">{message?.text ?? 'Chargement…'}</p>
  {:else if wizard}
    <section class="card">
      <p class="muted">Première installation · étape {step + 1} / {WIZARD.length}</p>
      <h2>{WIZARD[step].label}</h2>
      {@render editor(wizardSection!)}
      <div class="row">
        {#if step > 0}<button onclick={() => (step -= 1)}>Retour</button>{/if}
        {#if step < WIZARD.length - 1}
          <button class="primary" disabled={busy} onclick={() => save()}>Suivant</button>
        {:else}
          <button class="primary" disabled={busy} onclick={async () => (await save(false)) && (await finishWizard())}>Terminer</button>
        {/if}
      </div>
      {#if message}<p class:ok={message.ok} class:bad={!message.ok}>{message.text}</p>{/if}
    </section>
  {:else if section}
    <section class="card">
      <button onclick={() => { section = null; message = null; }}>← Réglages</button>
      <h2>{SECTIONS.find((s) => s.id === section)?.label}</h2>
      {@render editor(section)}
      <div class="row">
        <button class="primary" disabled={busy} onclick={() => save(false)}>Enregistrer</button>
      </div>
      {#if message}<p class:ok={message.ok} class:bad={!message.ok}>{message.text}</p>{/if}
    </section>
  {:else}
    <nav>
      {#each SECTIONS as s (s.id)}
        <button class="menu" onclick={() => (section = s.id)}>{s.label}<span>›</span></button>
      {/each}
    </nav>
    {#if status && status.has_pin === false}
      <p class="warn">Conseil : définissez un code PIN pour protéger ces réglages.</p>
    {/if}
  {/if}
</main>

{#snippet editor(id: Section)}
  {#if id === 'place'}
    <label><span>Nom du lieu</span><input bind:value={cfg!.weather.location_name} placeholder="Tours" /></label>
    <label><span>Latitude</span><input type="number" step="0.0001" bind:value={cfg!.weather.latitude} /></label>
    <label><span>Longitude</span><input type="number" step="0.0001" bind:value={cfg!.weather.longitude} /></label>
    <p class="muted">Sans coordonnées, la météo n'apparaît pas à l'écran.</p>
  {:else if id === 'tv'}
    <label><span>Prise connectée</span>
      <select bind:value={cfg!.power.provider}>
        <option value="none">Aucune (la télé ne s'éteint pas)</option>
        <option value="shelly">Shelly (Wi-Fi)</option>
      </select>
    </label>
    {#if cfg!.power.provider === 'shelly'}
      <label><span>Adresse de la prise (IP ou nom)</span><input bind:value={cfg!.power.shelly_host} placeholder="192.168.1.19" /></label>
    {/if}
  {:else if id === 'channels'}
    <p class="muted">{cfg!.channels.length} / 9 chaînes. Le numéro est la position dans la liste.</p>
    {#each cfg!.channels as ch, i (i)}
      <div class="item">
        <div class="row">
          <strong>{i + 1}</strong>
          <input bind:value={ch.name} onchange={() => renameChannel(ch)} placeholder="Nom" />
        </div>
        <div class="row">
          <button onclick={() => moveChannel(i, -1)} disabled={i === 0}>▲</button>
          <button onclick={() => moveChannel(i, 1)} disabled={i === cfg!.channels.length - 1}>▼</button>
          <button class:primary={ch.alarm} onclick={() => setAlarm(i)}>{ch.alarm ? 'Chaîne du réveil' : 'Faire du réveil'}</button>
          <button class="danger" onclick={() => removeChannel(i)}>Supprimer</button>
        </div>
        <label><span>Type</span>
          <select bind:value={ch.kind}>
            <option value="youtube">Playlist YouTube</option>
            <option value="library">Films et séries</option>
          </select>
        </label>
        {#if ch.kind === 'youtube'}
          <label><span>Identifiant de la playlist</span><input bind:value={ch.playlist_id} placeholder="PL…" /></label>
          <label class="check"><input type="checkbox" bind:checked={ch.save_progress} /> <span>Reprendre là où on s'est arrêté</span></label>
        {/if}
        <label class="check"><input type="checkbox" bind:checked={ch.show_name} /> <span>Afficher le nom à côté du logo</span></label>
        <div class="logo-pick">
          <button onclick={() => (logoFor = logoFor === i ? null : i)}>
            {#if logoUrl(ch.logo)}<img src={logoUrl(ch.logo)} alt="" />{/if}
            Logo : {logoName(ch.logo)}
          </button>
          {#if logoFor === i}
            <div class="logos">
              <button onclick={() => { ch.logo = null; logoFor = null; }}>Aucun</button>
              {#each logos as l (l.id)}
                <button class:selected={ch.logo === l.id} onclick={() => { ch.logo = l.id; logoFor = null; }}>
                  <img src={l.url} alt={l.id} />
                </button>
              {:else}
                <p class="muted">Aucun logo. Déposez vos images dans le dossier « logos » des données REWIND.</p>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    {/each}
    {#if cfg!.channels.length < 9}<button onclick={addChannel}>+ Ajouter une chaîne</button>{/if}
  {:else if id === 'remote'}
    <p class="muted">Appuyez sur « Apprendre », puis sur la touche de votre télécommande dans les 30 secondes.</p>
    {#each Object.keys(ACTIONS) as action (action)}
      <div class="item">
        <div class="row between">
          <span>{ACTIONS[action]}</span>
          <button onclick={() => learn(action)} disabled={learning !== null && learning !== action}>
            {learning === action ? 'Appuyez sur une touche…' : 'Apprendre'}
          </button>
        </div>
        <div class="keys">
          {#each cfg!.remote.keys[action] ?? [] as key (key)}
            <span class="key"><code>{key === ' ' ? 'Espace' : key}</code><button class="danger" onclick={() => removeKey(action, key)}>×</button></span>
          {:else}
            <span class="muted">Aucune touche</span>
          {/each}
        </div>
      </div>
    {/each}
  {:else if id === 'picture'}
    <label><span>Sortie vidéo</span><input bind:value={cfg!.display.output} placeholder="HDMI-A-2" /></label>
    <label><span>Mode</span><input bind:value={cfg!.display.mode} placeholder="720x576" /></label>
    <label class="check"><input type="checkbox" bind:checked={cfg!.display.crt_effects} /> <span>Effets écran cathodique</span></label>
    <label><span>Décalage audio (ms, + = son plus tard)</span><input type="number" min="-2000" max="2000" bind:value={cfg!.audio.av_offset_ms} /></label>
    <label><span>Sortie audio (PipeWire/PulseAudio)</span><input bind:value={cfg!.audio.output_port} placeholder="analog-output-headphones" /></label>
  {:else if id === 'alarm'}
    <label><span>Pas de réglage (minutes)</span><input type="number" min="1" max="60" bind:value={cfg!.alarm.step_minutes} /></label>
    <label><span>Son : montée (secondes)</span><input type="number" min="0" bind:value={cfg!.alarm.sound_ramp_s} /></label>
    <label><span>Image : délai avant l'arrivée (secondes)</span><input type="number" min="0" bind:value={cfg!.alarm.video_delay_s} /></label>
    <label><span>Image : montée (secondes)</span><input type="number" min="0" bind:value={cfg!.alarm.video_ramp_s} /></label>
    <label><span>Durée maximum (secondes)</span><input type="number" min="10" bind:value={cfg!.alarm.max_duration_s} /></label>
  {:else if id === 'library'}
    <label class="check"><input type="checkbox" bind:checked={cfg!.library.enabled} /> <span>Activer les films et séries</span></label>
    <label><span>Téléchargements en parallèle</span><input type="number" min="1" max="10" bind:value={cfg!.library.download_slots} /></label>
    <label><span>Clé TMDB</span><input bind:value={cfg!.tmdb.api_key} placeholder="Clé API TMDB" /></label>
    <h3>OpenSubtitles</h3>
    <label><span>Clé API</span><input bind:value={cfg!.opensubtitles.api_key} /></label>
    <label><span>Identifiant</span><input bind:value={cfg!.opensubtitles.username} /></label>
    <label><span>Mot de passe</span><input type="password" bind:value={cfg!.opensubtitles.password} /></label>
    <h3>Indexeurs (Jackett)</h3>
    {#each cfg!.indexers as ix, i (i)}
      <div class="item">
        <label><span>Nom</span><input bind:value={ix.name} /></label>
        <label><span>Adresse</span><input bind:value={ix.url} /></label>
        <label><span>Clé API</span><input bind:value={ix.api_key} /></label>
        <label><span>Unité systemd à relancer (facultatif)</span><input bind:value={ix.systemd_unit} placeholder="jackett.service" /></label>
        <button class="danger" onclick={() => cfg!.indexers.splice(i, 1)}>Supprimer</button>
      </div>
    {/each}
    <button onclick={addIndexer}>+ Ajouter un indexeur</button>
    <h3>Movie Advisor (IA)</h3>
    {#each cfg!.advisor as p, i (i)}
      <div class="item">
        <label><span>Nom</span><input bind:value={p.name} /></label>
        <label><span>Type</span>
          <select bind:value={p.kind}>
            <option value="gemini">Gemini</option>
            <option value="openai">Compatible OpenAI (OpenRouter, Groq…)</option>
          </select>
        </label>
        {#if p.kind === 'openai'}<label><span>Adresse de l'API</span><input bind:value={p.base_url} /></label>{/if}
        <label><span>Clé API</span><input bind:value={p.api_key} /></label>
        <label><span>Modèle</span><input bind:value={p.model} /></label>
        <button class="danger" onclick={() => cfg!.advisor.splice(i, 1)}>Supprimer</button>
      </div>
    {/each}
    <button onclick={addAdvisor}>+ Ajouter un fournisseur</button>
  {:else if id === 'security'}
    <p class="muted">{status?.has_pin ? 'Un code PIN est défini.' : 'Aucun code PIN : n\'importe qui sur le réseau peut changer les réglages.'}</p>
    <label><span>Nouveau code PIN</span><input type="password" inputmode="numeric" bind:value={pinNew} /></label>
    <label class="check"><input type="checkbox" bind:checked={pinRemove} /> <span>Supprimer le code PIN</span></label>
    <p class="muted">Le code est enregistré avec les autres réglages.</p>
  {/if}
{/snippet}

<style>
  main {
    max-width: 640px;
    margin: 0 auto;
    padding: 12px 14px 40px;
  }
  header {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 8px 0 14px;
  }
  .muted {
    color: var(--muted);
    font-size: 14px;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 16px;
  }
  h2 {
    margin: 10px 0 6px;
    font-size: 22px;
  }
  h3 {
    margin: 20px 0 4px;
    font-size: 17px;
  }
  nav {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .menu {
    display: flex;
    justify-content: space-between;
    font-size: 17px;
    text-align: left;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin: 10px 0;
  }
  .between {
    justify-content: space-between;
  }
  .item {
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 10px;
    margin: 12px 0;
  }
  .keys {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
  .key {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding-left: 8px;
    border: 1px solid var(--line);
    border-radius: 8px;
  }
  .key button {
    min-height: 32px;
    padding: 2px 8px;
    border: 0;
  }
  code {
    font-size: 15px;
  }
  .logo-pick button img,
  .logos img {
    height: 26px;
    width: auto;
    vertical-align: middle;
  }
  .logos {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
    gap: 6px;
    margin-top: 8px;
  }
  .logos button {
    min-height: 56px;
  }
  .logos .selected {
    border-color: var(--accent);
    border-width: 2px;
  }
  .ok {
    color: var(--ok);
  }
  .bad {
    color: var(--bad);
    white-space: pre-line;
  }
  .warn {
    color: var(--warn);
  }
</style>
