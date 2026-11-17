/** The soundtrack, sound effects and the pixel-art cursor. */
import { Audio, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame } from 'remotion';
import { LOOP_FROM, LOOP_TO, LOOPS, MUSIC_LENGTH } from './timeline';

const XFADE = 5; // frames on each side of a loop joint

/**
 * The music looped on the beat (see timeline.ts): one <Audio> per pass, each
 * crossfading (equal power) into the next around the joint.
 */
export const Music: React.FC<{ fadeOut: number }> = ({ fadeOut }) => {
  const passes: { at: number; from: number; to: number }[] = [];
  let at = 0;
  let from = 0;
  for (let i = 0; i <= LOOPS; i++) {
    const last = i === LOOPS;
    const to = last ? MUSIC_LENGTH : LOOP_FROM;
    passes.push({ at, from, to });
    at += to - from;
    from = LOOP_TO;
  }
  const end = at;
  return (
    <>
      {passes.map((p, i) => {
        const start = Math.max(0, p.from - (i ? XFADE : 0));
        const stop = Math.min(MUSIC_LENGTH, p.to + (i < passes.length - 1 ? XFADE : 0));
        const seqFrom = p.at - (p.from - start);
        const length = stop - start;
        return (
          <Sequence key={i} from={seqFrom} durationInFrames={length}>
            <Audio
              src={staticFile('background.mp3')}
              startFrom={start}
              endAt={stop}
              volume={(f) => {
                const fadeIn = i ? Math.sin((Math.PI / 2) * Math.min(1, f / (2 * XFADE))) : 1;
                const fadeOutJoint =
                  i < passes.length - 1 ? Math.cos((Math.PI / 2) * Math.max(0, (f - (length - 2 * XFADE)) / (2 * XFADE))) : 1;
                const global = seqFrom + f;
                const ending = interpolate(global, [end - fadeOut, end], [1, 0], {
                  extrapolateLeft: 'clamp',
                  extrapolateRight: 'clamp',
                });
                return 0.8 * fadeIn * fadeOutJoint * ending;
              }}
            />
          </Sequence>
        );
      })}
    </>
  );
};

/** A sound effect at a frame of the current sequence. */
export const Sfx: React.FC<{ at: number; name: string; volume?: number }> = ({ at, name, volume = 0.6 }) => (
  <Sequence from={at} durationInFrames={90}>
    <Audio src={staticFile(`sfx/${name}`)} volume={volume} />
  </Sequence>
);

export interface CursorStop {
  /** Frame (in the current sequence) the cursor reaches this point. */
  f: number;
  x: number;
  y: number;
}

const SIZE = 64; // 32 px art, ×2, nearest neighbour
const HOTSPOT = { arrow: [0, 0], hand: [15, 0] };

/**
 * The app's pixel-art cursor gliding between points, with clicks (a squash
 * and the app's own click blip). Points are frame pixels of the 960×720 shots.
 */
export const Cursor: React.FC<{
  path: CursorStop[];
  clicks?: number[];
  kind?: 'arrow' | 'hand';
  until?: number;
}> = ({ path, clicks = [], kind = 'hand', until = Infinity }) => {
  const frame = useCurrentFrame();
  if (frame < path[0].f || frame >= until) return clicks.map((c) => <Sfx key={c} at={c} name="click.wav" volume={0.5} />);
  let i = 0;
  while (i < path.length - 1 && frame >= path[i + 1].f) i++;
  const a = path[i];
  const b = path[Math.min(i + 1, path.length - 1)];
  const k =
    b === a ? 1 : interpolate(frame, [a.f, b.f], [0, 1], { easing: Easing.inOut(Easing.cubic), extrapolateRight: 'clamp' });
  const x = a.x + (b.x - a.x) * k;
  const y = a.y + (b.y - a.y) * k;
  const pressed = clicks.some((c) => frame >= c && frame < c + 4);
  const [hx, hy] = HOTSPOT[kind];
  return (
    <>
      <Img
        src={staticFile(`cursors/${kind === 'hand' ? 'pointer' : 'cursor'}.png`)}
        style={{
          position: 'absolute',
          left: x - (hx * SIZE) / 32,
          top: y - (hy * SIZE) / 32,
          width: SIZE,
          height: SIZE,
          imageRendering: 'pixelated',
          transform: pressed ? 'scale(0.85)' : undefined,
          transformOrigin: `${(hx * 100) / 32}% 0`,
          filter: 'drop-shadow(3px 3px 0 rgba(0,0,0,0.6))',
        }}
      />
      {clicks.map((c) => (
        <Sfx key={c} at={c} name="click.wav" volume={0.5} />
      ))}
    </>
  );
};
