/**
 * REWIND demo for the README: 50 s, 4:3, one scene per feature, cheap-camcorder
 * transitions, the app's pixel cursor clicking around, sound effects, and a
 * CRT layer on top. Screenshots come from public/shots (scripts/capture.mjs),
 * the music from assets/background.mp3 (looped on the beat, see timeline.ts).
 */
import { AbsoluteFill, Img, interpolate, random, Sequence, staticFile, useCurrentFrame } from 'remotion';
import { Backdrop, Caption, Crt, Inset, RgbFilter, Shot, Snow, useVcrFont, VCR } from './effects';
import { Cursor, Music, Sfx } from './motion';
import { HEIGHT, SCENES, TRANSITION, WIDTH } from './timeline';
import { Enter } from './transitions';

/** Hard cuts inside a scene: [first frame, element] pairs. */
const Cuts: React.FC<{ cuts: [number, React.ReactNode][] }> = ({ cuts }) => {
  const frame = useCurrentFrame();
  let current = 0;
  cuts.forEach(([from], i) => frame >= from && (current = i));
  const [from, el] = cuts[current];
  return <Sequence from={from}>{el}</Sequence>;
};

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  // CRT power-on: a white line that opens into the picture.
  const open = interpolate(frame, [12, 20], [0.006, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const glow = interpolate(frame, [12, 26], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Sfx at={0} name="static.wav" volume={0.5} />
      <Sfx at={12} name="poweron.wav" volume={0.7} />
      {frame < 12 ? (
        <Snow seed="intro" />
      ) : (
        <AbsoluteFill style={{ transform: `scaleY(${open})` }}>
          <Sequence from={12}>
            <Shot src="intro.png" zoom={[1, 1.1]} length={86} />
          </Sequence>
          {/* Hide the settings corner and the clip's watermark. */}
          <div style={{ position: 'absolute', left: 790, top: 0, width: 170, height: 100, background: '#000' }} />
          <div style={{ position: 'absolute', left: 800, top: 650, width: 160, height: 70, background: '#000' }} />
          <AbsoluteFill style={{ background: '#fff', opacity: glow }} />
        </AbsoluteFill>
      )}
      <Caption text="80s/90s TV FOR YOUR MINI PC" from={40} to={96} />
    </AbsoluteFill>
  );
};

const Channels: React.FC = () => (
  <AbsoluteFill>
    <Sfx at={0} name="sparkle.wav" volume={0.5} />
    <Cuts
      cuts={[
        [0, <Shot src="grid.png" zoom={[1.06, 1]} length={70} />],
        [70, <Snow seed="zap1" />],
        [74, <Shot src="billiard.png" length={70} />],
        [144, <Snow seed="zap2" />],
        [148, <Shot src="basketball.png" length={30} />],
        [178, <Shot src="basketball-volume.png" zoom={[1.03, 1.06]} />],
      ]}
    />
    <Cursor path={[{ f: 14, x: 900, y: 700 }, { f: 44, x: 480, y: 330 }, { f: 66, x: 482, y: 334 }]} clicks={[52]} until={70} />
    <Sfx at={70} name="static.wav" volume={0.5} />
    <Sfx at={144} name="static.wav" volume={0.5} />
    {[178, 184, 190, 196].map((f, i) => (
      <Sfx key={f} at={f} name="tick.wav" volume={0.4 + i * 0.1} />
    ))}
    <Caption text="YOUR OWN CHANNELS" sub="YouTube playlists, zapped like in 1993" from={80} to={170} />
  </AbsoluteFill>
);

const Movies: React.FC = () => (
  <AbsoluteFill>
    <Sfx at={0} name="whoosh.wav" />
    <Cuts
      cuts={[
        [0, <Shot src="demolition-detail.png" zoom={[1, 1]} />],
        [76, <Snow seed="play" />],
        [79, <Shot src="demolition-playing.png" zoom={[1, 1.12]} length={70} />],
        [150, <Shot src="series-detail.png" zoom={[1, 1.04]} length={70} />],
      ]}
    />
    <Cursor
      path={[
        { f: 8, x: 620, y: 560 },
        { f: 26, x: 300, y: 150 },
        { f: 36, x: 300, y: 150 },
        { f: 62, x: 777, y: 452 },
        { f: 74, x: 777, y: 452 },
      ]}
      clicks={[30, 68]}
      until={76}
    />
    <Caption text="MOVIES & SERIES" sub="downloaded, subtitled, resumed where you stopped" from={86} to={160} />
  </AbsoluteFill>
);

/** The three picks pop in one by one: the empty "thinking" screen hides the others. */
const AdvisorResults: React.FC = () => {
  const frame = useCurrentFrame();
  const shown = Math.min(3, Math.floor(frame / 8) + 1);
  const left = [0, 340, 628, 960][shown];
  return (
    <AbsoluteFill>
      <Shot src="advisor-results.png" zoom={[1, 1.05]} length={110} />
      {shown < 3 && (
        <AbsoluteFill style={{ clipPath: `polygon(${left}px 55px, 960px 55px, 960px 690px, ${left}px 690px)` }}>
          <Shot src="advisor-thinking.png" zoom={[1, 1.05]} length={110} />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

const Advisor: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Cuts
        cuts={[
          [0, <Shot src="advisor-criteria.png" zoom={[1, 1.03]} length={64} />],
          [64, <Shot src="advisor-thinking.png" zoom={[1.1, 1.1]} />],
          [104, <AdvisorResults />],
        ]}
      />
      {/* "is thinking…": the dots keep coming. */}
      {frame >= 64 && frame < 104 && (
        <div
          style={{
            position: 'absolute',
            left: 400,
            top: 70,
            width: 60,
            height: 30,
            background: 'rgb(0, 7, 66)',
            opacity: Math.floor(frame / 6) % 2,
          }}
        />
      )}
      <Cursor path={[{ f: 10, x: 900, y: 300 }, { f: 44, x: 756, y: 606 }, { f: 62, x: 756, y: 606 }]} clicks={[52]} until={64} />
      {[104, 112, 120].map((f) => (
        <Sfx key={f} at={f} name="tick.wav" volume={0.6} />
      ))}
      <Caption text="AI MOVIE ADVISOR" sub="Michael Harper picks three films for your mood" from={124} to={214} top={14} />
    </AbsoluteFill>
  );
};

/** IR waves from the top of the phone to the TV, emitted at `starts`. */
const Waves: React.FC<{ x: number; y: number; starts: number[] }> = ({ x, y, starts }) => {
  const frame = useCurrentFrame();
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {starts.map((start, n) => {
        const t = (frame - start) / 26;
        if (t < 0 || t > 1) return null;
        const r = 20 + t * 420;
        // Arcs facing the TV (down-left of the phone's IR window).
        const a0 = (118 * Math.PI) / 180;
        const a1 = (188 * Math.PI) / 180;
        const d = `M ${x + r * Math.cos(a0)} ${y + r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${x + r * Math.cos(a1)} ${y + r * Math.sin(a1)}`;
        return (
          <path
            key={start}
            d={d}
            fill="none"
            stroke={n % 2 ? '#3ff7ff' : '#ffe23a'}
            strokeWidth={10}
            strokeLinecap="round"
            opacity={1 - t}
            style={{ filter: 'drop-shadow(0 0 8px #fff)' }}
          />
        );
      })}
    </svg>
  );
};

const KeyGlow: React.FC<{ left: number; top: number }> = ({ left, top }) => (
  <div
    style={{
      position: 'absolute',
      left: `${left}%`,
      top: `${top}%`,
      width: 70,
      height: 70,
      borderRadius: '50%',
      transform: 'translate(-50%, -50%)',
      background: 'radial-gradient(circle, rgba(255,255,255,0.9), rgba(255,226,58,0.4) 60%, transparent 70%)',
    }}
  />
);

const RemoteScene: React.FC = () => {
  const frame = useCurrentFrame();
  const phone = { x: 640, y: 60, h: 600 };
  const ratio = 780 / 1688;
  // Key 2 at 20, the TV zaps to Basketball at 54; key 5 at 110, back to Billiard at 144.
  const tvShot = frame >= 144 ? 'billiard.png' : frame >= 54 ? 'basketball.png' : 'billiard.png';
  const zapping = (frame >= 54 && frame < 58) || (frame >= 144 && frame < 148);
  const waves = [22, 29, 36, 43, 112, 119, 126, 133];
  return (
    <AbsoluteFill>
      <Backdrop />
      <Inset src={tvShot} x={40} y={150} height={420} ratio={4 / 3} rotate={-3}>
        {zapping && <Snow seed={`remote-zap-${frame}`} />}
      </Inset>
      <Inset src="remote.png" x={phone.x} y={phone.y} height={phone.h} ratio={ratio} rotate={5} phone>
        {frame >= 16 && frame < 28 && <KeyGlow left={38.8} top={25.8} />}
        {frame >= 106 && frame < 118 && <KeyGlow left={38.8} top={36.6} />}
      </Inset>
      <Waves x={phone.x + 12 + (phone.h * ratio) / 2 - 20} y={phone.y + 30} starts={waves} />
      <Cursor path={[{ f: 4, x: 820, y: 700 }, { f: 16, x: 760, y: 232 }, { f: 90, x: 760, y: 232 }, { f: 104, x: 765, y: 297 }]} clicks={[18, 108]} until={180} />
      {[20, 110].map((f) => (
        <Sfx key={f} at={f} name="beam.wav" volume={0.5} />
      ))}
      <Sfx at={54} name="static.wav" volume={0.45} />
      <Sfx at={144} name="static.wav" volume={0.45} />
      <Caption text="YOUR PHONE IS THE REMOTE" sub="or any USB remote: REWIND learns its keys" from={60} to={196} top={14} />
    </AbsoluteFill>
  );
};

const Admin: React.FC = () => {
  const frame = useCurrentFrame();
  const ratio = 780 / 1688;
  const slide = (start: number, fromX: number, toX: number) =>
    interpolate(frame, [start, start + 10], [fromX, toX], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill>
      <Backdrop />
      <Sfx at={4} name="whoosh.wav" />
      <Inset src="admin-channel-edit.png" x={slide(4, -400, 150)} y={50} height={620} ratio={ratio} rotate={-5} phone />
      {frame >= 60 && (
        <>
          <Sfx at={60} name="whoosh.wav" />
          <Inset src="admin-alarm.png" x={slide(60, WIDTH + 50, 500)} y={40} height={620} ratio={ratio} rotate={5} phone />
        </>
      )}
      <Caption text="SET UP FROM YOUR PHONE" sub="channels, alarm, movies… no keyboard needed" from={20} to={156} />
    </AbsoluteFill>
  );
};

const Alarm: React.FC = () => {
  const frame = useCurrentFrame();
  // The alarm rings: the picture shakes like an old bell clock.
  const shake = frame < 60 ? Math.sin(frame * 2.4) * 1.4 : 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `rotate(${shake}deg) scale(1.04)` }}>
        <Cuts
          cuts={[
            [0, <Shot src="alarm-ringing.png" length={60} />],
            [60, <Shot src="alarm-screen.png" length={60} />],
          ]}
        />
      </AbsoluteFill>
      <Sfx at={0} name="bells.mp3" volume={0.5} />
      <Caption text="WAKES YOU UP" sub="gently: a chime, then your channel" from={8} to={116} top={14} />
    </AbsoluteFill>
  );
};

const Weather: React.FC = () => {
  const frame = useCurrentFrame();
  const pop = interpolate(frame, [34, 42], [0.6, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill>
      {frame < 34 ? (
        <Shot src="grid.png" zoom={[1, 1]} />
      ) : (
        <AbsoluteFill>
          <Shot src="billiard.png" style={{ filter: 'brightness(0.45)' }} />
          <AbsoluteFill style={{ mixBlendMode: 'lighten', transform: `scale(${pop})` }}>
            <Shot src="weather.png" zoom={[1, 1.04]} length={66} />
          </AbsoluteFill>
        </AbsoluteFill>
      )}
      <Cursor path={[{ f: 6, x: 420, y: 560 }, { f: 24, x: 640, y: 648 }, { f: 33, x: 640, y: 648 }]} clicks={[28]} until={34} />
      <Sfx at={34} name="whoosh.wav" volume={0.5} />
      <Caption text="LOCAL FORECAST" sub="the Weather Channel look" from={40} to={100} top={14} />
    </AbsoluteFill>
  );
};

const REW_SHOTS = [
  'weather.png', 'alarm-screen.png', 'alarm-ringing.png', 'advisor-results.png', 'advisor-criteria.png',
  'series-detail.png', 'demolition-playing.png', 'demolition-detail.png', 'basketball-volume.png',
  'billiard.png', 'grid.png', 'intro.png',
]; // prettier-ignore

const Rewind: React.FC = () => {
  const frame = useCurrentFrame();
  const src = REW_SHOTS[Math.min(REW_SHOTS.length - 1, Math.floor(frame / 2))];
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Img src={staticFile(`shots/${src}`)} style={{ width: WIDTH, height: HEIGHT, filter: 'saturate(1.4) contrast(1.2)' }} />
      {Array.from({ length: 6 }, (_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: random(`rew-y-${frame}-${i}`) * HEIGHT,
            height: 6 + random(`rew-h-${frame}-${i}`) * 26,
            background: 'rgba(255,255,255,0.75)',
            mixBlendMode: 'difference',
            transform: `translateX(${(random(`rew-x-${frame}-${i}`) - 0.5) * 80}px)`,
          }}
        />
      ))}
      <div style={{ position: 'absolute', left: 70, top: 56, fontFamily: VCR, fontSize: 60, color: '#fff', textShadow: '3px 3px 0 #000' }}>
        ◀◀ REW
      </div>
    </AbsoluteFill>
  );
};

const COMMAND = 'wget -qO- …/install.sh | bash';
const OUTPUT = ['REWIND installer', '[ OK ] cage, Chromium, ffmpeg', '[ OK ] REWIND in /opt/rewind', 'Reboot: the TV starts on REWIND.'];

/** A 90s xterm typing the one-line install, on a desk-blue backdrop. */
const Terminal: React.FC = () => {
  const frame = useCurrentFrame();
  const typed = COMMAND.slice(0, Math.max(0, Math.floor((frame - 8) * 1.1)));
  const doneTyping = typed.length === COMMAND.length;
  const enterAt = 8 + Math.ceil(COMMAND.length / 1.1) + 6;
  const lines = frame < enterAt ? 0 : Math.min(OUTPUT.length, Math.floor((frame - enterAt) / 7) + 1);
  const blink = Math.floor(frame / 8) % 2 === 0;
  const keys = Array.from({ length: COMMAND.length }, (_, i) => 8 + Math.floor(i / 1.1)).filter((f, i, a) => a.indexOf(f) === i);
  const green = '#5dff7a';
  return (
    <AbsoluteFill style={{ background: 'radial-gradient(circle at 50% 40%, #2a3fd0, #0a1060)' }}>
      {keys.map((f, i) => (
        <Sfx key={f} at={f} name={`key${i % 4}.wav`} volume={0.5} />
      ))}
      <Sfx at={enterAt - 2} name="click.wav" volume={0.5} />
      <div
        style={{
          position: 'absolute',
          left: 70,
          top: 170,
          width: 820,
          height: 400,
          background: '#c8c8c8',
          border: '3px solid #000',
          boxShadow: 'inset 3px 3px 0 #fff, inset -3px -3px 0 #777, 12px 12px 0 rgba(0,0,0,0.55)',
        }}
      >
        <div
          style={{
            height: 40,
            margin: 6,
            background: 'linear-gradient(90deg, #00007a, #1084d0)',
            color: '#fff',
            fontFamily: VCR,
            fontSize: 26,
            display: 'flex',
            alignItems: 'center',
            paddingLeft: 12,
          }}
        >
          xterm — tv@mini-pc: ~
        </div>
        <div
          style={{
            position: 'absolute',
            left: 12,
            right: 12,
            top: 56,
            bottom: 12,
            background: '#050805',
            border: '3px solid #000',
            padding: '18px 22px',
            fontFamily: VCR,
            fontSize: 30,
            lineHeight: '42px',
            color: green,
            textShadow: `0 0 8px ${green}`,
            whiteSpace: 'pre',
          }}
        >
          <div>
            <span style={{ color: '#fff' }}>tv@mini-pc:~$ </span>
            {typed}
            {(!doneTyping || frame < enterAt) && <span style={{ opacity: blink ? 1 : 0 }}>█</span>}
          </div>
          {OUTPUT.slice(0, lines).map((l) => (
            <div key={l} style={{ color: l.startsWith('[') ? green : '#fff' }}>
              {l}
            </div>
          ))}
        </div>
      </div>
      <Caption text="INSTALLS WITH ONE COMMAND" sub="Debian 13 · Raspberry Pi OS" from={4} to={200} top={40} />
    </AbsoluteFill>
  );
};

const End: React.FC = () => {
  const frame = useCurrentFrame();
  // The very end: "End of broadcast", then the tube switches off (line, then dot).
  const offY = interpolate(frame, [142, 148], [1, 0.006], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const offX = interpolate(frame, [148, 153], [1, 0.01], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Sfx at={0} name="rewind.wav" volume={0.7} />
      <Cuts
        cuts={[
          [0, <Rewind />],
          [24, <Terminal />],
          [116, <Snow seed="end" />],
          [
            120,
            <AbsoluteFill style={{ transform: `scale(${offX}, ${offY})`, filter: frame >= 142 ? 'brightness(3)' : undefined }}>
              <Shot src="end.png" zoom={[1, 1.03]} length={36} />
            </AbsoluteFill>,
          ],
        ]}
      />
      <Sfx at={116} name="static.wav" volume={0.4} />
    </AbsoluteFill>
  );
};

const VIEWS: Record<string, React.FC> = {
  intro: Intro,
  channels: Channels,
  movies: Movies,
  advisor: Advisor,
  remote: RemoteScene,
  admin: Admin,
  alarm: Alarm,
  weather: Weather,
  end: End,
};

/** A scene in its slot, entering with its transition over the previous one. */
const Scene: React.FC<{ index: number }> = ({ index }) => {
  const frame = useCurrentFrame();
  const s = SCENES[index];
  const View = VIEWS[s.id];
  const p = index === 0 || s.enter === 'rewind' ? 1 : Math.min(1, frame / TRANSITION);
  return (
    <Enter kind={s.enter} p={p} id={s.id}>
      <View />
    </Enter>
  );
};

export const Demo: React.FC = () => {
  useVcrFont();
  const last = SCENES[SCENES.length - 1].to;
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <RgbFilter />
      <AbsoluteFill style={{ filter: 'url(#rgb)' }}>
        {SCENES.map((s, i) => (
          <Sequence
            key={s.id}
            from={s.from}
            durationInFrames={Math.min(last, s.to + (i < SCENES.length - 1 ? TRANSITION : 0)) - s.from}
          >
            <Scene index={i} />
          </Sequence>
        ))}
      </AbsoluteFill>
      <Crt />
      <Music fadeOut={30} />
    </AbsoluteFill>
  );
};
