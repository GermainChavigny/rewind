#!/usr/bin/env bash
# Build the release tarball that install.sh downloads: dist/rewind.tar.gz
# (+ dist/install.sh, published next to it as a release asset).
#
#   scripts/build-release.sh          version from backend/src/rewind/__init__.py
#
# The tarball is architecture-independent: the Python dependencies are
# installed on the TV by pip from the hashed requirements.txt, and native ones
# come from apt (python3-libtorrent, ffmpeg, cage, chromium…).
#
# Layout of rewind-<version>/:
#   VERSION  install.sh  requirements.txt  rewind-<version>-py3-none-any.whl
#   frontend/   the built UI (served by the backend)
#   deploy/     kiosk, systemd units, polkit rule, boot menu, apt packages
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UV="${UV:-uv}"; command -v "$UV" >/dev/null || UV="$HOME/.local/bin/uv"
NPM="${NPM:-npm}"; [ -x "$HOME/.local/bin/npm" ] && NPM="$HOME/.local/bin/npm"
OUT="${OUT:-$ROOT/dist}"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/backend/src/rewind/__init__.py")"
PYPROJECT_VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/backend/pyproject.toml")"
[ -n "$VERSION" ] || { echo "cannot read __version__" >&2; exit 1; }
[ "$VERSION" = "$PYPROJECT_VERSION" ] || {
  echo "version mismatch: __init__.py $VERSION, pyproject.toml $PYPROJECT_VERSION" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
DIR="$STAGE/rewind-$VERSION"
mkdir -p "$DIR" "$OUT"

echo "== REWIND $VERSION"
echo "== frontend"
(cd "$ROOT/frontend" && "$NPM" ci --silent && "$NPM" run -s build)
cp -r "$ROOT/frontend/dist" "$DIR/frontend"

echo "== backend wheel + requirements"
(cd "$ROOT/backend" && "$UV" build --quiet --wheel --out-dir "$DIR")
rm -f "$DIR/.gitignore"
# libtorrent comes from apt (python3-libtorrent): one package for every arch.
(cd "$ROOT/backend" && "$UV" export --quiet --frozen --no-dev --no-emit-project \
  --no-emit-package libtorrent --no-header -o "$DIR/requirements.txt")

echo "== deploy files"
mkdir -p "$DIR/deploy"
mkdir -p "$DIR/deploy/kiosk" && cp "$ROOT/deploy/kiosk/rewind-kiosk" "$DIR/deploy/kiosk/"
cp -r "$ROOT/deploy/systemd" "$ROOT/deploy/polkit" "$DIR/deploy/"
mkdir -p "$DIR/deploy/boot"
cp "$ROOT/deploy/boot/rewind-boot" "$ROOT/deploy/boot/tv-switch" \
   "$ROOT/deploy/boot/install-boot-menu" "$DIR/deploy/boot/"
cp "$ROOT/deploy/apt-packages" "$DIR/deploy/"
cp "$ROOT/deploy/install.sh" "$DIR/install.sh"
cp "$ROOT/LICENSE" "$DIR/"
echo "$VERSION" > "$DIR/VERSION"

tar -C "$STAGE" -czf "$OUT/rewind.tar.gz" "rewind-$VERSION"
cp "$ROOT/deploy/install.sh" "$OUT/install.sh"
echo "Built $OUT/rewind.tar.gz ($(du -h "$OUT/rewind.tar.gz" | cut -f1)) and $OUT/install.sh"
