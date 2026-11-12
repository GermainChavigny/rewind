# REWIND

> An 80s/90s TV experience for your mini PC: channels, a movie and series
> library, alarm clock, weather… dressed up like a real channel of the era.

**🚧 Work in progress (v2)** — see the [roadmap](docs/roadmap.md).

The user interface is in French for now; it is built for translation (i18n).

## Principles

- **CRT first**: a 4:3 interface at 720×576, readable from the couch. Works on
  HD screens too (4:3 pillarboxed UI, 16:9 movies full screen).
- **Easy to install**: Debian + one command, then everything is configured from
  a phone (`http://tv.local`).
- **Modular**: each feature (YouTube channels, movies, series, alarm, weather,
  smart plug…) only shows up once it is configured.

## Installation

On a mini PC with **Debian 13** (amd64) or a **Raspberry Pi 4/5** with
**Raspberry Pi OS Lite 64-bit**, plugged into the TV and connected to the
network, log in as the user who will own the TV and run:

```bash
wget -qO- https://github.com/GermainChavigny/rewind/releases/latest/download/install.sh | bash
```

(or `curl -fsSL <same URL> | bash`). It asks for your password once (sudo),
installs what it needs (cage, Chromium, ffmpeg…) and REWIND in `/opt/rewind`.
Then reboot: the TV starts on REWIND and shows a QR code. Scan it with your
phone to finish the setup (`http://<tv-ip>:8080/admin/`).

No sudo on this user? Run it as root with `bash -s -- --user <name>`.

### Updates

From the phone: **Réglages → Mise à jour**. Or on the TV computer:

```bash
/opt/rewind/install.sh update       # latest release
/opt/rewind/install.sh rollback     # back to the previous one
```

Updates never touch your settings and library (`~/.config/rewind`,
`~/.local/share/rewind`). An update that needs new system packages asks you to
run `/opt/rewind/install.sh update` yourself on the TV (sudo).

### What it sets up

- `rewind.service`: the backend, a systemd **user** service on port 8080.
- `rewind-kiosk.service`: cage + Chromium on tty1, in place of the login
  prompt (other consoles: Ctrl+Alt+F2).
- [Jackett](https://github.com/Jackett/Jackett) (`jackett.service`, user
  service on port 9117), already connected to REWIND: to search movies, add
  sites from the phone (**Films et séries → Ouvrir Jackett**). A Jackett that
  is already there is reused.
- uBlock Origin Lite for the YouTube channels, a polkit rule so the phone's
  power key can turn the computer off, and `rewind` in `/usr/local/bin`.

Options (after `bash -s --`): `--kiosk service|boot-menu|none`, `--port N`,
`--no-ublock`, `--no-jackett`, `--version X.Y.Z`, `--from rewind.tar.gz`. If REWIND v1's boot
menu is installed, the installer keeps it and its v2 entry starts the cage kiosk.

### Uninstall

```bash
/opt/rewind/install.sh uninstall            # keeps settings and library
/opt/rewind/install.sh uninstall --purge    # removes them too
```

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

On the TV, a checkout can run without installing: `deploy/kiosk/start-v2`
(an X session with the backend and Chromium, from the tty1 console).

### Releases

Bump the version in `backend/src/rewind/__init__.py` and
`backend/pyproject.toml`, commit, then `scripts/release.sh`: it runs the
checks, builds `dist/rewind.tar.gz` (UI, wheel, hashed requirements, deploy
files: one archive for amd64 and arm64) and publishes it with `install.sh` as
a GitHub release. `scripts/build-release.sh` only builds.

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
