

https://github.com/user-attachments/assets/8a585d3a-4aed-4e04-8cc1-e0c6815250c5



# REWIND

> Turn a mini PC and an old TV into a channel straight out of the 80s/90s.

<!-- Demo video: edit this README on github.com and drag docs/demo/out/github-demo.mp4 here. -->

## What it does

- 📺 **Your own channels** — YouTube playlists become TV channels you zap
  through like in 1993.
- 🎬 **Movies & series** — downloaded, subtitled, and resumed where you
  stopped.
- 🤖 **AI movie advisor** — tell it your mood, it picks three films for
  tonight.
- 📱 **Your phone is the remote** — or plug in any USB remote: REWIND learns
  its keys.
- ⏰ **Wakes you up** — gently: a chime, then your favorite channel.
- 🌦️ **Local forecast** — with the Weather Channel look.
- 🔌 **Turns the TV on and off** — with a smart plug, if you have one.
- ⚙️ **Set up from your phone** — no keyboard needed. Each feature only shows
  up once you've configured it.

Made for a real CRT (4:3, readable from the couch), but works just as well on
a flat screen.

## Install

On a mini PC with **Debian 13** or a **Raspberry Pi 4/5** (Raspberry Pi OS
Lite 64-bit), plugged into the TV:

```bash
wget -qO- https://github.com/GermainChavigny/rewind/releases/latest/download/install.sh | bash
```

Reboot: the TV shows a QR code. Scan it with your phone and follow the setup.

Updates are one tap away on the phone (**Settings → Update**).
To remove it: `/opt/rewind/install.sh uninstall`.

## Hacking on it

```bash
(cd backend && uv sync && uv run rewind serve)     # API on :8080
(cd frontend && npm install && npm run dev)        # TV interface on :5173
```

Set `[power] provider = "fake"` in `config.toml` if you don't have a smart
plug. The demo video lives in [docs/demo](docs/demo).

## License

[GPL-3.0-or-later](LICENSE). You are responsible for how you use the content
sources you configure.
