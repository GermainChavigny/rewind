<!--
  Phone admin (served at /admin/), early-90s online-service look. First run:
  a wizard (welcome, 5 steps, done). Afterwards: an icon menu with a lamp per
  section, each section with Cancel / Save. Every save writes the whole
  config; masked secrets go back as they came and the server keeps them.
-->
<script lang="ts">
  import Brand from '../components/Brand.svelte';
  import { LANGUAGES, setLanguage, t } from '../lib/i18n';
  import Glyph from '../components/Glyph.svelte';
  import { onDestroy, onMount, type Component } from 'svelte';
  import { adminApi, type Cfg, NeedsPin, rememberPin, savedPin, type Status } from './api';
  import { liveAudio } from './helpers';
  import Alarm from './sections/Alarm.svelte';
  import Channels from './sections/Channels.svelte';
  import Library from './sections/Library.svelte';
  import Picture from './sections/Picture.svelte';
  import Place from './sections/Place.svelte';
  import Remote from './sections/Remote.svelte';
  import Security from './sections/Security.svelte';
  import Tv from './sections/Tv.svelte';
  import Updates from './Updates.svelte';
  import Icon from './ui/Icon.svelte';
  import Progress from './ui/Progress.svelte';
  import Window from './ui/Window.svelte';

  type Section = 'place' | 'tv' | 'channels' | 'remote' | 'picture' | 'alarm' | 'library' | 'security';
  type Lamp = 'on' | 'todo' | 'off';

  const MASK = '********';
  // Labels, titles and intros are i18n keys (the language can change live).
  const VIEWS: Record<Section, { label: string; icon: string; view: Component<{ cfg: Cfg }> }> = {
    channels: { label: 'admin.menu.channels', icon: 'channels', view: Channels },
    remote: { label: 'admin.menu.remote', icon: 'remote', view: Remote },
    tv: { label: 'admin.menu.tv', icon: 'tv', view: Tv },
    place: { label: 'admin.menu.place', icon: 'weather', view: Place },
    alarm: { label: 'admin.menu.alarm', icon: 'alarm', view: Alarm },
    picture: { label: 'admin.menu.picture', icon: 'picture', view: Picture },
    library: { label: 'admin.menu.library', icon: 'library', view: Library },
    security: { label: 'admin.menu.security', icon: 'lock', view: Security },
  };
  const MENU = Object.keys(VIEWS) as Section[];
  /** Settings the backend could not apply live (status.restart_needed). */
  const RESTART_LABELS: Record<string, string> = { display: 'admin.restart.display' };
  const WIZARD: { id: Section; title: string; intro: string }[] = [
    { id: 'place', title: 'admin.wiz.place', intro: 'admin.wiz.place_intro' },
    { id: 'tv', title: 'admin.wiz.tv', intro: 'admin.wiz.tv_intro' },
    { id: 'channels', title: 'admin.wiz.channels', intro: 'admin.wiz.channels_intro' },
    { id: 'remote', title: 'admin.wiz.remote', intro: 'admin.wiz.remote_intro' },
    { id: 'security', title: 'admin.wiz.security', intro: 'admin.wiz.security_intro' },
  ];

  let status = $state<Status | null>(null);
  let cfg = $state<Cfg | null>(null);
  let section = $state<Section | null>(null);
  let wizard = $state(false);
  let step = $state(-1); // -1 = welcome, WIZARD.length = done
  let needPin = $state(false);
  let pinInput = $state('');
  let pinError = $state(false);
  let loadError = $state('');
  let snapshot = '';

  // Save dialog: a "Saving…" progress bar, then OK or the error.
  let saving = $state<{ progress: number; done: boolean; error: string | null } | null>(null);
  let saveTimer: ReturnType<typeof setInterval> | undefined;

  // The interface follows the language picked in the settings (before saving, as a preview).
  $effect(() => {
    if (cfg) setLanguage(cfg.general.language);
  });

  const current = $derived<Section | null>(
    wizard ? (step >= 0 && step < WIZARD.length ? WIZARD[step].id : null) : section,
  );

  async function load() {
    // The language first, so the PIN screen already speaks it (public, no PIN).
    await fetch('/api/ui')
      .then((r) => r.json())
      .then((ui) => setLanguage(ui.language))
      .catch(() => {});
    try {
      [status, cfg] = await Promise.all([adminApi.status(), adminApi.config()]);
      needPin = false;
      if (status.first_run) wizard = true;
    } catch (err) {
      if (err instanceof NeedsPin) {
        needPin = true;
        pinError = savedPin() !== '';
      } else loadError = (err as Error).message;
    }
  }

  function unlock(event: Event) {
    event.preventDefault();
    rememberPin(pinInput);
    pinInput = '';
    void load();
  }

  function lampOf(id: Section): Lamp {
    if (!cfg || !status) return 'off';
    switch (id) {
      case 'channels':
        return cfg.channels.length ? 'on' : 'todo';
      case 'remote':
        return 'on';
      case 'tv':
        return cfg.power.provider === 'none' ? 'off' : cfg.power.shelly_host ? 'on' : 'todo';
      case 'place':
        return status.weather ? 'on' : 'todo';
      case 'alarm':
        return cfg.alarm.chime !== 'none' || cfg.channels.some((c: Cfg) => c.alarm) ? 'on' : 'todo';
      case 'picture':
        return 'on';
      case 'library':
        return !cfg.library.enabled ? 'off' : cfg.tmdb.api_key ? 'on' : 'todo';
      case 'security':
        return status.has_pin ? 'on' : 'todo';
    }
  }

  function open(id: Section) {
    snapshot = JSON.stringify(cfg);
    section = id;
    window.scrollTo(0, 0);
  }

  function cancel() {
    if (snapshot) {
      const saved = JSON.parse(snapshot);
      // The A/V offset may have been tried live: put the saved one back.
      if (liveAudio.port && saved.audio.av_offset_ms !== cfg?.audio.av_offset_ms)
        void adminApi.avOffset(liveAudio.port, saved.audio.av_offset_ms).catch(() => {});
      cfg = saved;
    }
    section = null;
    window.scrollTo(0, 0);
  }

  async function save(): Promise<boolean> {
    if (!cfg) return false;
    const pin = cfg.admin.pin !== MASK ? (cfg.admin.pin as string) : null;
    saving = { progress: 0, done: false, error: null };
    clearInterval(saveTimer);
    saveTimer = setInterval(() => saving && !saving.done && (saving.progress = Math.min(0.9, saving.progress + 0.08)), 60);
    const started = Date.now();
    try {
      cfg = await adminApi.save(cfg);
      if (pin !== null) rememberPin(pin); // this phone keeps working after a PIN change
      status = await adminApi.status();
      snapshot = JSON.stringify(cfg);
      // Let the bar run a little: the retro "Saving…" is part of the fun.
      await new Promise((r) => setTimeout(r, Math.max(0, 700 - (Date.now() - started))));
      saving = { progress: 1, done: true, error: null };
      setTimeout(() => saving?.done && !saving.error && (saving = null), 900);
      return true;
    } catch (err) {
      if (err instanceof NeedsPin) {
        saving = null;
        needPin = true;
        return false;
      }
      saving = { progress: 1, done: true, error: (err as Error).message };
      return false;
    } finally {
      clearInterval(saveTimer);
    }
  }

  async function saveAndBack() {
    if (await save()) {
      section = null;
      window.scrollTo(0, 0);
    }
  }

  async function next() {
    if (!(await save())) return;
    step += 1;
    window.scrollTo(0, 0);
    if (step === WIZARD.length) {
      await adminApi.completeSetup().catch(() => {});
      status = await adminApi.status().catch(() => status);
    }
  }

  function back() {
    step = Math.max(-1, step - 1);
    window.scrollTo(0, 0);
  }

  function leaveWizard() {
    wizard = false;
    section = null;
    window.scrollTo(0, 0);
  }

  onMount(load);
  onDestroy(() => clearInterval(saveTimer));
</script>

<div class="screen">
  <header class="brand">
    <div class="logo">
      <svg class="globe" viewBox="0 0 100 100" aria-hidden="true">
        <g fill="none" stroke="#a7b8c9" stroke-width="3">
          <circle cx="50" cy="50" r="46" />
          <ellipse cx="50" cy="50" rx="20" ry="46" />
          <ellipse cx="50" cy="50" rx="36" ry="46" />
          <path d="M4 50 H96 M12 27 H88 M12 73 H88" />
        </g>
      </svg>
      <span class="mark"><Brand size={34} /></span>
    </div>
    <div class="side">
      <span class="title">{t('setup.title')}</span>
      {#if status}<span class="ver">v{status.version}</span>{/if}
    </div>
  </header>

  {#if needPin}
    <Window title={t('admin.pin.title')}>
      <p>{t('admin.pin.prompt')}</p>
      <form class="row" onsubmit={unlock}>
        <input class="grow" type="password" inputmode="numeric" autocomplete="current-password" bind:value={pinInput} placeholder={t('admin.pin.placeholder')} />
        <button class="primary" type="submit">{t('admin.pin.enter')}</button>
      </form>
      {#if pinError}<p class="bad">{t('admin.pin.wrong')}</p>{/if}
    </Window>
  {:else if loadError}
    <Window title={t('admin.error')}>
      <p class="bad">{t('admin.load_error', { error: loadError })}</p>
      <div class="row"><button onclick={() => location.reload()}>{t('lib.retry')}</button></div>
    </Window>
  {:else if !cfg}
    <Window title={t('admin.connecting_title')}>
      <p>{t('admin.connecting')}</p>
      <div class="pulse"><Progress value={0.35} /></div>
    </Window>
  {:else if wizard}
    {#if step === -1}
      <Window title={t('admin.wiz.welcome_title')}>
        <p class="hello">{@html t('admin.wiz.welcome')}</p>
        <p>{t('admin.wiz.welcome_text')}</p>
        <label><span>{t('admin.language')}</span>
          <select bind:value={cfg.general.language}>
            {#each LANGUAGES as l (l.id)}<option value={l.id}>{l.name}</option>{/each}
          </select>
        </label>
        <ol class="plan">
          {#each WIZARD as w (w.id)}
            <li><Icon name={VIEWS[w.id].icon} size={28} /> {t(w.title)}</li>
          {/each}
        </ol>
        <div class="row end"><button class="primary" onclick={() => (step = 0)}>{t('admin.wiz.start')} <Glyph name="right" /></button></div>
      </Window>
    {:else if step < WIZARD.length}
      <Window title={t('admin.wiz.title')}>
        <p class="step-name"><span>{t('admin.wiz.step', { n: step + 1, total: WIZARD.length })}</span> {t(WIZARD[step].title)}</p>
        <Progress value={(step + 1) / WIZARD.length} segments={WIZARD.length * 4} />
        <p class="muted">{t(WIZARD[step].intro)}</p>
      </Window>
      {@const View = VIEWS[WIZARD[step].id].view}
      <View bind:cfg={cfg!} />
      <div class="bottom">
        <button onclick={back}><Glyph name="left" /> {t('nav.back')}</button>
        <span class="grow"></span>
        <button class="primary" onclick={next}>{#if step === WIZARD.length - 1}{t('admin.wiz.finish')}{:else}{t('admin.wiz.next')} <Glyph name="right" />{/if}</button>
      </div>
    {:else}
      <Window title={t('admin.wiz.done_title')}>
        <p class="hello"><Icon name="tv" size={34} /> {t('admin.wiz.done')}</p>
        <p>{t('admin.wiz.done_text')}</p>
        <div class="row end"><button class="primary" onclick={leaveWizard}>{t('admin.wiz.to_settings')}</button></div>
      </Window>
    {/if}
  {:else if current}
    {@const View = VIEWS[current].view}
    <h1 class="s-title"><Icon name={VIEWS[current].icon} size={34} /> {t(VIEWS[current].label)}</h1>
    <View bind:cfg={cfg!} />
    <div class="bottom">
      <button onclick={cancel}>{t('nav.cancel')}</button>
      <span class="grow"></span>
      <button class="primary" onclick={saveAndBack}>{t('admin.save')}</button>
    </div>
  {:else}
    {#if status?.restart_needed?.length}
      <div class="alert">
        <strong><Glyph name="refresh" /> {t('admin.restart.title')}</strong>
        {t('admin.restart.text', { what: t(RESTART_LABELS[status.restart_needed[0]] ?? 'admin.restart.some') })}
      </div>
    {/if}
    {#if status && !status.has_pin}
      <div class="alert">
        <strong><Glyph name="warn" /> {t('admin.nopin.title')}</strong>
        {t('admin.nopin.text')}
        <button class="link" onclick={() => open('security')}>{t('admin.sec.choose')}</button>
      </div>
    {/if}
    <a class="remote-btn" href="/remote/" target="_blank" rel="noopener">
      <span class="r-led"></span>
      <span class="r-text"><strong>{t('admin.remote_btn')}</strong><small>{t('admin.remote_btn_hint')}</small></span>
      <span class="r-arrow"><Glyph name="external" size="20px" /></span>
    </a>
    <nav class="menu">
      {#each MENU as id (id)}
        {@const lamp = lampOf(id)}
        <button onclick={() => open(id)}>
          <Icon name={VIEWS[id].icon} />
          <span class="m-label">{t(VIEWS[id].label)}</span>
          <span class="lamp" class:on={lamp === 'on'} class:todo={lamp === 'todo'} title={lamp === 'todo' ? t('admin.lamp.todo') : ''}></span>
        </button>
      {/each}
    </nav>
    <p class="legend">
      <span><span class="lamp on"></span> {t('admin.lamp.on')}</span>
      <span><span class="lamp todo"></span> {t('admin.lamp.todo')}</span>
      <span><span class="lamp"></span> {t('admin.lamp.off')}</span>
    </p>
    <div class="updates"><Updates /></div>
  {/if}
</div>

{#if saving}
  <div class="modal" role="dialog" aria-modal="true" aria-label={t('admin.saving')}>
    <Window title={saving.error ? t('admin.error') : saving.done ? t('admin.saved') : t('admin.saving')}>
      {#if saving.error}
        <p class="bad">{saving.error}</p>
        <div class="row end"><button class="primary" onclick={() => (saving = null)}>OK</button></div>
      {:else}
        <p>{#if saving.done}{t('admin.saved_text')} <Glyph name="check" />{:else}{t('admin.sending')}{/if}</p>
        <Progress value={saving.progress} />
      {/if}
    </Window>
  </div>
{/if}

<style>
  .screen {
    max-width: 560px;
    margin: 0 auto;
    padding: 12px 12px 96px;
  }
  /* Brand bar: pale panel with the outlined logo and a wireframe globe, blue side. */
  .brand {
    display: flex;
    margin-bottom: 14px;
    border: 2px solid var(--ink);
    box-shadow: 5px 5px 0 rgba(0, 0, 0, 0.45);
  }
  .logo {
    position: relative;
    flex: 0 0 58%;
    padding: 8px 12px;
    background: var(--panel);
    border-right: 2px solid var(--ink);
    overflow: hidden;
  }
  .globe {
    position: absolute;
    right: -26px;
    bottom: -34px;
    width: 120px;
    height: 120px;
    opacity: 0.85;
  }
  .mark {
    position: relative;
    display: inline-block;
    --brand-tag: var(--ink);
  }
  .side {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 8px 12px;
    background: var(--desk);
    color: #fff;
  }
  .title {
    font: 24px var(--cond);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-shadow: 2px 2px 0 #000;
  }
  .ver {
    font-size: 12px;
    opacity: 0.8;
  }
  .s-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 12px;
    font: 26px var(--cond);
    color: #fff;
    text-transform: uppercase;
    text-shadow: 2px 2px 0 #000;
  }
  .menu {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .menu button {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    min-height: 104px;
    padding: 12px 6px 10px;
    font-size: 17px;
    box-shadow:
      inset 2px 2px 0 var(--hi),
      inset -2px -2px 0 var(--lo),
      4px 4px 0 rgba(0, 0, 0, 0.45);
  }
  .menu .lamp {
    position: absolute;
    top: 8px;
    right: 8px;
  }
  .m-label {
    text-transform: uppercase;
  }
  /* Not a settings button: charcoal like the remote, square like the other buttons. */
  .remote-btn {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
    padding: 14px 16px;
    border: 2px solid var(--ink);
    border-radius: 0;
    background: #29292c;
    color: #f2f2f2;
    text-decoration: none;
    font-weight: normal;
    box-shadow:
      inset 2px 2px 0 #55555b,
      inset -2px -2px 0 #111,
      4px 4px 0 rgba(0, 0, 0, 0.45);
  }
  .remote-btn:active {
    box-shadow:
      inset 2px 2px 0 #111,
      inset -2px -2px 0 #55555b;
  }
  .r-led {
    width: 14px;
    height: 6px;
    background: #ff3030;
    box-shadow: 0 0 8px #ff3030;
  }
  .r-text {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .r-text strong {
    font: 19px var(--cond);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .r-text small {
    font-size: 12px;
    color: #bbb;
  }
  .r-arrow {
    display: flex;
  }
  .legend {
    display: flex;
    justify-content: center;
    gap: 14px;
    margin-top: 14px;
    font-size: 12px;
    color: #fff;
  }
  .updates {
    margin-top: 18px;
  }
  .alert {
    margin-bottom: 14px;
    padding: 10px 12px;
    background: var(--yellow);
    border: 2px solid var(--ink);
    box-shadow: 5px 5px 0 rgba(0, 0, 0, 0.45);
    font-size: 14px;
  }
  .alert {
    --glyph-cut: var(--yellow);
  }
  .alert strong {
    display: flex;
    align-items: center;
    gap: 6px;
    font: 18px var(--cond);
    text-transform: uppercase;
  }
  .hello {
    font: 22px var(--cond);
  }
  .plan {
    list-style: none;
    padding: 0;
  }
  .plan li {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 6px 0;
    font-weight: bold;
  }
  .step-name {
    font: 20px var(--cond);
    text-transform: uppercase;
  }
  .step-name span {
    display: block;
    font: 13px Verdana, Geneva, sans-serif;
    text-transform: none;
    color: var(--muted);
  }
  .pulse {
    animation: pulse 1.2s steps(2) infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.4;
    }
  }
  .end {
    justify-content: flex-end;
  }
  /* Cancel / Save bar, always reachable (GIF: Cancel / Sign On). */
  .bottom {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10;
    display: flex;
    gap: 10px;
    max-width: 560px;
    margin: 0 auto;
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
    background: var(--win);
    border-top: 2px solid var(--ink);
    box-shadow: inset 0 2px 0 var(--hi);
  }
  .bottom button {
    min-width: 120px;
  }
  .modal {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    padding: 16px;
    background: rgba(10, 20, 90, 0.55);
  }
  .modal > :global(.window) {
    width: 100%;
    max-width: 420px;
    margin: 0 auto;
  }
</style>
