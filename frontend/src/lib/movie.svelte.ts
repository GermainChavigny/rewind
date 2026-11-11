/**
 * Movie / episode playback on a <video> element (v1 PlayerManager, movie part).
 *
 * - Resumes at the saved position; progress is saved every 2.5 s, on pause and
 *   when stopping. A queue drives next/previous (the library order, or the
 *   ready episodes of a show).
 * - Subtitles: one <track> per language. Inactive tracks stay `hidden` (not
 *   `disabled`) so their cues are loaded and can be shifted. The offset is per
 *   language, persisted, and re-applied when a VTT (re)loads, never twice
 *   (`applied` remembers what each language's cues already received).
 * - Fit: `contain` (16:9 letterbox) or `cover` (4:3 crop), persisted per item.
 */

import { api, mediaUrl, type Media } from './api';
import { isWatched, library, WATCHED_THRESHOLD } from './library.svelte';

const SAVE_EVERY_MS = 2500;
const LANG_NAMES: Record<string, string> = { fr: 'Français', en: 'English' };

export type SubMode = 'fr' | 'en' | 'off';

interface BrowserAudioTrack {
  enabled: boolean;
  language: string;
  label: string;
}

class MoviePlayer {
  entry = $state<Media | null>(null);
  paused = $state(false);
  ended = $state(false);
  time = $state(0);
  duration = $state(0);
  fit = $state<'contain' | 'cover'>('contain');
  subLangs = $state<string[]>([]);
  subMode = $state<SubMode>('off');
  offsets = $state<Record<string, number>>({});
  audioTracks = $state<{ index: number; label: string }[]>([]);
  audioIndex = $state(0);

  queue: Media[] = [];
  index = -1;
  private video: HTMLVideoElement | null = null;
  private saveTimer: ReturnType<typeof setInterval> | null = null;
  private applied: Record<string, number> = {};
  private volume = 1;

  get active(): boolean {
    return this.entry !== null;
  }

  /** Watched threshold reached (unlocks the "next episode" button). */
  get watchedNow(): boolean {
    return this.ended || (this.duration > 0 && this.time >= WATCHED_THRESHOLD * this.duration);
  }

  get next(): Media | null {
    return this.queue[this.index + 1] ?? null;
  }

  attach(video: HTMLVideoElement): void {
    this.video = video;
    video.addEventListener('pause', () => {
      this.paused = true;
      this.save();
      this.stopSaving();
    });
    video.addEventListener('play', () => {
      this.paused = false;
      this.ended = false;
      this.startSaving();
    });
    video.addEventListener('ended', () => {
      this.ended = true;
      this.markWatched();
    });
    video.addEventListener('timeupdate', () => (this.time = video.currentTime));
    video.addEventListener('durationchange', () => (this.duration = video.duration || 0));
    video.addEventListener('loadedmetadata', () => this.readAudioTracks());
    video.addEventListener('loadeddata', () => this.applySubtitles());
  }

  play(entry: Media, queue?: Media[], index?: number): void {
    const video = this.video;
    if (!video || !entry.file) return;
    if (this.entry) this.save();
    if (queue) {
      this.queue = queue;
      this.index = index ?? queue.findIndex((m) => m.id === entry.id);
    }
    this.entry = entry;
    this.ended = false;
    this.paused = false;
    this.time = entry.position || 0;
    this.duration = entry.duration || 0;
    this.fit = entry.fit ?? 'contain';

    video.src = mediaUrl(entry.file);
    this.attachSubtitles(entry);
    const resumeAt = isWatched(entry) ? 0 : entry.position || 0; // a finished movie restarts
    video.addEventListener('loadedmetadata', () => (video.currentTime = resumeAt), { once: true });
    video.volume = this.volume;
    void video.play().catch(() => {});
    library.patchLocal(entry.id, { last_played_at: Math.floor(Date.now() / 1000) });
    void api.playback(entry.id, { started: true }).catch(() => {});
  }

  stop(): void {
    if (!this.entry || !this.video) return;
    this.save();
    this.stopSaving();
    this.video.pause();
    this.video.removeAttribute('src');
    this.video.querySelectorAll('track').forEach((t) => t.remove());
    this.video.load();
    this.entry = null;
    this.paused = false;
    this.ended = false;
  }

  togglePlay(): void {
    if (!this.video || !this.entry) return;
    if (this.video.paused) void this.video.play().catch(() => {});
    else this.video.pause();
  }

  pause(): void {
    this.video?.pause();
  }

  resume(): void {
    void this.video?.play().catch(() => {});
  }

  seek(delta: number): void {
    if (this.video && this.entry) this.video.currentTime = Math.max(0, this.video.currentTime + delta);
  }

  seekRatio(ratio: number): void {
    if (!this.video?.duration) return;
    this.video.currentTime = ratio * this.video.duration;
    this.resume();
  }

  playNext(): void {
    if (this.next) this.play(this.next, this.queue, this.index + 1);
  }

  playPrevious(): void {
    if (this.index > 0) this.play(this.queue[this.index - 1], this.queue, this.index - 1);
  }

  setVolume(percent: number): void {
    this.volume = Math.max(0, Math.min(1, percent / 100));
    if (this.video) this.video.volume = this.volume;
  }

  setFit(fit: 'contain' | 'cover'): void {
    this.fit = fit;
    this.persist({ fit });
  }

  // --- progress -------------------------------------------------------------------

  private startSaving(): void {
    this.stopSaving();
    this.saveTimer = setInterval(() => this.save(), SAVE_EVERY_MS);
  }

  private stopSaving(): void {
    if (this.saveTimer) clearInterval(this.saveTimer);
    this.saveTimer = null;
  }

  private save(): void {
    const video = this.video;
    const entry = this.entry;
    if (!video || !entry || !video.duration || Number.isNaN(video.duration)) return;
    const position = video.currentTime || 0;
    const duration = video.duration;
    const watched = entry.watched || position >= WATCHED_THRESHOLD * duration;
    library.patchLocal(entry.id, { position, duration, watched });
    void api.playback(entry.id, { position, duration }).catch(() => {});
  }

  private markWatched(): void {
    if (!this.entry || !this.video) return;
    library.patchLocal(this.entry.id, { watched: true });
    void api.playback(this.entry.id, { watched: true, position: this.video.currentTime || 0 }).catch(() => {});
  }

  private persist(fields: Partial<Pick<Media, 'fit' | 'subtitle_mode' | 'subtitle_offsets' | 'audio_track'>>): void {
    if (!this.entry) return;
    Object.assign(this.entry, fields);
    library.patchLocal(this.entry.id, fields);
    void api.playback(this.entry.id, fields as never).catch(() => {});
  }

  // --- subtitles ------------------------------------------------------------------

  private attachSubtitles(entry: Media): void {
    const video = this.video!;
    video.querySelectorAll('track').forEach((t) => t.remove());
    const subs = entry.subtitles ?? {};
    const langs = Object.keys(subs).filter((l) => l === 'fr' || l === 'en');
    this.subLangs = langs;
    this.offsets = { ...(entry.subtitle_offsets ?? {}) };
    this.applied = {};
    const saved = entry.subtitle_mode;
    // Saved choice if still valid, else French first, else the first language.
    this.subMode =
      saved && (saved === 'off' || langs.includes(saved))
        ? saved
        : langs.includes('fr')
          ? 'fr'
          : ((langs[0] as SubMode | undefined) ?? 'off');
    for (const lang of langs) {
      const track = document.createElement('track');
      track.kind = 'subtitles';
      track.srclang = lang;
      track.label = LANG_NAMES[lang] ?? lang;
      track.src = mediaUrl(subs[lang]);
      if (lang === this.subMode) track.default = true;
      // A (re)parsed VTT is back to its original timings: shift it again.
      track.addEventListener('load', () => {
        this.applied[lang] = 0;
        this.applySubtitles();
      });
      video.appendChild(track);
    }
    this.applySubtitles();
  }

  /** One language showing, the others hidden; catch up on pending offsets. */
  private applySubtitles(): void {
    const tracks = this.video?.textTracks;
    if (!tracks) return;
    for (const track of Array.from(tracks)) {
      track.mode = track.language === this.subMode ? 'showing' : 'hidden';
    }
    for (const lang of Object.keys(this.offsets)) {
      const delta = (this.offsets[lang] || 0) - (this.applied[lang] || 0);
      if (delta && this.shiftCues(lang, delta)) this.applied[lang] = this.offsets[lang];
    }
  }

  private shiftCues(lang: string, delta: number): boolean {
    let done = false;
    for (const track of Array.from(this.video?.textTracks ?? [])) {
      if (track.language !== lang || !track.cues?.length) continue;
      for (const cue of Array.from(track.cues)) {
        cue.startTime = Math.max(0, cue.startTime + delta);
        cue.endTime = Math.max(0, cue.endTime + delta);
      }
      done = true;
    }
    return done;
  }

  get offset(): number {
    return this.offsets[this.subMode] || 0;
  }

  setSubtitleMode(mode: SubMode): void {
    if (mode !== 'off' && !this.subLangs.includes(mode)) return;
    this.subMode = mode;
    this.applySubtitles();
    this.persist({ subtitle_mode: mode });
  }

  cycleSubtitles(): void {
    const cycle: SubMode[] = ['off', ...(this.subLangs as SubMode[])];
    this.setSubtitleMode(cycle[(cycle.indexOf(this.subMode) + 1) % cycle.length]);
  }

  /** Shift the ACTIVE language by `delta` seconds (+ = later), live. */
  adjustOffset(delta: number): void {
    const lang = this.subMode;
    if (lang === 'off') return;
    const round = (n: number) => Math.round(n * 100) / 100;
    if (this.shiftCues(lang, delta)) this.applied[lang] = round((this.applied[lang] || 0) + delta);
    this.offsets = { ...this.offsets, [lang]: round((this.offsets[lang] || 0) + delta) };
    this.persist({ subtitle_offsets: { ...this.offsets } });
  }

  // --- audio tracks ---------------------------------------------------------------

  private browserTracks(): BrowserAudioTrack[] {
    // `audioTracks` needs Chromium's AudioVideoTracks feature (kiosk flag).
    const list = (this.video as unknown as { audioTracks?: ArrayLike<BrowserAudioTrack> }).audioTracks;
    return list ? Array.from(list) : [];
  }

  private readAudioTracks(): void {
    const tracks = this.browserTracks();
    const names: Record<string, string> = { fr: 'Français', en: 'English', es: 'Español', de: 'Deutsch', it: 'Italiano' };
    this.audioTracks =
      tracks.length > 1
        ? tracks.map((t, i) => ({
            index: i,
            label: names[(t.language || '').slice(0, 2).toLowerCase()] || t.label || t.language || `#${i + 1}`,
          }))
        : [];
    const saved = this.entry?.audio_track;
    if (saved !== undefined && saved < tracks.length) this.setAudioTrack(saved, false);
    else this.audioIndex = Math.max(0, tracks.findIndex((t) => t.enabled));
  }

  setAudioTrack(index: number, save = true): void {
    const tracks = this.browserTracks();
    tracks.forEach((t, i) => (t.enabled = i === index));
    this.audioIndex = index;
    if (save) this.persist({ audio_track: index });
  }

  cycleAudio(): void {
    if (this.audioTracks.length < 2) return;
    const pos = this.audioTracks.findIndex((t) => t.index === this.audioIndex);
    this.setAudioTrack(this.audioTracks[(pos + 1) % this.audioTracks.length].index);
  }
}

export const movie = new MoviePlayer();
