<!--
  Software update (bottom of the settings menu): installed version, the latest
  GitHub release, and an "Update" button that runs install.sh on the TV. The
  backend restarts at the end; this page waits for it, then shows the result.
-->
<script lang="ts">
  import Glyph from '../components/Glyph.svelte';
  import { onDestroy, onMount } from 'svelte';
  import { t } from '../lib/i18n';
  import { adminApi, type UpdateStatus } from './api';
  import Progress from './ui/Progress.svelte';
  import Window from './ui/Window.svelte';

  let status = $state<UpdateStatus | null>(null);
  let checking = $state(false);
  let error = $state('');
  let poll: ReturnType<typeof setInterval> | undefined;

  // install.sh steps (update.json "message") → progress bar and label (admin.upd.step.*).
  const STEPS: Record<string, number> = { starting: 0.05, checking: 0.1, download: 0.25, install: 0.55, restart: 0.9 };
  const ERRORS = ['no_release', 'unreachable', 'running', 'not_installed', 'spawn_failed'];
  const errorText = (code: string) => (ERRORS.includes(code) ? t(`admin.upd.err.${code}`) : code);

  const running = $derived(status?.progress?.state === 'running');
  const step = $derived.by((): [number, string] => {
    const id = status?.progress?.message ?? '';
    return id in STEPS ? [STEPS[id], t(`admin.upd.step.${id}`)] : [0.4, t('admin.upd.step.running')];
  });

  async function refresh(check = false) {
    try {
      status = await adminApi.update(check);
      error = '';
    } catch {
      // The backend is restarting at the end of an update: keep polling.
      if (!running) error = t('admin.upd.offline');
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
      error = errorText((err as Error).message);
    }
    await refresh();
  }

  onMount(() => void refresh());
  onDestroy(() => clearInterval(poll));
</script>

{#if status}
  <Window title={t('admin.upd.title')} lamp={status.available ? 'todo' : 'on'}>
    <p>{t('admin.upd.installed')} <strong>{status.current}</strong></p>
    {#if running}
      <p>{step[1]}</p>
      <Progress value={step[0]} />
      <p class="muted">{t('admin.upd.restart_note')}</p>
    {:else}
      {#if status.progress?.state === 'failed'}
        <p class="bad"><Glyph name="warn" /> {t('admin.upd.failed', { error: status.progress.message })}</p>
      {:else if status.progress?.state === 'done' && status.progress.message !== 'up to date' && status.progress.version === status.current}
        <p><Glyph name="check" /> {t('admin.upd.done')}</p>
      {/if}
      {#if status.available}
        <p>{t('admin.upd.available')} <strong>{status.latest}</strong></p>
        {#if status.notes}<pre class="notes">{status.notes}</pre>{/if}
        {#if status.can_update}
          <div class="row end"><button class="primary" onclick={update}><Glyph name="refresh" /> {t('admin.upd.update')}</button></div>
        {:else}
          <p class="muted">{errorText('not_installed')}</p>
        {/if}
      {:else if status.latest}
        <p class="muted">{t('admin.upd.up_to_date')}</p>
      {:else if status.error}
        <p class="muted">{errorText(status.error)}</p>
      {/if}
      {#if error}<p class="bad">{error}</p>{/if}
      <div class="row end">
        <button onclick={check} disabled={checking}>{checking ? t('admin.upd.checking') : t('admin.upd.check')}</button>
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
