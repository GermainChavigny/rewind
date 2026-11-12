#!/usr/bin/env bash
# Publish a GitHub release: scripts/release.sh
#
# Version from backend/src/rewind/__init__.py (bump it, and pyproject.toml,
# first). Runs the checks, builds dist/rewind.tar.gz + dist/install.sh, tags
# v<version> and uploads both: install.sh then finds them at
# releases/latest/download/. Release notes: docs/release-notes/<version>.md if
# present, else GitHub's generated notes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' backend/src/rewind/__init__.py)"
TAG="v$VERSION"
[ -z "$(git status --porcelain)" ] || { echo "Commit your changes first." >&2; exit 1; }
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && { echo "$TAG already exists." >&2; exit 1; }

scripts/check.sh
scripts/build-release.sh

NOTES=(--generate-notes)
[ -f "docs/release-notes/$VERSION.md" ] && NOTES=(--notes-file "docs/release-notes/$VERSION.md")
git tag -a "$TAG" -m "REWIND $VERSION"
git push origin "$TAG"
gh release create "$TAG" dist/rewind.tar.gz dist/install.sh --title "REWIND $VERSION" "${NOTES[@]}"
echo "Released $TAG."
