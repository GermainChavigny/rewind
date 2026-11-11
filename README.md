# REWIND

> Une télé des années 80/90 pour votre mini PC : chaînes, bibliothèque de films
> et séries, réveil, météo… avec l'habillage d'une vraie chaîne d'époque.

**🚧 En cours de développement (v2).** L'installation en une commande arrive
en phase 5 ; voir la [feuille de route](docs/roadmap.md).

## Principes

- **Pensé pour la TV cathodique** : interface 4:3 en 720×576, lisible de loin ;
  fonctionne aussi sur écran HD (4:3 centré, films 16:9 en plein écran).
- **Simple à installer** : Debian + une commande, puis tout se règle depuis un
  téléphone (`http://tv.local`).
- **Modulaire** : chaque fonction (chaînes YouTube, films, séries, réveil,
  météo, prise connectée…) n'apparaît que si elle est configurée.

## Développer

Prérequis : [uv](https://docs.astral.sh/uv/) (Python 3.11+) — Linux ou macOS.

```bash
cd backend
uv sync
uv run pytest
uv run rewind serve          # http://localhost:8080/api/health
```

### Migrer depuis la v1

```bash
uv run rewind import-v1 --tv-data ~/tv_data --movies ~/movies
```

Ne modifie jamais la v1 : copie des données + liens physiques vers les vidéos.
Relançable à volonté.

## Licence

[GPL-3.0-or-later](LICENSE). L'usage des sources de contenu que vous
configurez relève de votre responsabilité.
