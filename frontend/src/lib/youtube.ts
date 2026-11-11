/**
 * YouTube channel player (IFrame API), ported from v1's PlayerManager:
 *
 * - A channel is a playlist. We resume at the saved video index and position.
 * - Each video also remembers its own position: when the playlist moves to a
 *   video we already started, we seek to where we left it.
 * - Progress is saved every 2.5 s while playing (unless the channel has
 *   `save_progress = false`, e.g. news: those always restart from the top).
 * - Unavailable videos (YouTube errors) are skipped.
 */

import { api, type Channel, type PlaylistProgress } from './api';

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window {
    YT: any;
    onYouTubeIframeAPIReady?: () => void;
  }
}

const SAVE_EVERY_MS = 2500;
const PLAYING = 1;
const ENDED = 0;

let apiReady: Promise<void> | null = null;

function loadApi(): Promise<void> {
  apiReady ??= new Promise((resolve) => {
    if (window.YT?.Player) return resolve();
    window.onYouTubeIframeAPIReady = () => resolve();
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    document.head.appendChild(tag);
  });
  return apiReady;
}

export interface YouTubeEvents {
  onError: (code: number) => void;
}

export class YouTubeChannel {
  private player: any = null;
  private ready: Promise<void>;
  private channel: Channel | null = null;
  private progress: PlaylistProgress = {};
  private currentVideo: string | null = null;
  private saveTimer: ReturnType<typeof setInterval> | null = null;
  private loadSeq = 0;
  private suspended = false;

  constructor(
    element: HTMLElement,
    private events: YouTubeEvents,
  ) {
    this.ready = loadApi().then(
      () =>
        new Promise<void>((resolve) => {
          this.player = new window.YT.Player(element, {
            width: '100%',
            height: '100%',
            playerVars: {
              autoplay: 0,
              controls: 0, // driven by the remote only
              disablekb: 1,
              fs: 0,
              playsinline: 1,
              iv_load_policy: 3, // no annotations
              cc_load_policy: 0,
              rel: 0,
            },
            events: {
              onReady: () => resolve(),
              onStateChange: (e: any) => this.onState(e.data),
              onError: (e: any) => this.events.onError(e.data),
            },
          });
        }),
    );
  }

  /** Tune to a channel: resume its playlist where we left it. */
  async play(channel: Channel): Promise<void> {
    const seq = ++this.loadSeq;
    this.suspended = false;
    this.stopSaving();
    this.channel = channel;
    this.currentVideo = null;
    this.progress = channel.save_progress
      ? await api.progress(channel.playlist_id!).catch(() => ({}))
      : {};
    await this.ready;
    if (seq !== this.loadSeq) return; // zapped again meanwhile
    this.player.loadPlaylist({
      listType: 'playlist',
      list: channel.playlist_id,
      index: this.progress.video_index ?? 0,
      startSeconds: this.progress.position ?? 0,
    });
    this.player.setPlaybackQuality?.('hd720');
  }

  /** Pause and stop reacting (another source, e.g. a movie, takes over). */
  suspend(): void {
    this.suspended = true;
    this.pause();
  }

  pause(): void {
    this.player?.pauseVideo?.();
  }

  resume(): void {
    this.suspended = false;
    this.player?.playVideo?.();
  }

  get isPlaying(): boolean {
    return this.player?.getPlayerState?.() === PLAYING;
  }

  togglePlay(): void {
    if (this.isPlaying) this.pause();
    else this.resume();
  }

  next(): void {
    this.player?.nextVideo?.();
  }

  previous(): void {
    this.player?.previousVideo?.();
  }

  seek(delta: number): void {
    if (!this.player?.getCurrentTime) return;
    this.player.seekTo(Math.max(0, this.player.getCurrentTime() + delta), true);
  }

  setVolume(volume: number): void {
    this.player?.setVolume?.(volume);
  }

  private onState(state: number): void {
    if (this.suspended) {
      if (state === PLAYING) this.pause();
      return;
    }
    if (state === PLAYING) {
      this.player.unloadModule?.('captions');
      const videoId: string | undefined = this.player.getVideoData?.().video_id;
      if (videoId && videoId !== this.currentVideo) {
        // First play of the playlist already starts at the saved position.
        const first = this.currentVideo === null;
        this.currentVideo = videoId;
        const saved = this.progress.videos?.[videoId];
        if (!first && saved && saved > 0) this.player.seekTo(saved, true);
      }
      this.startSaving();
    } else if (state === ENDED) {
      this.player.playVideo();
    } else {
      this.stopSaving();
    }
  }

  private startSaving(): void {
    if (this.saveTimer || !this.channel?.save_progress) return;
    this.saveTimer = setInterval(() => this.save(), SAVE_EVERY_MS);
  }

  private stopSaving(): void {
    if (this.saveTimer) clearInterval(this.saveTimer);
    this.saveTimer = null;
  }

  private save(): void {
    const ch = this.channel;
    const videoId: string | undefined = this.player?.getVideoData?.().video_id;
    if (!ch?.playlist_id || !videoId) return;
    const position = this.player.getCurrentTime();
    const index = this.player.getPlaylistIndex();
    this.progress.videos = { ...this.progress.videos, [videoId]: position };
    api
      .saveProgress(ch.playlist_id, { video_id: videoId, video_index: Math.max(0, index), position })
      .catch(() => {});
  }
}
