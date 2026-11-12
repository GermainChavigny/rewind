<!-- Picture and sound: CRT effects, lip-sync offset, and (advanced) the video/audio outputs. -->
<script lang="ts">
  import type { Cfg } from '../api';
  import { avOffsetText } from '../helpers';
  import Help from '../ui/Help.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();
  let advanced = $state(false);

  function nudge(ms: number) {
    cfg.audio.av_offset_ms = Math.max(-2000, Math.min(2000, (cfg.audio.av_offset_ms ?? 0) + ms));
  }
</script>

<Window title="Image">
  {#snippet help()}
    <p>
      Les effets cathodiques imitent un vieux téléviseur : lignes de balayage, léger flou, coins arrondis. Sur une vraie
      télé cathodique, vous pouvez les couper, l'écran s'en charge déjà.
    </p>
  {/snippet}
  <label class="check">
    <input type="checkbox" bind:checked={cfg.display.crt_effects} />
    <span>Effets « écran cathodique »</span>
  </label>
</Window>

<Window title="Son synchronisé">
  {#snippet help()}
    <p>
      Si les lèvres bougent avant ou après les paroles, décalez le son. Regardez quelqu'un qui parle face caméra et
      ajustez par petits pas jusqu'à ce que ça colle.
    </p>
    <ul>
      <li>La voix arrive <strong>trop tôt</strong> : retardez le son (+).</li>
      <li>La voix arrive <strong>trop tard</strong> : avancez le son (−).</li>
    </ul>
  {/snippet}
  <div class="offset">
    <button onclick={() => nudge(-20)} aria-label="Avancer le son de 20 ms">− 20</button>
    <strong>{cfg.audio.av_offset_ms > 0 ? '+' : ''}{cfg.audio.av_offset_ms} ms</strong>
    <button onclick={() => nudge(20)} aria-label="Retarder le son de 20 ms">+ 20</button>
  </div>
  <input type="range" min="-500" max="500" step="10" bind:value={cfg.audio.av_offset_ms} aria-label="Décalage du son" />
  <p class="sentence">{avOffsetText(cfg.audio.av_offset_ms)}</p>
</Window>

<Window title="Branchements (avancé)">
  {#snippet help()}
    <p>
      À ne toucher que si l'image ou le son ne sortent pas au bon endroit. Laissés vides, REWIND choisit tout seul.
    </p>
  {/snippet}
  <button class="link" onclick={() => (advanced = !advanced)}>{advanced ? '▾ Masquer' : '▸ Afficher'} les réglages</button>
  {#if advanced}
    <label><span>Sortie vidéo</span><input bind:value={cfg.display.output} placeholder="automatique (ex. HDMI-A-2)" autocapitalize="off" /></label>
    <label><span>Définition</span><input bind:value={cfg.display.mode} placeholder="automatique (ex. 720x576)" autocapitalize="off" /></label>
    <Help label="Où trouver ces noms ?">
      <p>
        Sur le PC de la télé, la commande <code>xrandr</code> liste les sorties (<code>HDMI-A-2</code>,
        <code>VGA-1</code>…) et leurs définitions. Pour une télé cathodique PAL, <code>720x576</code> est la bonne.
      </p>
    </Help>
    <label><span>Sortie audio</span><input bind:value={cfg.audio.output_port} placeholder="automatique" autocapitalize="off" /></label>
    <Help label="Où trouver le nom de la sortie audio ?">
      <p>
        Sur le PC de la télé : <code>pactl list sinks</code>, rubrique « Ports » (par exemple
        <code>analog-output-headphones</code> pour la prise casque).
      </p>
    </Help>
  {/if}
</Window>

<style>
  .offset {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin: 8px 0 4px;
  }
  .offset strong {
    flex: 1;
    text-align: center;
    padding: 6px 0;
    font: 24px var(--cond);
    background: #000;
    color: var(--yellow);
    border: 2px solid var(--ink);
  }
</style>
