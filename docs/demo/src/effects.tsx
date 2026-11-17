/** Shared look: shots, snow, captions, the CRT layer, the VCR font. */
import { useEffect, useState } from 'react';
import { AbsoluteFill, continueRender, delayRender, Img, interpolate, random, staticFile, useCurrentFrame } from 'remotion';
import { HEIGHT, WIDTH } from './timeline';

export const VCR = 'VCR OSD Mono';

/** Loads the VCR OSD Mono font before the first frame renders. */
export function useVcrFont(): void {
  const [handle] = useState(() => delayRender('VCR font'));
  useEffect(() => {
    const face = new FontFace(VCR, `url(${staticFile('fonts/vcr-osd-mono.ttf')})`);
    face
      .load()
      .then((f) => (document.fonts as unknown as Set<FontFace>).add(f))
      .finally(() => continueRender(handle));
  }, [handle]);
}

/** A screenshot filling the frame, with a slow push-in (Ken Burns, camcorder style). */
export const Shot: React.FC<{ src: string; zoom?: [number, number]; length?: number; style?: React.CSSProperties }> = ({
  src,
  zoom = [1, 1.05],
  length = 40,
  style,
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, length], zoom, { extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ overflow: 'hidden', background: '#000' }}>
      <Img
        src={staticFile(`shots/${src}`)}
        style={{ width: WIDTH, height: HEIGHT, objectFit: 'cover', transform: `scale(${scale})`, ...style }}
      />
    </AbsoluteFill>
  );
};

/** TV snow: SVG noise with a new seed every frame. */
export const Snow: React.FC<{ opacity?: number; seed?: string }> = ({ opacity = 1, seed = 'snow' }) => {
  const frame = useCurrentFrame();
  const s = Math.floor(random(`${seed}-${frame}`) * 1000);
  return (
    <AbsoluteFill style={{ opacity, background: '#000' }}>
      <svg width={WIDTH} height={HEIGHT}>
        <filter id={`snow-${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={s} />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="linear" slope="1" />
            <feFuncR type="linear" slope="1.6" intercept="-0.3" />
            <feFuncG type="linear" slope="1.6" intercept="-0.3" />
            <feFuncB type="linear" slope="1.6" intercept="-0.3" />
          </feComponentTransfer>
        </filter>
        <rect width={WIDTH} height={HEIGHT} filter={`url(#snow-${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

/**
 * The caption of a scene: VCR letters typed one by one with a block cursor,
 * on a band at the bottom, then gone.
 */
export const Caption: React.FC<{ text: string; sub?: string; from?: number; to?: number; top?: number }> = ({
  text,
  sub,
  from = 6,
  to = 52,
  top,
}) => {
  const frame = useCurrentFrame();
  if (frame < from || frame >= to) return null;
  const t = frame - from;
  const shown = text.slice(0, Math.floor(t * 1.6) + 1);
  const typing = shown.length < text.length;
  const blink = Math.floor(t / 6) % 2 === 0;
  const out = interpolate(frame, [to - 5, to], [1, 0], { extrapolateLeft: 'clamp' });
  return (
    <AbsoluteFill style={{ justifyContent: top === undefined ? 'flex-end' : 'flex-start', alignItems: 'center' }}>
      <div
        style={{
          marginBottom: top === undefined ? 46 : 0,
          marginTop: top ?? 0,
          padding: '10px 22px 6px',
          background: 'rgba(0, 0, 40, 0.72)',
          border: '3px solid #fff',
          boxShadow: '6px 6px 0 #ff2fb4',
          opacity: out,
          transform: `scaleY(${out})`,
          fontFamily: VCR,
          color: '#fff',
          textAlign: 'center',
          textShadow: '3px 3px 0 #0018ff',
        }}
      >
        <div style={{ fontSize: 46, letterSpacing: 2, whiteSpace: 'pre' }}>
          {shown}
          <span style={{ opacity: typing || blink ? 1 : 0 }}>█</span>
        </div>
        {sub && !typing && <div style={{ fontSize: 26, color: '#ffe23a', marginTop: 4 }}>{sub}</div>}
      </div>
    </AbsoluteFill>
  );
};

/**
 * The CRT layer on top of everything: scanlines, a rolling bright band,
 * grain, flicker, vignette and rounded tube corners.
 */
export const Crt: React.FC = () => {
  const frame = useCurrentFrame();
  const flicker = 0.02 + random(`flicker-${frame}`) * 0.04;
  const roll = ((frame * 6) % (HEIGHT + 300)) - 150;
  const seed = Math.floor(random(`grain-${frame}`) * 1000);
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <AbsoluteFill
        style={{
          background: 'repeating-linear-gradient(to bottom, rgba(0,0,0,0.28) 0px, rgba(0,0,0,0.28) 1px, transparent 1px, transparent 3px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: roll,
          height: 150,
          background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,0.06), transparent)',
        }}
      />
      <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', opacity: 0.07, mixBlendMode: 'screen' }}>
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves={1} seed={seed} />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width={WIDTH} height={HEIGHT} filter="url(#grain)" />
      </svg>
      <AbsoluteFill style={{ background: '#fff', opacity: flicker * 0.5 }} />
      <AbsoluteFill
        style={{ background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)' }}
      />
      {/* The tube: rounded corners in a black bezel. */}
      <AbsoluteFill style={{ borderRadius: 40, boxShadow: '0 0 0 40px #000, inset 0 0 40px rgba(0,0,0,0.8)' }} />
    </AbsoluteFill>
  );
};

/** Red/blue fringes (the colour bleeding of an old tube), as an SVG filter for the picture. */
export const RgbFilter: React.FC = () => (
  <svg width={0} height={0} style={{ position: 'absolute' }}>
    <filter id="rgb" x="0" y="0" width="100%" height="100%" colorInterpolationFilters="sRGB">
      <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
      <feOffset in="r" dx="1.2" dy="0" result="r2" />
      <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g" />
      <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b" />
      <feOffset in="b" dx="-1.2" dy="0" result="b2" />
      <feBlend in="r2" in2="g" mode="screen" result="rg" />
      <feBlend in="rg" in2="b2" mode="screen" />
    </filter>
  </svg>
);

/** A tilted, framed inset (a phone screen or a small TV) with a hard 90s shadow. */
export const Inset: React.FC<{
  src: string;
  x: number;
  y: number;
  height: number;
  ratio: number;
  rotate?: number;
  phone?: boolean;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ src, x, y, height, ratio, rotate = 0, phone = false, style, children }) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: height * ratio,
      height,
      transform: `rotate(${rotate}deg)`,
      border: phone ? '12px solid #111' : '12px solid #d8d2bf',
      borderRadius: phone ? 34 : 18,
      boxShadow: '12px 12px 0 rgba(0,0,0,0.55)',
      overflow: 'hidden',
      background: '#000',
      ...style,
    }}
  >
    <Img
      src={staticFile(`shots/${src}`)}
      style={{ width: '100%', height: '100%', objectFit: 'cover', transform: phone ? 'scale(1.06)' : undefined }}
    />
    {children}
  </div>
);

/** 90s backdrop for the phone scenes: purple sky and a moving neon grid floor. */
export const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: 'linear-gradient(to bottom, #12002e 0%, #3a0a6b 55%, #ff2fb4 56%, #12002e 57%)' }}>
      <div
        style={{
          position: 'absolute',
          left: -WIDTH,
          right: -WIDTH,
          top: HEIGHT * 0.56,
          height: HEIGHT,
          transformOrigin: 'top',
          transform: 'perspective(400px) rotateX(70deg)',
          backgroundImage:
            'linear-gradient(#ff2fb4 2px, transparent 2px), linear-gradient(90deg, #ff2fb4 2px, transparent 2px)',
          backgroundSize: '80px 80px',
          backgroundPosition: `0 ${(frame * 4) % 80}px`,
          opacity: 0.8,
        }}
      />
    </AbsoluteFill>
  );
};
