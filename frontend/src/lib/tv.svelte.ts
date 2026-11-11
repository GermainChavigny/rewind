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
 */

import { api, ApiError, type Alarm, type Channel, type Media, type UiSettings, type Weather } from './api';
import { setLanguage, t } from './i18n';
import { buildKeyLookup, channelNumber, type Action } from './keymap';
import { advisor } from './advisor.svelte';
import { changeDarkness, shiftTime, stepToVolume, volumeToStep, VOLUME_STEPS } from './levels';
import { library } from './library.svelte';
import { movie } from './movie.svelte';
import { search, type SearchKind } from './search.svelte';
import { wakeAudio } from './sound';
import { announce, announceTime } from './voice';
import { YouTubeChannel } from './youtube';

const GRID_BOOT_MS = 3000;
const GRID_ZAP_MS = 2000;
const OSD_MS = 3000;
const ALARM_CHECK_MS = 4000;
const WEATHER_REFRESH_MS = 15 * 60 * 1000;
const OPEN_LIBRARY_MS = 900; // let the grid show the library channel first

export type Osd = 'volume' | 'alarm' | null;
/** Full screens. */
export type Screen = 'alarm' | 'library' | 'results' | 'series' | 'advisor' | null;
/** Above a screen; closing it shows the screen again. */
export type Overlay = 'weather' | 'keyboard' | null;
const MOVIE_SCREENS: Screen[] = ['library', 'results', 'series', 'advisor'];

class Tv {
  ready = $state(false);
  ui: UiSettings | null = null;
  modules = $state<Record<string, boolean>>({});
  channels = $state<Channel[]>([]);
  logos = $state<Record<string, string>>({});

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
  youtube: YouTubeChannel | null = null;
  private timers: Record<string, ReturnType<typeof setTimeout>> = {};
  private lastAlarmMinute: string | null = null;
  private stopRinging: (() => void) | null = null;

  // --- boot -------------------------------------------------------------------

  async init(): Promise<void> {
    setInterval(() => (this.now = new Date()), 1000);
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
    this.flashGrid(GRID_BOOT_MS);
    setInterval(() => this.checkAlarm(), ALARM_CHECK_MS);
    if (this.modules.weather) {
      void this.refreshWeather();
      setInterval(() => void this.refreshWeather(), WEATHER_REFRESH_MS);
    }
    if (this.modules.library) void library.init().catch(() => {});
  }

  private async load(): Promise<void> {
    const [ui, modules, channels, logos, state] = await Promise.all([
      api.ui(),
      api.modules(),
      api.channels(),
      api.logos(),
      api.state(),
    ]);
    this.ui = ui;
    setLanguage(ui.language);
    this.keys = buildKeyLookup(ui.keymap);
    this.modules = Object.fromEntries(modules.map((m) => [m.id, m.configured]));
    this.channels = channels;
    this.logos = Object.fromEntries(logos.map((l) => [l.id, l.url]));
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

  // --- remote -----------------------------------------------------------------

  onKey(event: KeyboardEvent): void {
    wakeAudio();
    const action = this.keys.get(event.key);
    if (this.ringing) {
      this.stopAlarm();
      return; // the key only silences the alarm
    }
    // The on-screen keyboard types letters, digits, space, backspace, enter.
    if (this.overlay === 'keyboard' && /^([a-z0-9 ]|Backspace|Enter|Escape)$/i.test(event.key)) return;
    if (!action) return;
    event.preventDefault();
    if (action !== 'tv_power' && !this.tvOn) void this.setPower(true);

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
    this.overlay = 'keyboard';
  }

  /** Keyboard validated: search, or the advisor's keywords. */
  submitKeyboard(text: string, kind: SearchKind): void {
    this.overlay = null;
    if (this.keyboardFor === 'advisor') {
      advisor.keywords = text;
      return;
    }
    this.searchFor(text, kind);
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

  /** Progressive alarm: chime fades in, then the alarm channel fades in. */
  async ring(): Promise<void> {
    const cfg = this.ui!.alarm;
    const number = this.channels.findIndex((c) => c.alarm) + 1;
    if (!number) return;
    await this.setPower(true);
    this.ringing = true;
    const target = this.volume || stepToVolume(VOLUME_STEPS / 2);
    this.selectChannel(number);
    this.youtube?.setVolume(0);

    const chime = new Audio('audio/alarm.wav');
    chime.loop = true;
    chime.volume = 0;
    chime.play().catch(() => {});
    const start = Date.now();
    const tick = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      if (elapsed >= cfg.max_duration_s) return this.stopAlarm();
      chime.volume = Math.min(1, elapsed / cfg.sound_ramp_s);
      if (elapsed >= cfg.video_delay_s) {
        const ratio = Math.min(1, (elapsed - cfg.video_delay_s) / cfg.video_ramp_s);
        this.youtube?.setVolume(ratio * target);
      }
    }, 100);
    this.stopRinging = () => {
      clearInterval(tick);
      chime.pause();
      this.youtube?.setVolume(this.volume);
    };
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

export const tv = new Tv();
