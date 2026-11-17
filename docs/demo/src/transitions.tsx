/**
 * Cheap-camcorder transitions (early-90s video titler style). Each one wraps
 * the entering scene and reveals it over the previous one as `p` goes 0 → 1.
 */
import { AbsoluteFill, Easing, interpolate, random } from 'remotion';
import { HEIGHT, type TransitionKind, WIDTH } from './timeline';

const DIAG = Math.hypot(WIDTH, HEIGHT);

function star(cx: number, cy: number, r: number, turn: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const a = turn + (i * Math.PI) / 5 - Math.PI / 2;
    const rr = i % 2 ? r * 0.45 : r;
    pts.push(`${cx + rr * Math.cos(a)},${cy + rr * Math.sin(a)}`);
  }
  return pts.join(' ');
}

function heart(cx: number, cy: number, s: number): string {
  // A heart of width ~2s, centred on (cx, cy).
  return `M ${cx} ${cy + s * 0.9}
    C ${cx - s * 1.6} ${cy - s * 0.1}, ${cx - s * 0.9} ${cy - s * 1.3}, ${cx} ${cy - s * 0.45}
    C ${cx + s * 0.9} ${cy - s * 1.3}, ${cx + s * 1.6} ${cy - s * 0.1}, ${cx} ${cy + s * 0.9} Z`;
}

/** An SVG clip path shape for the mask transitions, in frame pixels. */
function clipShapes(kind: TransitionKind, p: number, id: string): React.ReactNode {
  switch (kind) {
    case 'star': {
      const r = interpolate(p, [0, 1], [1, DIAG * 1.25], { easing: Easing.in(Easing.quad) });
      return <polygon points={star(WIDTH / 2, HEIGHT / 2, r, p * Math.PI)} />;
    }
    case 'hearts': {
      const out: React.ReactNode[] = [];
      const cols = 5;
      const rows = 4;
      for (let c = 0; c < cols; c++)
        for (let r = 0; r < rows; r++) {
          const delay = random(`${id}-${c}-${r}`) * 0.4;
          const k = Math.max(0, Math.min(1, (p - delay) / 0.6));
          const cx = ((c + 0.5) * WIDTH) / cols;
          const cy = ((r + 0.5) * HEIGHT) / rows;
          if (k > 0) out.push(<path key={`${c}-${r}`} d={heart(cx, cy, k * 170)} />);
        }
      return out;
    }
    case 'blinds': {
      const n = 10;
      const h = HEIGHT / n;
      return Array.from({ length: n }, (_, i) => (
        <rect key={i} x={0} y={i * h} width={WIDTH} height={h * p} />
      ));
    }
    case 'mosaic': {
      const cols = 16;
      const rows = 12;
      const w = WIDTH / cols;
      const h = HEIGHT / rows;
      const out: React.ReactNode[] = [];
      for (let c = 0; c < cols; c++)
        for (let r = 0; r < rows; r++)
          if (random(`${id}-m-${c}-${r}`) < p) out.push(<rect key={`${c}-${r}`} x={c * w} y={r * h} width={w + 0.5} height={h + 0.5} />);
      return out;
    }
    default:
      return null;
  }
}

export const Enter: React.FC<{ kind: TransitionKind; p: number; id: string; children: React.ReactNode }> = ({
  kind,
  p,
  id,
  children,
}) => {
  if (p >= 1) return <AbsoluteFill>{children}</AbsoluteFill>;
  const clipId = `clip-${id}`;
  switch (kind) {
    case 'star':
    case 'hearts':
    case 'blinds':
    case 'mosaic':
      return (
        <AbsoluteFill>
          <svg width={0} height={0} style={{ position: 'absolute' }}>
            <clipPath id={clipId} clipPathUnits="userSpaceOnUse">
              {clipShapes(kind, p, id)}
            </clipPath>
          </svg>
          <AbsoluteFill style={{ clipPath: `url(#${clipId})` }}>{children}</AbsoluteFill>
          {kind === 'star' && <Sparkle p={p} />}
        </AbsoluteFill>
      );
    case 'cube': {
      // A face of a cube turning in from the right.
      const e = Easing.inOut(Easing.cubic)(p);
      return (
        <AbsoluteFill style={{ perspective: 1100 }}>
          <AbsoluteFill
            style={{
              transformOrigin: 'left center',
              transform: `translateX(${(1 - e) * WIDTH}px) rotateY(${(1 - e) * -90}deg)`,
              boxShadow: '-20px 0 40px rgba(0,0,0,0.7)',
            }}
          >
            {children}
            <AbsoluteFill style={{ background: '#000', opacity: (1 - e) * 0.6 }} />
          </AbsoluteFill>
        </AbsoluteFill>
      );
    }
    case 'page': {
      // A page flipping over from the left, its back shading as it turns.
      const e = Easing.out(Easing.cubic)(p);
      return (
        <AbsoluteFill style={{ perspective: 1400 }}>
          <AbsoluteFill style={{ transformOrigin: 'left center', transform: `rotateY(${(1 - e) * 110}deg)` }}>
            {children}
            <AbsoluteFill
              style={{ background: 'linear-gradient(to left, rgba(255,255,255,0.5), rgba(0,0,0,0.5))', opacity: 1 - e }}
            />
          </AbsoluteFill>
        </AbsoluteFill>
      );
    }
    case 'spin': {
      const e = Easing.out(Easing.back(1.4))(p);
      return (
        <AbsoluteFill style={{ transform: `scale(${Math.max(0.001, e)}) rotate(${(1 - p) * 720}deg)` }}>
          {children}
        </AbsoluteFill>
      );
    }
    default:
      return <AbsoluteFill>{children}</AbsoluteFill>;
  }
};

/** Glitter around the star wipe, because why not. */
const Sparkle: React.FC<{ p: number }> = ({ p }) => (
  <AbsoluteFill>
    {Array.from({ length: 14 }, (_, i) => {
      const a = random(`sp-a-${i}`) * Math.PI * 2;
      const d = p * DIAG * (0.25 + random(`sp-d-${i}`) * 0.4);
      return (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: WIDTH / 2 + Math.cos(a) * d,
            top: HEIGHT / 2 + Math.sin(a) * d,
            color: i % 2 ? '#fff6a0' : '#ffffff',
            fontSize: 30 + random(`sp-s-${i}`) * 30,
            opacity: 1 - p,
            transform: `translate(-50%, -50%) rotate(${p * 360}deg)`,
            textShadow: '0 0 10px #fff',
          }}
        >
          ✦
        </div>
      );
    })}
  </AbsoluteFill>
);
