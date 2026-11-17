<!-- TV power: no plug, or a Shelly smart plug that the Mute key switches. -->
<script lang="ts">
  import { t } from '../../lib/i18n';
  import { adminApi, type Cfg } from '../api';
  import TestButton from '../ui/TestButton.svelte';
  import Help from '../ui/Help.svelte';
  import Window from '../ui/Window.svelte';

  let { cfg = $bindable() }: { cfg: Cfg } = $props();

  const shelly = $derived(cfg.power.provider === 'shelly');
  const lamp = $derived(cfg.power.provider === 'none' ? 'off' : cfg.power.shelly_host ? 'on' : 'todo');
</script>

<Window title={t('admin.tv.title')} {lamp}>
  {#snippet help()}
    <p>{@html t('admin.tv.help1')}</p>
    <p>{t('admin.tv.help2')}</p>
  {/snippet}

  <p>{t('admin.tv.question')}</p>
  <div class="choices">
    <button class:selected={!shelly} onclick={() => (cfg.power.provider = 'none')}>
      {t('admin.tv.normal')}
      <small>{t('admin.tv.normal_hint')}</small>
    </button>
    <button class:selected={shelly} onclick={() => (cfg.power.provider = 'shelly')}>
      {t('admin.tv.shelly')}
      <small>{t('admin.tv.shelly_hint')}</small>
    </button>
  </div>

  {#if shelly}
    <label>
      <span>{t('admin.tv.address')}</span>
      <input bind:value={cfg.power.shelly_host} placeholder="192.168.1.50" inputmode="url" autocapitalize="off" />
    </label>
    <Help label={t('admin.tv.where')}>
      <ol>
        <li>{@html t('admin.tv.where1')}</li>
        <li>{@html t('admin.tv.where2')}</li>
        <li>{@html t('admin.tv.where3')}</li>
      </ol>
      <p>{t('admin.tv.tip')}</p>
    </Help>
    <TestButton label={t('admin.tv.test')} run={() => adminApi.check('power', cfg)} />
  {/if}
</Window>
