# Architecture

```
backend/   Python 3.11+ · FastAPI · SQLite — API + sert l'interface compilée
frontend/  Svelte 5 · TypeScript · Vite — interface TV (720×576) et admin mobile
deploy/    menu de démarrage, services systemd, kiosque (cage + Chromium)
docs/      documentation
```

## Emplacements

| Variable | Défaut | Contenu |
|---|---|---|
| `REWIND_DATA_DIR` | `~/.local/share/rewind` | base SQLite, affiches, imports |
| `REWIND_CONFIG_DIR` | `~/.config/rewind` | `config.toml` |
| `REWIND_MEDIA_DIR` | `<data>/media` | films et séries |

## Cohabitation v1 / v2

Pendant le développement, la v1 reste utilisée au quotidien :

- `deploy/boot/rewind-boot` : menu télétexte sur tty1, pilotable à la
  télécommande ; lance la v1 par défaut au bout de 5 s.
  Installation : `deploy/boot/install-boot-menu` (réversible avec `--remove`).
- `tv-switch v1|v2 [--now]` : change le programme par défaut.
- `rewind import-v1` : instantané des données v1 + liens physiques vers
  `~/movies`. La v1 n'est jamais modifiée.
- La v2 écoute sur le port 8080 (v1 : 5000 et 8000).
