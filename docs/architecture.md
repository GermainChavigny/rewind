# Architecture

```
backend/   Python 3.11+ · FastAPI · SQLite — API, also serves the built UI
frontend/  Svelte 5 · TypeScript · Vite — TV interface (720×576) and phone admin
deploy/    boot menu, systemd services, kiosk (cage + Chromium)
docs/      documentation
```

## TV interface

The UI is laid out on a fixed **720×576 stage** (the CRT's PAL mode) and scaled
into a 4:3 frame (`frontend/src/lib/stage.ts`): scale 1 on the CRT (v1 sizes
kept), pillarboxed on 16:9 screens. Videos (intro, YouTube, movies) are not on
the stage: they always fill the screen. Layers, bottom to top: video, stage
(grid, screens, "technical difficulties" card), darkness veil, stage (OSDs),
retro cursor. State and remote behaviour live in `frontend/src/lib/tv.svelte.ts`.

Screens: one full screen at a time (`tv.screen`: alarm, library, results,
series, advisor) and an overlay above it (`tv.overlay`: weather popup, on-screen
keyboard). The movie screens share a footer with the Films / Recherche / Advisor
shortcuts; a playing movie shows the pause screen and the subtitle / next
episode HUDs. Movie playback is `lib/movie.svelte.ts`, the catalog and the job
polling `lib/library.svelte.ts`.

Errors are shown as a "TECHNICAL DIFFICULTIES — please stand by" card.

## Languages

Code, comments, docs and logs are in English. The user interface is in French
first; every UI string goes through the i18n layer so it can be translated.

## Locations

| Variable | Default | Contents |
|---|---|---|
| `REWIND_DATA_DIR` | `~/.local/share/rewind` | SQLite database, posters, imports |
| `REWIND_CONFIG_DIR` | `~/.config/rewind` | `config.toml` |
| `REWIND_MEDIA_DIR` | `<data>/media` | movies and series |

## Configuration

`config.toml` (mode 0600, it holds API keys) is validated by the pydantic models
in `backend/src/rewind/config.py`. It is meant to be edited from the phone admin
UI (`/api/admin/config`, secrets masked as `********`), but stays hand-editable.
Set `[admin] pin` to protect the admin API (`X-Rewind-Pin` header).

Hardware-free development: `[power] provider = "fake"`.

## Modules

Each feature is a module that reports whether it is configured
(`GET /api/modules`). The TV UI only shows configured modules; routes of an
unconfigured module answer 404.

| Module | Configured when | Routes |
|---|---|---|
| channels | at least one channel | `/api/channels`, `/api/progress/{playlist}` |
| alarm | a channel has `alarm = true` | `/api/alarm` |
| power | `[power]` provider set | `/api/tv/power` |
| weather | latitude + longitude set | `/api/weather` |
| library | `[library] enabled` | `/api/library…`, `/api/series…`, `/api/advisor…`, `/api/posters/{id}`, `/media/{file}` |

Inside the library, `GET /api/library/features` tells the UI what else is
configured: `search` (an indexer + libtorrent), `series` (an indexer + a TMDB
key), `advisor` (an AI provider). Unconfigured parts answer 503.

## Library pipeline

`backend/src/rewind/library/`: a movie job goes magnet → libtorrent download
(several in parallel) → subtitles (embedded fr/en extracted to WebVTT, missing
languages from OpenSubtitles by moviehash, re-timed with ffsubsync) → ffmpeg
(remux, audio-only or full re-encode: one at a time) → ready. Series downloads
are "packs" (an episode, a season or the whole show) whose files are mapped to
episodes; episodes missing from a season pack fall back to single-episode
searches. Job state lives in the database, so jobs resume after a reboot.
Downloads are staged in `<data>/downloads` and removed once converted.

Always available: `/api/health`, `/api/state` (darkness, volume — persisted),
`/api/admin/*`.

## Storage

SQLite (`<data>/rewind.db`, WAL), schema migrations tracked with
`PRAGMA user_version` in `backend/src/rewind/db.py`. Media items keep their
indexed fields in columns and the rest (metadata, subtitles, job state) in a
JSON `data` column.

## v1 / v2 side by side

While v2 is being developed, v1 stays in daily use:

- `deploy/boot/rewind-boot`: teletext-style menu on tty1, driven by the remote;
  boots v1 by default after 5 s. Install with `deploy/boot/install-boot-menu`
  (undo with `--remove`).
- `tv-switch v1|v2 [--now]`: change the default program.
- `rewind import-v1`: snapshot of the v1 data + hardlinks to `~/movies`, then
  rebuilds the v2 database from it (alarm, YouTube progress, library). The first
  run also generates `config.toml` from the values v1 hardcoded (channels,
  Shelly IP, weather location, A/V offset, video output, API keys);
  `--overwrite-config` regenerates it. v1 is never modified.
- v2 listens on port 8080 (v1 uses 5000 and 8000).
- `deploy/kiosk/start-v2`: temporary X session for v2 (backend + Chromium
  kiosk with uBlock Origin Lite), launched by the boot menu. Replaced by the
  cage kiosk in phase 5.

See [v1-behaviors.md](v1-behaviors.md) for the checklist of v1 details to carry over.

## Third-party assets to check before going public

The fonts (VCR OSD Mono, Home Video Bold), the intro video, the sounds and the
Movie Advisor critic picture (`frontend/public/img/advisor-critic.gif`) come
from v1; their licenses must be verified before the repository is made public.

## Retro channel logos

Channel logos are drawn by `ChannelLogo.svelte`: a background
chosen by channel number and variant (`frontend/public/img/channels/v{1,2}/{n}.webp`,
cut from the boards in `assets/channel-logos` by `scripts/cut-channel-logos.py`)
with the channel name written over it in CSS, each style matching the
reference boards (`assets/channel-logos/ref-*.jpg`). Each channel picks
`logo_style` 1 or 2; v1 image logos are not used. The boards were generated
by the project owner. The logo fonts (Exo 2, Oswald, Libre Bodoni, Cinzel,
Kaushan Script, Silkscreen, Doto, Audiowide) are SIL OFL fonts from Google
Fonts, bundled in `frontend/public/fonts`. `frontend/dev/logos.html` (dev
server only) shows the 18 logos under the references, `?name=` to try a name.

## Phone admin, virtual remote, TV events

- `/admin/` (phone settings) and `/remote/` (virtual remote) are separate Vite
  pages next to the TV UI.
- The TV page listens to `GET /api/tv/events` (Server-Sent Events, `events.py`):
  virtual remote presses (`POST /api/remote/press`, same actions as the keymap,
  plus `home`), touchpad moves and clicks (`/api/remote/pointer`), text typed
  on the phone (`/api/remote/text`), the end-of-broadcast card before a
  shutdown, the A/V sync test (flash + beep, `AvSyncTest.svelte`) and chime
  previews. Key learning still uses polling (`/api/remote/learn`).
- The other way round, the TV reports what it shows (`PUT /api/tv/report`:
  movies or not, the on-screen keyboard and its text) and the phone remotes
  follow it on `GET /api/remote/events` (`routes/remote.py`).
- The virtual remote has two modes, each with its own layout in the database
  (`kv.remote_layout`, `kv.remote_layout.movies`): "tv" (channels, alarm…)
  and "movies" (transport keys, a touchpad, `home` to leave the movies for
  the welcome screen). When the TV keyboard is open, a text field on the
  phone opens the phone's own keyboard.
- Touchpad: the page cannot move the system cursor, so `lib/vpointer.ts`
  plays the mouse itself (position, mouse/pointer events, clicks) and copies
  every `:hover` CSS rule as a `.v-hover` rule. No system tool: works under
  X11, cage/Wayland and on a dev Mac.
- Computer power key (`POST /api/remote/shutdown`, `system.py`, after a
  confirmation on the phone): end-of-broadcast card, `systemctl poweroff`,
  then the TV plug off. `[system] shutdown = "fake"` only logs it (sandbox,
  dev), `"none"` hides the key. polkit lets the active local session's user
  power off without a password; a systemd user service is not in that
  session, so phase 5 will need a polkit rule for the kiosk user.
- Settings QR code: on the welcome screen (intro, or the channel grid of a
  paused channel) a corner button or → shows a QR code of
  `http://<lan-ip>:<port>/admin/` (`/api/remote/admin-url`). It shows by
  itself until the setup wizard is finished (`/api/ui` `first_run`).
- The REWIND brand mark (`components/Brand.svelte`, Roboto, SIL OFL) copies
  the intro video's logo; every place showing the name as a logo uses it.
- `hardware.py` lists video connectors/modes (DRM sysfs) and audio output ports
  (`pactl`), and applies the A/V offset live (`pactl set-port-latency-offset`)
  on save and while tuning; the video mode is applied at session start
  (`deploy/kiosk/xinitrc-v2`).
- `checks.py`: the admin "Test" buttons (TMDB, OpenSubtitles, Jackett, AI
  providers, Shelly plug) and AI model lists, run with the settings as typed.
- Alarm chimes: `frontend/public/audio/chimes/*.mp3`. `classic` is the v1 chime;
  the others are synthesised by `scripts/make-chimes.py` (no third-party audio).
  With a chime, the alarm works without an alarm channel.
