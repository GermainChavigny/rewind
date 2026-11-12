<!-- TV power: no plug, or a Shelly smart plug that the Mute key switches. -->
<script lang="ts">
  import { adminApi, type Cfg } from '../api';
  import TestButton from '../ui/TestButton.svelte';
  import Help from '../ui/Help.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  const shelly = $derived(cfg.power.provider === 'shelly');
  const lamp = $derived(cfg.power.provider === 'none' ? 'off' : cfg.power.shelly_host ? 'on' : 'todo');
</script>

<Window title="Allumer la télé" {lamp}>
  {#snippet help()}
    <p>
      Une vieille télé cathodique ne s'allume pas toute seule. Branchée sur une prise connectée, REWIND peut l'allumer
      et l'éteindre : avec la touche <strong>Mute</strong> de la télécommande, et automatiquement pour le réveil.
    </p>
    <p>Sans prise, tout fonctionne quand même : vous allumez la télé à la main.</p>
  {/snippet}

  <p>Comment la télé est-elle alimentée ?</p>
  <div class="choices">
    <button class:selected={!shelly} onclick={() => (cfg.power.provider = 'none')}>
      Prise normale
      <small>J'allume la télé moi-même</small>
    </button>
    <button class:selected={shelly} onclick={() => (cfg.power.provider = 'shelly')}>
      Prise Shelly
      <small>REWIND allume et éteint</small>
    </button>
  </div>

  {#if shelly}
    <label>
      <span>Adresse de la prise</span>
      <input bind:value={cfg.power.shelly_host} placeholder="192.168.1.50" inputmode="url" autocapitalize="off" />
    </label>
    <Help label="Où trouver l'adresse de la prise ?">
      <ol>
        <li>Ouvrez l'application <strong>Shelly Smart Control</strong>.</li>
        <li>Touchez la prise, puis <strong>Paramètres → Informations sur l'appareil</strong>.</li>
        <li>Recopiez l'<strong>adresse IP</strong> (quatre nombres, comme <code>192.168.1.50</code>).</li>
      </ol>
      <p>
        Conseil : dans votre box Internet, réservez cette adresse à la prise (« bail DHCP fixe ») pour qu'elle ne change
        jamais.
      </p>
    </Help>
    <TestButton label="Tester la prise" run={() => adminApi.check('power', cfg)} />
  {/if}
</Window>
