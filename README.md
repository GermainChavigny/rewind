# REWIND

> An 80s/90s TV experience for your mini PC: channels, a movie and series
> library, alarm clock, weather… dressed up like a real channel of the era.

**🚧 Work in progress (v2).** Installation is manual for now (see
[Installation](#installation)); the one-command install lands in phase 5 — see
the [roadmap](docs/roadmap.md).

The user interface is in French for now; it is built for translation (i18n).

## Principles

- **CRT first**: a 4:3 interface at 720×576, readable from the couch. Works on
  HD screens too (4:3 pillarboxed UI, 16:9 movies full screen).
- **Easy to install**: Debian + one command, then everything is configured from
  a phone (`http://tv.local`).
- **Modular**: each feature (YouTube channels, movies, series, alarm, weather,
  smart plug…) only shows up once it is configured.

## Installation

Target: a mini PC on **Debian 13** (amd64), plugged into the TV, with a user
that logs in automatically on the console (tty1). Raspberry Pi OS Lite 64-bit
(Pi 4/5) will be supported by the installer in phase 5.

> Until `install.sh` exists (phase 5), these steps are manual. The X + openbox
> kiosk below is temporary and will be replaced by a cage kiosk.

### 1. System packages

```bash
sudo apt install git curl ffmpeg chromium xserver-xorg xinit openbox \
                 unclutter pulseaudio pulseaudio-utils nodejs npm
curl -LsSf https://astral.sh/uv/install.sh | sh     # installs uv in ~/.local/bin
```

Debian 13 ships Node 20.19, which is enough to build the interface.

### 2. Get REWIND and build it

Clone into `~/rewind` (the boot scripts expect this path):

```bash
git clone https://github.com/GermainChavigny/rewind.git ~/rewind
cd ~/rewind/backend && uv sync              # Python deps (Python 3.11+, fetched by uv if needed)
cd ~/rewind/frontend && npm ci && npm run build
```

### 3. Try it

From the TV console (not over SSH):

```bash
~/rewind/deploy/kiosk/start-v2
```

This starts the backend on port 8080 and Chromium in kiosk mode. On first run
the TV shows a QR code: scan it with your phone to open the settings
(`http://<tv-ip>:8080/admin/`) and follow the setup wizard. Logs go to
`~/.local/state/rewind/`.

### 4. Start it at boot

```bash
~/rewind/deploy/boot/install-boot-menu
```

On the next boot, a small menu on tty1 lets you pick v1 or v2 with the remote
(arrows + OK, or keys 1 / 2) and starts the default after 5 seconds. Change the
default with `tv-switch v2` (add `--now` to switch immediately). To remove the
menu and restore your original `~/.bash_profile`:
`~/rewind/deploy/boot/install-boot-menu --remove`.

### Where things live

| What | Default path | Override |
|---|---|---|
| Settings (`config.toml`) | `~/.config/rewind/` | `REWIND_CONFIG_DIR` |
| Database, posters, imports | `~/.local/share/rewind/` | `REWIND_DATA_DIR` |
| Movies and series | `~/.local/share/rewind/media/` | `REWIND_MEDIA_DIR` |

### Optional

- **Torrent downloads**: needs a [Jackett](https://github.com/Jackett/Jackett)
  instance; if a `jackett.service` user unit exists, the kiosk starts it.
- **Ad blocking in YouTube channels**: put an unpacked uBlock Origin Lite in
  `~/ublock_extension`; it is loaded automatically when present.

### Update

```bash
cd ~/rewind && git pull
cd backend && uv sync
cd ../frontend && npm ci && npm run build
```

Then restart the session: `tv-switch v2 --now`.

## Development

Requirements: [uv](https://docs.astral.sh/uv/) (Python 3.11+) — Linux or macOS.

```bash
cd backend
uv sync
uv run pytest
# from the repo root, everything the CI checks: scripts/check.sh
uv run rewind serve          # http://localhost:8080/api/health
```

And the TV interface (Node 20.19+):

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173 (proxies /api to :8080)
npm run build                # dist/ is then served by `rewind serve` on :8080
```

No hardware needed: set `[power] provider = "fake"` in `config.toml`.

### Sandbox (try the UI from any browser)

```bash
deploy/dev/setup-sandbox     # → http://<tv-ip>:8081
```

A second v2 instance with its own copy of the data and a **fake TV plug**, so
keys pressed in the browser never switch the real TV. Runs as a systemd user
service, even while the TV runs v1. Re-run to rebuild the UI and refresh data.
End-to-end checks against it: `deploy/dev/e2e/*.py` (Playwright).

### Migrating from v1

```bash
uv run rewind import-v1 --tv-data ~/tv_data --movies ~/movies
```

Never modifies v1: data is copied and videos are hardlinked. Safe to re-run.

## License

[GPL-3.0-or-later](LICENSE). You are responsible for how you use the content
sources you configure.
