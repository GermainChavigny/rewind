<!--
  Software update (bottom of the settings menu): installed version, the latest
  GitHub release, and an "Update" button that runs install.sh on the TV. The
  backend restarts at the end; this page waits for it, then shows the result.
-->
<script lang="ts">
  import Glyph from '../components/Glyph.svelte';
  import { onDestroy, onMount } from 'svelte';
  import { adminApi, type UpdateStatus } from './api';
  import Progress from './ui/Progress.svelte';
  import Window from './ui/Window.svelte';

  let status = $state<UpdateStatus | null>(null);
  let checking = $state(false);
  let error = $state('');
  let poll: ReturnType<typeof setInterval> | undefined;

  // install.sh steps (update.json "message") → progress bar and French label.
  const STEPS: Record<string, [number, string]> = {
    starting: [0.05, 'Démarrage…'],
    checking: [0.1, 'Recherche de la nouvelle version…'],
    download: [0.25, 'Téléchargement…'],
    install: [0.55, 'Installation (quelques minutes)…'],
    restart: [0.9, 'Redémarrage de REWIND…'],
  };
  const ERRORS: Record<string, string> = {
    no_release: "Aucune version n'est encore publiée.",
    unreachable: 'Impossible de joindre le serveur des mises à jour (Internet ?).',
    running: 'Une mise à jour est déjà en cours.',
    not_installed: "Cette copie de REWIND n'a pas été installée par install.sh : mettez-la à jour avec git.",
    spawn_failed: "La mise à jour n'a pas pu démarrer.",
  };

  const running = $derived(status?.progress?.state === 'running');
  const step = $derived(STEPS[status?.progress?.message ?? ''] ?? [0.4, 'Mise à jour en cours…']);

  async function refresh(check = false) {
    try {
      status = await adminApi.update(check);
      error = '';
    } catch {
      // The backend is restarting at the end of an update: keep polling.
      if (!running) error = 'REWIND ne répond pas.';
    }
    if (running && !poll) poll = setInterval(() => void refresh(), 2000);
    if (!running && poll) {
      clearInterval(poll);
      poll = undefined;
    }
  }

  async function check() {
    checking = true;
    await refresh(true);
    checking = false;
  }

  async function update() {
    try {
      await adminApi.startUpdate();
    } catch (err) {
      error = ERRORS[(err as Error).message] ?? (err as Error).message;
    }
    await refresh();
  }

  onMount(() => void refresh());
  onDestroy(() => clearInterval(poll));
</script>

{#if status}
  <Window title="Mise à jour" lamp={status.available ? 'todo' : 'on'}>
    <p>Version installée : <strong>{status.current}</strong></p>
    {#if running}
      <p>{step[1]}</p>
      <Progress value={step[0]} />
      <p class="muted">La télé redémarre REWIND à la fin : l'écran clignote quelques secondes.</p>
    {:else}
      {#if status.progress?.state === 'failed'}
        <p class="bad"><Glyph name="warn" /> La dernière mise à jour a échoué : {status.progress.message}</p>
      {:else if status.progress?.state === 'done' && status.progress.message !== 'up to date' && status.progress.version === status.current}
        <p><Glyph name="check" /> Mise à jour terminée.</p>
      {/if}
      {#if status.available}
        <p>Nouvelle version disponible : <strong>{status.latest}</strong></p>
        {#if status.notes}<pre class="notes">{status.notes}</pre>{/if}
        {#if status.can_update}
          <div class="row end"><button class="primary" onclick={update}><Glyph name="refresh" /> Mettre à jour</button></div>
        {:else}
          <p class="muted">{ERRORS.not_installed}</p>
        {/if}
      {:else if status.latest}
        <p class="muted">REWIND est à jour.</p>
      {:else if status.error}
        <p class="muted">{ERRORS[status.error]}</p>
      {/if}
      {#if error}<p class="bad">{error}</p>{/if}
      <div class="row end">
        <button onclick={check} disabled={checking}>{checking ? 'Recherche…' : 'Rechercher une mise à jour'}</button>
      </div>
    {/if}
  </Window>
{/if}

<style>
  .notes {
    max-height: 160px;
    overflow: auto;
    padding: 8px;
    background: #fff;
    border: 2px inset var(--lo);
    font: 12px/1.4 Verdana, Geneva, sans-serif;
    white-space: pre-wrap;
  }
  .end {
    justify-content: flex-end;
  }
</style>
