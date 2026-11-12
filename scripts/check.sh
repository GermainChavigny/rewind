#!/usr/bin/env bash
# Run every check the CI runs, locally (lint, types, tests, build).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UV="${UV:-uv}"; command -v "$UV" >/dev/null || UV="$HOME/.local/bin/uv"
NPM="${NPM:-npm}"; [ -x "$HOME/.local/bin/npm" ] && NPM="$HOME/.local/bin/npm"

echo "== backend"
cd "$ROOT/backend"
"$UV" sync -q
"$UV" run ruff check .
"$UV" run ruff format --check .
"$UV" run pytest -q -p no:warnings

echo "== frontend"
cd "$ROOT/frontend"
"$NPM" run -s check
"$NPM" test --silent
"$NPM" run -s build

echo "== deploy scripts"
cd "$ROOT"
bash -n deploy/boot/rewind-boot deploy/boot/tv-switch deploy/boot/install-boot-menu
bash -n deploy/install.sh scripts/build-release.sh scripts/release.sh
sh -n deploy/kiosk/start-v2 deploy/kiosk/xinitrc-v2 deploy/kiosk/rewind-kiosk
python3 deploy/boot/tests/test_rewind_boot.py
python3 deploy/tests/test_install.py

echo "All checks passed."
