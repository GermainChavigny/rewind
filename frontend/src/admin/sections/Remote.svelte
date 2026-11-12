<!--
  Remote keys, grouped by use. "Learn" waits (30 s) for a key press on the TV
  and adds it to the action; the TV does not run the action meanwhile.
-->
<script lang="ts">
  import { onDestroy } from 'svelte';
  import { adminApi, type Cfg } from '../api';
  import { ACTION_GROUPS, keyLabel } from '../helpers';
  import Progress from '../ui/Progress.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  const LEARN_S = 30;
  let learning = $state<{ id: string; label: string } | null>(null);
  let left = $state(LEARN_S);
  let result = $state<{ ok: boolean; text: string } | null>(null);
  let timer: ReturnType<typeof setInterval> | undefined;
  let openGroup = $state<string | null>('Chaînes');

  async function learn(id: string, label: string) {
    if (learning) return;
    result = null;
    try {
      await adminApi.startLearn(id);
    } catch (err) {
      result = { ok: false, text: (err as Error).message };
      return;
    }
    learning = { id, label };
    left = LEARN_S;
    const started = Date.now();
    timer = setInterval(async () => {
      left = Math.max(0, LEARN_S - (Date.now() - started) / 1000);
      const state = await adminApi.learnState().catch(() => null);
      if (!state || !learning) return;
      if (state.key) {
        const keys: string[] = cfg.remote.keys[id] ?? [];
        cfg.remote.keys[id] = [state.key, ...keys.filter((k) => k !== state.key)];
        result = { ok: true, text: `Touche « ${keyLabel(state.key)} » ajoutée à « ${label} ».` };
        stop();
      } else if (!state.waiting) {
        result = { ok: false, text: 'Aucune touche reçue. La télé est-elle allumée sur REWIND v2 ?' };
        stop();
      }
    }, 500);
  }

  function stop() {
    clearInterval(timer);
    learning = null;
    void adminApi.cancelLearn().catch(() => {});
  }

  function removeKey(id: string, key: string) {
    cfg.remote.keys[id] = (cfg.remote.keys[id] ?? []).filter((k: string) => k !== key);
  }

  onDestroy(() => learning && stop());
</script>

<Window title="Les touches">
  {#snippet help()}
    <p>Apprenez à REWIND les touches de votre télécommande :</p>
    <ol>
      <li>Allumez la télé sur REWIND.</li>
      <li>Ici, touchez <strong>Apprendre</strong> à côté d'une action.</li>
      <li>Dans les 30 secondes, appuyez sur la touche de la télécommande.</li>
    </ol>
    <p>
      Une action peut avoir plusieurs touches (par exemple « 1 » et « & » pour la chaîne 1). Touchez une touche pour
      l'enlever. N'oubliez pas d'enregistrer à la fin.
    </p>
  {/snippet}

  {#if result}<p class:ok={result.ok} class:bad={!result.ok}>{result.text}</p>{/if}

  {#each ACTION_GROUPS as g (g.title)}
    <div class="group">
      <button class="g-head" aria-expanded={openGroup === g.title} onclick={() => (openGroup = openGroup === g.title ? null : g.title)}>
        <span>{openGroup === g.title ? '▾' : '▸'} {g.title}</span>
        <small>{g.actions.filter((a) => (cfg.remote.keys[a.id] ?? []).length).length}/{g.actions.length}</small>
      </button>
      {#if openGroup === g.title}
        {#each g.actions as a (a.id)}
          {@const keys = cfg.remote.keys[a.id] ?? []}
          <div class="action">
            <div class="a-main">
              <span class="lamp" class:on={keys.length} class:todo={!keys.length}></span>
              <span class="a-label">{a.label}</span>
            </div>
            <div class="keys">
              {#each keys as key (key)}
                <button class="key" onclick={() => removeKey(a.id, key)} aria-label="Enlever {keyLabel(key)}">
                  {keyLabel(key)} <span>×</span>
                </button>
              {/each}
              <button class="learn" onclick={() => learn(a.id, a.label)} disabled={!!learning}>+ Apprendre</button>
            </div>
          </div>
        {/each}
      {/if}
    </div>
  {/each}
</Window>

{#if learning}
  <div class="modal" role="dialog" aria-modal="true" aria-label="Apprentissage">
    <Window title="Apprentissage">
      <p class="big">Appuyez sur la touche<br /><strong>« {learning.label} »</strong><br />de la télécommande…</p>
      <Progress value={left / LEARN_S} />
      <p class="muted center">{Math.ceil(left)} s</p>
      <div class="row end"><button onclick={stop}>Annuler</button></div>
    </Window>
  </div>
{/if}

<style>
  .group {
    margin: 8px 0;
    border: 2px solid var(--ink);
    background: var(--win-2);
  }
  .g-head {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 0;
    border-radius: 0;
  }
  .g-head small {
    font: 13px Verdana, Geneva, sans-serif;
  }
  .action {
    padding: 8px 10px;
    border-top: 2px solid var(--lo);
  }
  .a-main {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .a-label {
    font-weight: bold;
  }
  .keys {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
  .key {
    min-height: 36px;
    padding: 4px 10px;
    background: #2b2b2b;
    color: #fff;
    font: 16px var(--cond);
    box-shadow:
      inset 2px 2px 0 #5a5a5a,
      inset -2px -2px 0 #000;
  }
  .key span {
    color: #ff7d8c;
    margin-left: 4px;
  }
  .learn {
    min-height: 36px;
    padding: 4px 10px;
    font-size: 15px;
  }
  .modal {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    padding: 16px;
    background: rgba(10, 20, 90, 0.55);
  }
  .modal > :global(.window) {
    width: 100%;
  }
  .big {
    font-size: 17px;
    text-align: center;
    line-height: 1.5;
  }
  .center {
    text-align: center;
  }
  .end {
    justify-content: flex-end;
  }
</style>
