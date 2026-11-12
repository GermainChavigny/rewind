/**
 * Central TV state and remote-control behaviour.
 *
 * Remote semantics (see docs/v1-behaviors.md):
 * - Any key stops a ringing alarm; any key except TV power turns the TV on.
 * - TV power (mute key): TV on → pause what plays and turn the TV off;
 *   TV off → turn it on. (The PC power button is handled by the OS.)
 * - Up/down set the alarm time (and arm it), 0 toggles it, with voice + OSD.
 *   In the movie screens they scroll the list under the cursor instead.
 * - Play/pause, next/previous, seek and volume drive the movie when one is
 *   playing, else YouTube. The library channel opens the library.
 * - On the welcome screen (intro video, or the channel grid of a paused
 *   channel), → opens the settings QR code (← closes it). It opens by itself
 *   while REWIND is not set up yet.
 * - The phone remote adds `home` (leave the movies for the welcome screen), a
 *   touchpad and its keyboard; the TV reports what it shows (`reportToPhones`).
 */

import { api, ApiError, learn, type Alarm, type Channel, type Media, type UiSettings, type Weather } from './api';
import { setLanguage, t } from './i18n';
import { buildKeyLookup, channelNumber, type Action } from './keymap';
import { advisor } from './advisor.svelte';
import { changeDarkness, shiftTime, stepToVolume, volumeToStep, VOLUME_STEPS } from './levels';
import { library } from './library.svelte';
import { movie } from './movie.svelte';
import { search, type SearchKind } from './search.svelte';
import { wakeAudio } from './sound';
import { announce, announceTime } from './voice';
import { clickPointer, movePointer, scrollPointer } from './vpointer';
import { YouTubeChannel } from './youtube';

const GRID_ZAP_MS = 2000;
const OSD_MS = 3000;
const ALARM_CHECK_MS = 4000;
const WEATHER_REFRESH_MS = 15 * 60 * 1000;
const OPEN_LIBRARY_MS = 900; // let the grid show the library channel first
const REPORT_MS = 120; // groups quick changes (typing) before telling the phones
const MAX_TEXT = 80;

export type Osd = 'volume' | 'alarm' | null;
/** Full screens. */
export type Screen = 'alarm' | 'library' | 'results' | 'series' | 'advisor' | null;
/** Above a screen; closing it shows the screen again. */
export type Overlay = 'weather' | 'keyboard' | 'setup' | null;
const MOVIE_SCREENS: Screen[] = ['library', 'results', 'series', 'advisor'];

class Tv {
  ready = $state(false);
  ui: UiSettings | null = null;
  modules = $state<Record<string, boolean>>({});
  channels = $state<Channel[]>([]);

  current = $state<Channel | null>(null);
  intro = $state(true);
  /** The YouTube channel is paused (the channel grid then stays on screen). */
  paused = $state(false);
  gridVisible = $state(false);
  darkness = $state(0);
  volume = $state(100);
  osd = $state<Osd>(null);
  screen = $state<Screen>(null);
  overlay = $state<Overlay>(null);
  keyboardFor = $state<'search' | 'advisor'>('search');
  /** On-screen keyboard: the text, and what a search looks for. */
  kbText = $state('');
  kbKind = $state<SearchKind>('movie');
  /** Not set up yet (first start): the welcome screen shows the settings QR code. */
  firstRun = $state(false);
  /** The phone asked to turn the computer off: "end of broadcast" card. */
  shuttingDown = $state(false);
  /** Series screen: the show, and where to start (resume point). */
  show = $state<Media | null>(null);
  showAt = $state<{ season?: number; episode?: number }>({});
  /** Library screen: the item to select when it opens. */
  libraryFocus = $state<string | null>(null);
  /** i18n key of the "technical difficulties" card, or null. */
  difficulty = $state<string | null>(null);
  alarm = $state<Alarm>({ time: '08:00', enabled: false });
  ringing = $state(false);
  tvOn = $state(true);
  weather = $state<Weather | null>(null);
  now = $state(new Date());

  private keys = new Map<string, Action>();
  /** Action the phone asked to learn a key for (polled from the server). */
  learning: string | null = null;
  youtube: YouTubeChannel | null = null;
  private timers: Record<string, ReturnType<typeof setTimeout>> = {};
  private lastAlarmMinute: string | null = null;
  private stopRinging: (() => void) | null = null;
  /** A/V sync test running until this time (ms), 0 = off. */
  avTestUntil = $state(0);
  private preview: HTMLAudioElement | null = null;
  /** The movie screen to show again when the alarm screen closes. */
  private alarmReturn = $state<Screen>(null);

  // --- boot -------------------------------------------------------------------

  async init(): Promise<void> {
    setInterval(() => (this.now = new Date()), 1000);
    setInterval(() => void learn.pending().then((r) => (this.learning = r.action)).catch(() => {}), 1000);
    this.listenEvents();
    while (!this.ready) {
      try {
        await this.load();
        this.ready = true;
        this.difficulty = null;
      } catch {
        this.difficulty = 'difficulties.offline';
        await new Promise((r) => setTimeout(r, 5000));
      }
    }
    // Boot: the intro video alone, no channel grid over it.
    if (this.firstRun) this.overlay = 'setup';
    this.reportToPhones();
    setInterval(() => this.checkAlarm(), ALARM_CHECK_MS);
    void this.refreshWeather();
    setInterval(() => void this.refreshWeather(), WEATHER_REFRESH_MS);
    if (this.modules.library) void library.init().catch(() => {});
  }

  /**
   * Settings were saved from the phone: reload them without restarting
   * (channels, keymap, alarm, modules, weather place, library).
   */
  private async reloadConfig(): Promise<void> {
    if (!this.ready) return;
    const hadLibrary = this.modules.library;
    const before = this.current;
    try {
      await this.load();
    } catch {
      return;
    }
    void this.refreshWeather();
    if (this.modules.library && !hadLibrary) void library.init().catch(() => {});
    // Set up from the phone: the QR code has done its job.
    if (!this.firstRun && this.overlay === 'setup') this.overlay = null;
    if (!before) return;
    const now = this.channels.find((c) => c.id === before.id) ?? null;
    if (!now) return;
    this.current = now;
    // Its playlist changed while it plays: tune it again.
    const playing = !this.screen && !movie.active && !this.intro;
    if (playing && now.kind === 'youtube' && now.playlist_id !== before.playlist_id)
      this.selectChannel(this.channels.indexOf(now) + 1);
  }

  private async load(): Promise<void> {
    const [ui, modules, channels, state] = await Promise.all([
      api.ui(),
      api.modules(),
      api.channels(),
      api.state(),
    ]);
    this.ui = ui;
    this.firstRun = ui.first_run;
    setLanguage(ui.language);
    this.keys = buildKeyLookup(ui.keymap);
    this.modules = Object.fromEntries(modules.map((m) => [m.id, m.configured]));
    this.channels = channels;
    this.darkness = state.darkness;
    this.volume = state.volume;
    if (this.modules.alarm) this.alarm = await api.alarm();
    if (this.modules.power) this.tvOn = (await api.power().catch(() => ({ on: true }))).on;
  }

  attachYouTube(element: HTMLElement): void {
    this.youtube = new YouTubeChannel(element, {
      onError: () => {
        // Unavailable video: show the card briefly and move on.
        this.showDifficulty('difficulties.video', 3000);
        setTimeout(() => this.youtube?.next(), 1500);
      },
      onPausedChange: (paused) => (this.paused = paused),
    });
  }

  attachMovie(video: HTMLVideoElement): void {
    movie.attach(video);
    movie.setVolume(this.volume);
  }

  /** On a movie screen, or watching a movie. */
  get inMovieUI(): boolean {
    return movie.active || MOVIE_SCREENS.includes(this.screen) || this.overlay === 'keyboard';
  }

  /** The phone remote's layout: the movies one also while the alarm screen is open from there. */
  get remoteMode(): 'tv' | 'movies' {
    return this.inMovieUI || (this.screen === 'alarm' && this.alarmReturn) ? 'movies' : 'tv';
  }

  /** Welcome screen: the intro video, or the channel grid of a paused channel. */
  get welcome(): boolean {
    return (
      this.ready &&
      !this.screen &&
      !this.overlay &&
      !movie.active &&
      !this.difficulty &&
      !this.ringing &&
      !this.shuttingDown &&
      (this.intro || this.paused)
    );
  }

  /**
   * A click on the picture (not on a button) pauses what plays: a movie, an
   * episode or a YouTube channel. Resuming stays on the play key / pause screen.
   */
  clickPause(): void {
    if (this.ringing || this.screen || this.overlay || this.difficulty || !this.tvOn) return;
    if (movie.active) {
      if (!movie.paused && !movie.ended) movie.togglePlay();
    } else if (this.current?.kind === 'youtube' && !this.paused && !this.intro) {
      this.youtube?.togglePlay();
    }
  }

  // --- remote -----------------------------------------------------------------

  onKey(event: KeyboardEvent): void {
    wakeAudio();
    if (this.learning) {
      // The phone is learning a key: this press is the new key, not an action.
      event.preventDefault();
      void learn.offer(event.key).catch(() => {});
      return;
    }
    const action = this.keys.get(event.key);
    if (this.ringing) {
      this.stopAlarm();
      return; // the key only silences the alarm
    }
    // The on-screen keyboard types letters, digits, space, backspace, enter.
    if (this.overlay === 'keyboard' && /^([a-z0-9 ]|Backspace|Enter|Escape)$/i.test(event.key)) return;
    if (!action) return;
    event.preventDefault();
    this.runAction(action);
  }

  /** What a remote action does (a key press, or the phone's virtual remote). */
  runAction(action: Action): void {
    if (this.ringing) return this.stopAlarm();
    if (this.shuttingDown) return;
    this.avTestUntil = 0;
    if (action !== 'tv_power' && !this.tvOn) void this.setPower(true);
    if (action === 'home') return this.goHome();
    // Exceptionally, → on the welcome screen opens the settings QR code.
    if (action === 'seek_forward' && this.welcome) return this.openOverlay('setup');
    if (this.overlay === 'setup' && (action === 'seek_backward' || action === 'play_pause'))
      return this.closeOverlay();

    const n = channelNumber(action);
    if (n !== null) return this.selectChannel(n);

    const film = movie.active;
    switch (action) {
      case 'tv_power':
        return void this.togglePower();
      case 'play_pause':
        return film ? movie.togglePlay() : this.youtube?.togglePlay();
      case 'next':
        return film ? movie.playNext() : this.youtube?.next();
      case 'previous':
        return film ? movie.playPrevious() : this.youtube?.previous();
      case 'seek_forward':
        return film ? movie.seek(15) : this.youtube?.seek(15);
      case 'seek_backward':
        return film ? movie.seek(-15) : this.youtube?.seek(-15);
      case 'volume_up':
        return this.changeVolume(1);
      case 'volume_down':
        return this.changeVolume(-1);
      case 'darker':
        return this.setDarkness(changeDarkness(this.darkness, 1));
      case 'brighter':
        return this.setDarkness(changeDarkness(this.darkness, -1));
      case 'alarm_toggle':
        return this.toggleAlarm();
      case 'alarm_later':
        return this.inMovieUI ? scrollHovered(-1) : this.shiftAlarm(1);
      case 'alarm_earlier':
        return this.inMovieUI ? scrollHovered(1) : this.shiftAlarm(-1);
    }
  }

  // --- channels -----------------------------------------------------------------

  selectChannel(number: number): void {
    const channel = this.channels[number - 1];
    if (!channel) return;
    this.current = channel;
    this.screen = null;
    this.overlay = null;
    this.difficulty = null;
    clearTimeout(this.timers.library);
    this.flashGrid(GRID_ZAP_MS);
    if (channel.kind === 'youtube' && this.modules.channels) {
      movie.stop();
      this.intro = false;
      void this.youtube
        ?.play(channel)
        .then(() => this.youtube?.setVolume(this.ringing ? 0 : this.volume));
    } else if (channel.kind === 'library' && this.modules.library) {
      this.youtube?.suspend();
      this.later('library', OPEN_LIBRARY_MS, () => {
        if (this.current?.id === channel.id && !this.screen) this.goLibrary();
      });
    } else {
      this.youtube?.suspend();
      this.showDifficulty('difficulties.soon');
    }
  }

  /**
   * Leaves the movies (phone remote): back to the welcome screen, with the
   * intro video and no channel grid; the phone remote follows.
   */
  goHome(): void {
    movie.stop();
    this.youtube?.suspend();
    clearTimeout(this.timers.library);
    clearTimeout(this.timers.grid);
    this.current = null;
    this.screen = null;
    this.overlay = null;
    this.difficulty = null;
    this.alarmReturn = null;
    this.gridVisible = false;
    this.paused = false;
    this.intro = true;
  }

  // --- movie screens ----------------------------------------------------------------

  /** The library (also the downloads list: unfinished items come first). */
  goLibrary(focus: string | null = null): void {
    movie.stop();
    this.libraryFocus = focus;
    this.overlay = null;
    this.screen = 'library';
    void library.load();
  }

  goSearch(): void {
    movie.stop();
    this.keyboardFor = 'search';
    this.kbText = '';
    // Movies or series: only what is configured can be searched.
    this.kbKind = !library.features.search ? 'series' : !library.features.series ? 'movie' : search.kind;
    this.overlay = 'keyboard';
  }

  goAdvisor(): void {
    movie.stop();
    this.overlay = null;
    advisor.open();
    this.screen = 'advisor';
  }

  editKeywords(): void {
    this.keyboardFor = 'advisor';
    this.kbText = advisor.keywords;
    this.overlay = 'keyboard';
  }

  /** Text typed on the TV keyboard, a real keyboard or the phone. */
  setKeyboardText(text: string): void {
    this.kbText = text.slice(0, MAX_TEXT);
  }

  /** Keyboard validated: search, or the advisor's keywords (empty = clear them). */
  submitKeyboard(): void {
    const text = this.kbText.trim();
    if (this.keyboardFor === 'advisor') {
      this.overlay = null;
      advisor.keywords = text;
      return;
    }
    if (text) this.searchFor(text, this.kbKind);
  }

  searchFor(query: string, kind: SearchKind): void {
    this.overlay = null;
    this.screen = 'results';
    void search.run(query, kind);
  }

  /** Series screen, at the last watched episode by default. */
  openSeries(show: Media, at?: { season?: number; episode?: number }): void {
    movie.stop();
    const last = library.lastPlayedEpisode(show.id, true);
    this.show = show;
    this.showAt = at ?? (last ? { season: last.season!, episode: last.episode! } : {});
    this.overlay = null;
    this.screen = 'series';
  }

  /** Download started: the library doubles as the downloads list. */
  downloadStarted(id: string | null = null): void {
    library.watchJobs();
    this.goLibrary(id);
  }

  playMovie(item: Media, queue?: Media[], index?: number): void {
    this.youtube?.suspend();
    this.intro = false;
    this.screen = null;
    this.overlay = null;
    this.difficulty = null;
    movie.setVolume(this.volume);
    movie.play(item, queue, index);
  }

  /** An episode of a show; next/previous follow the show's ready episodes. */
  async playEpisode(showId: string, season: number, episode: number): Promise<void> {
    await library.load(); // fresh state: an episode may just have finished
    const queue = library.readyEpisodes(showId);
    const index = queue.findIndex((e) => e.season === season && e.episode === episode);
    if (index >= 0) this.playMovie(queue[index], queue, index);
  }

  /** "Episodes" from a playing episode: back to its season. */
  episodesOfCurrent(): void {
    const entry = movie.entry;
    const show = library.get(entry?.parent_id);
    if (entry && show) this.openSeries(show, { season: entry.season!, episode: entry.episode! });
  }

  private flashGrid(ms: number): void {
    this.gridVisible = true;
    this.later('grid', ms, () => (this.gridVisible = false));
  }

  // --- TV power -----------------------------------------------------------------

  private async togglePower(): Promise<void> {
    if (!this.modules.power) return;
    if (this.tvOn) {
      // Pause whatever plays, movies included (v1 bug: a movie only paused).
      this.youtube?.pause();
      movie.pause();
      await this.setPower(false);
    } else {
      await this.setPower(true);
    }
  }

  private async setPower(on: boolean): Promise<void> {
    if (!this.modules.power) return;
    this.tvOn = on; // optimistic: the remote must feel instant
    try {
      this.tvOn = (await api.setPower(on)).on;
    } catch (err) {
      if (err instanceof ApiError) console.warn('TV power:', err.message);
    }
  }

  // --- volume & darkness ----------------------------------------------------------

  private changeVolume(direction: 1 | -1): void {
    const step = Math.max(0, Math.min(VOLUME_STEPS, volumeToStep(this.volume) + direction));
    this.volume = stepToVolume(step);
    this.youtube?.setVolume(this.volume);
    movie.setVolume(this.volume);
    this.showOsd('volume');
    this.later('saveVolume', 800, () => void api.patchState({ volume: this.volume }));
  }

  private setDarkness(value: number): void {
    this.darkness = value;
    this.later('saveDarkness', 800, () => void api.patchState({ darkness: this.darkness }));
  }

  get volumeStep(): number {
    return volumeToStep(this.volume);
  }

  // --- alarm ----------------------------------------------------------------------

  async setAlarm(alarm: Alarm): Promise<void> {
    this.alarm = alarm;
    await api.saveAlarm(alarm).catch(() => {});
  }

  toggleAlarm(): void {
    if (!this.modules.alarm) return;
    const enabled = !this.alarm.enabled;
    void this.setAlarm({ ...this.alarm, enabled });
    announce(t(enabled ? 'alarm.voice_on' : 'alarm.voice_off'), enabled ? 'alarm-on' : 'alarm-off');
    this.showOsd('alarm');
  }

  shiftAlarm(direction: 1 | -1): void {
    if (!this.modules.alarm) return;
    const time = shiftTime(this.alarm.time, direction * (this.ui?.alarm.step_minutes ?? 10));
    void this.setAlarm({ time, enabled: true });
    void announceTime(time);
    this.showOsd('alarm');
  }

  private checkAlarm(): void {
    if (!this.modules.alarm || !this.alarm.enabled || this.ringing) return;
    const now = new Date();
    const hhmm = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    if (hhmm !== this.alarm.time) {
      this.lastAlarmMinute = null;
      return;
    }
    if (this.lastAlarmMinute === hhmm) return;
    this.lastAlarmMinute = hhmm;
    void this.ring();
  }

  /**
   * Progressive alarm: the chime fades in (a safety net if the video is
   * silent), then the alarm channel fades in. Either one may be missing.
   */
  async ring(): Promise<void> {
    const cfg = this.ui!.alarm;
    const number = this.channels.findIndex((c) => c.alarm) + 1;
    const chimeId = cfg.chime && cfg.chime !== 'none' ? cfg.chime : null;
    if (!number && !chimeId) return;
    await this.setPower(true);
    this.ringing = true;
    const target = this.volume || stepToVolume(VOLUME_STEPS / 2);
    if (number) this.selectChannel(number);
    this.youtube?.setVolume(0);

    const chime = chimeId ? chimeAudio(chimeId) : null;
    if (chime) {
      chime.loop = true;
      chime.volume = 0;
      chime.play().catch(() => {});
    }
    const ramp = (elapsed: number, over: number) => (over > 0 ? Math.min(1, elapsed / over) : 1);
    const start = Date.now();
    const tick = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      if (elapsed >= cfg.max_duration_s) return this.stopAlarm();
      if (chime) chime.volume = ramp(elapsed, cfg.sound_ramp_s);
      if (number && elapsed >= cfg.video_delay_s) {
        this.youtube?.setVolume(ramp(elapsed - cfg.video_delay_s, cfg.video_ramp_s) * target);
      }
    }, 100);
    this.stopRinging = () => {
      clearInterval(tick);
      chime?.pause();
      this.youtube?.setVolume(this.volume);
    };
  }

  // --- events from the phone (virtual remote, sync test, chime preview) ---------------

  private listenEvents(): void {
    const source = new EventSource('/api/tv/events');
    // (Re)connected, e.g. after a backend restart: the phones need our state again.
    source.onopen = () => this.ready && this.reportToPhones(true);
    source.onmessage = (message) => {
      let event: PhoneEvent;
      try {
        event = JSON.parse(message.data);
      } catch {
        return;
      }
      if (event.type !== 'config' && event.type !== 'pointer') wakeAudio();
      if (event.type === 'action' && event.action) this.runAction(event.action as Action);
      else if (event.type === 'pointer') this.phonePointer(event);
      else if (event.type === 'text') this.phoneText(event.text ?? '', !!event.submit);
      else if (event.type === 'shutdown') this.endOfBroadcast();
      else if (event.type === 'shutdown_failed') {
        this.shuttingDown = false;
        this.showDifficulty('difficulties.shutdown_failed', 6000);
      }
      else if (event.type === 'avtest') this.startAvTest();
      else if (event.type === 'avtest_stop') this.avTestUntil = 0;
      else if (event.type === 'chime' && event.chime) this.previewChime(event.chime);
      else if (event.type === 'chime_stop') this.preview?.pause();
      else if (event.type === 'config') void this.reloadConfig();
    };
    // EventSource reconnects by itself after a backend restart.
  }

  private phonePointer(e: PhoneEvent): void {
    if (this.shuttingDown) return;
    if (e.scroll) scrollPointer(e.scroll);
    if (e.dx || e.dy) movePointer(e.dx ?? 0, e.dy ?? 0);
    if (e.click) clickPointer();
  }

  private phoneText(text: string, submit: boolean): void {
    if (this.overlay !== 'keyboard') return;
    this.setKeyboardText(text);
    if (submit) this.submitKeyboard();
  }

  /** The computer turns off in a few seconds: stop everything, show the card. */
  private endOfBroadcast(): void {
    this.stopAlarm();
    this.youtube?.pause();
    movie.pause();
    this.overlay = null;
    this.osd = null;
    this.shuttingDown = true;
  }

  private lastReport = '';
  private reportTimer: ReturnType<typeof setTimeout> | undefined;
  private reporting = false;

  /**
   * Tells the phone remotes what the TV shows (movies or not, the keyboard and
   * its text) now, then whenever it changes. `force` sends it even unchanged
   * (the backend restarted and forgot it).
   */
  reportToPhones(force = false): void {
    if (force) this.lastReport = '';
    if (this.reporting) return void this.sendReport();
    this.reporting = true;
    $effect.root(() => {
      $effect(() => {
        // Read what the report depends on, then send it shortly after.
        void [this.remoteMode, this.overlay, this.kbText, this.kbKind, this.keyboardFor];
        clearTimeout(this.reportTimer);
        this.reportTimer = setTimeout(() => this.sendReport(), REPORT_MS);
      });
    });
  }

  private sendReport(): void {
    const body = JSON.stringify({
      mode: this.remoteMode,
      keyboard:
        this.overlay === 'keyboard'
          ? { text: this.kbText, purpose: this.keyboardFor === 'advisor' ? 'advisor' : this.kbKind }
          : null,
    });
    if (body === this.lastReport) return;
    this.lastReport = body;
    fetch('/api/tv/report', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body }).catch(
      () => (this.lastReport = ''),
    );
  }

  startAvTest(seconds = 60): void {
    if (!this.tvOn) void this.setPower(true);
    this.avTestUntil = Date.now() + seconds * 1000;
  }

  /** Plays a chime once on the TV, at the TV volume (alarm settings preview). */
  previewChime(id: string): void {
    this.preview?.pause();
    if (id === 'none') return;
    this.preview = chimeAudio(id);
    this.preview.volume = Math.max(0.2, this.volume / 100);
    this.preview.play().catch(() => {});
  }

  stopAlarm(): void {
    this.stopRinging?.();
    this.stopRinging = null;
    this.ringing = false;
  }

  // --- overlays -------------------------------------------------------------------

  showOsd(kind: Exclude<Osd, null>): void {
    this.osd = kind;
    this.later('osd', OSD_MS, () => (this.osd = null));
  }

  showDifficulty(key: string, ms?: number): void {
    this.difficulty = key;
    if (ms) this.later('difficulty', ms, () => (this.difficulty = null));
  }

  /** Alarm settings, from the header of a movie screen: closing goes back there. */
  openAlarm(): void {
    if (this.screen === 'alarm') return;
    this.alarmReturn = this.screen && MOVIE_SCREENS.includes(this.screen) ? this.screen : null;
    this.openScreen('alarm');
  }

  closeAlarm(): void {
    const back = this.alarmReturn;
    this.alarmReturn = null;
    this.openScreen(back);
  }

  openScreen(screen: Screen): void {
    this.screen = screen;
    this.overlay = null;
    this.osd = null;
  }

  openOverlay(overlay: Overlay): void {
    this.overlay = overlay;
    this.osd = null;
  }

  closeOverlay(): void {
    this.overlay = null;
  }

  private async refreshWeather(): Promise<void> {
    if (!this.modules.weather) {
      this.weather = null;
      return;
    }
    this.weather = await api.weather().catch(() => this.weather);
  }

  private later(name: string, ms: number, fn: () => void): void {
    clearTimeout(this.timers[name]);
    this.timers[name] = setTimeout(fn, ms);
  }
}

/** Scroll the scrollable box under the cursor (↑/↓ on the movie screens). */
let mouse = { x: 0, y: 0 };
if (typeof window !== 'undefined') {
  window.addEventListener('mousemove', (e) => (mouse = { x: e.clientX, y: e.clientY }), { passive: true });
}

function scrollHovered(direction: 1 | -1): void {
  let node = document.elementFromPoint(mouse.x, mouse.y);
  while (node && node !== document.body) {
    const style = getComputedStyle(node);
    const el = node as HTMLElement;
    if (/(auto|scroll)/.test(style.overflowY) && el.scrollHeight > el.clientHeight + 1) {
      el.scrollBy({ top: Math.round(el.clientHeight * 0.6) * direction, behavior: 'smooth' });
      return;
    }
    if (/(auto|scroll)/.test(style.overflowX) && el.scrollWidth > el.clientWidth + 1) {
      el.scrollBy({ left: Math.round(el.clientWidth * 0.6) * direction, behavior: 'smooth' });
      return;
    }
    node = node.parentElement;
  }
}

interface PhoneEvent {
  type: string;
  action?: string;
  chime?: string;
  dx?: number;
  dy?: number;
  click?: boolean;
  scroll?: number;
  text?: string;
  submit?: boolean;
}

export const tv = new Tv();

function chimeAudio(id: string): HTMLAudioElement {
  return new Audio(`audio/chimes/${id}.mp3`);
}
