# REWIND

> An 80s/90s TV experience for your mini PC: channels, a movie and series
> library, alarm clock, weather… dressed up like a real channel of the era.

**🚧 Work in progress (v2).** One-command install lands in phase 5 — see the
[roadmap](docs/roadmap.md).

The user interface is in French for now; it is built for translation (i18n).

## Principles

- **CRT first**: a 4:3 interface at 720×576, readable from the couch. Works on
  HD screens too (4:3 pillarboxed UI, 16:9 movies full screen).
- **Easy to install**: Debian + one command, then everything is configured from
  a phone (`http://tv.local`).
- **Modular**: each feature (YouTube channels, movies, series, alarm, weather,
  smart plug…) only shows up once it is configured.

## Development

Requirements: [uv](https://docs.astral.sh/uv/) (Python 3.11+) — Linux or macOS.

```bash
cd backend
uv sync
uv run pytest
uv run rewind serve          # http://localhost:8080/api/health
```

### Migrating from v1

```bash
uv run rewind import-v1 --tv-data ~/tv_data --movies ~/movies
```

Never modifies v1: data is copied and videos are hardlinked. Safe to re-run.

## License

[GPL-3.0-or-later](LICENSE). You are responsible for how you use the content
sources you configure.
