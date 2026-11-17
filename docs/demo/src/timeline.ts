/**
 * The cut list, in frames at 30 fps.
 *
 * The music (assets/background.mp3, 28.5 s) is 90 BPM: a beat every 20
 * frames, the first at frame 18. It is looped to 50 s: around its frame 418
 * it sounds almost exactly like its frame 98 (4 bars earlier, same beat), so
 * it jumps back there twice with a short crossfade on the beat:
 *   music 0 → 418, then 98 → 418, then 98 → 854.
 * Every cut lands on a beat (frame 18 + 20 k). A scene keeps running for
 * TRANSITION frames after its end, under the next one's entrance.
 */
export const FPS = 30;
export const WIDTH = 960;
export const HEIGHT = 720;
export const TRANSITION = 12;

export const MUSIC_LENGTH = 854;
export const LOOP_FROM = 418; // jump from here…
export const LOOP_TO = 98; // …back to here
export const LOOPS = 2;
export const DURATION = LOOP_FROM + (LOOPS - 1) * (LOOP_FROM - LOOP_TO) + (MUSIC_LENGTH - LOOP_TO); // 1494

export type TransitionKind = 'snow' | 'star' | 'cube' | 'mosaic' | 'page' | 'blinds' | 'hearts' | 'spin' | 'rewind';

export interface SceneTiming {
  id: string;
  from: number;
  to: number;
  /** How this scene comes in over the previous one. */
  enter: TransitionKind;
}

export const SCENES: SceneTiming[] = [
  { id: 'intro', from: 0, to: 98, enter: 'snow' },
  { id: 'channels', from: 98, to: 318, enter: 'star' },
  { id: 'movies', from: 318, to: 538, enter: 'cube' },
  { id: 'advisor', from: 538, to: 758, enter: 'mosaic' },
  { id: 'remote', from: 758, to: 958, enter: 'page' },
  { id: 'admin', from: 958, to: 1118, enter: 'blinds' },
  { id: 'alarm', from: 1118, to: 1238, enter: 'hearts' },
  { id: 'weather', from: 1238, to: 1338, enter: 'spin' },
  { id: 'end', from: 1338, to: DURATION, enter: 'rewind' },
];
