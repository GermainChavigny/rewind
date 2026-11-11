# Architecture

```
backend/   Python 3.11+ · FastAPI · SQLite — API, also serves the built UI
frontend/  Svelte 5 · TypeScript · Vite — TV interface (720×576) and phone admin
deploy/    boot menu, systemd services, kiosk (cage + Chromium)
docs/      documentation
```

## Languages

Code, comments, docs and logs are in English. The user interface is in French
first; every UI string goes through the i18n layer so it can be translated.

## Locations

| Variable | Default | Contents |
|---|---|---|
| `REWIND_DATA_DIR` | `~/.local/share/rewind` | SQLite database, posters, imports |
| `REWIND_CONFIG_DIR` | `~/.config/rewind` | `config.toml` |
| `REWIND_MEDIA_DIR` | `<data>/media` | movies and series |

## v1 / v2 side by side

While v2 is being developed, v1 stays in daily use:

- `deploy/boot/rewind-boot`: teletext-style menu on tty1, driven by the remote;
  boots v1 by default after 5 s. Install with `deploy/boot/install-boot-menu`
  (undo with `--remove`).
- `tv-switch v1|v2 [--now]`: change the default program.
- `rewind import-v1`: snapshot of the v1 data + hardlinks to `~/movies`.
  v1 is never modified.
- v2 listens on port 8080 (v1 uses 5000 and 8000).

See [v1-behaviors.md](v1-behaviors.md) for the checklist of v1 details to carry over.
