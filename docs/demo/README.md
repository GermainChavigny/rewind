# Demo video

The 50-second video at the top of the main README, made with
[Remotion](https://www.remotion.dev/) (React, rendered frame by frame) from
real screenshots of REWIND. Cheap-camcorder transitions, the app's pixel-art
cursor clicking around, sound effects, a CRT layer, the
[VCR OSD Mono](https://www.dafont.com/vcr-osd-mono.font) font, and
`assets/background.mp3` looped on the beat as the soundtrack.

Requirements: Node 20+. Remotion downloads its own headless Chromium; the
captures use the system one (`CHROMIUM`).

```bash
cd docs/demo
npm install
npm run prepare-assets      # copies the music, cursors and chime, downloads the font (any OS)
npm run studio              # live preview in the browser, scrub the timeline
npm run preview             # half-size render, quick check → out/preview.mp4
npm run render              # final render → out/rewind-demo.mp4
```

## Screenshots

`public/shots/` holds the screenshots the video uses (committed, so the video
can be rendered without a running REWIND). To refresh them, run a sandbox
REWIND (English UI, weather set, channels and a library), then:

```bash
REWIND_URL=http://127.0.0.1:8081 REWIND_PIN=<pin> npm run capture   # → captures/
```

The script drives the TV page (960×720, the 4:3 frame), the phone remote and
the admin, and writes every step to `captures/`. Copy the ones the video uses
into `public/shots/` under the names `src/Demo.tsx` expects. It sets the alarm
to ring a minute later, plays a movie and sends a shutdown: use a sandbox
whose `[system] shutdown` and `[power] provider` are `"fake"`.

The sound effects in `public/sfx/*.wav` are synthesized by
`scripts/make-sfx.py` (numpy).

`npm run studio` plays the video in your browser (frames are drawn by your
browser), `npm run render` renders on the machine that runs it: run it on a
fast computer, it takes a while.

## Cut list

`src/timeline.ts`: the music is 90 BPM (a beat every 20 frames at 30 fps) and
every cut lands on a beat. It is looped (two jumps back of 4 bars, where it
sounds the same, with a short crossfade) to give the scenes time. Each scene names the transition it enters with
(`src/transitions.tsx`).

## Putting it in the README

GitHub only plays videos uploaded as attachments: edit the README on
github.com, drag `out/rewind-demo.mp4` into the editor, and keep the
`https://github.com/user-attachments/assets/…` link it inserts.
