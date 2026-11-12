#!/usr/bin/env bash
# REWIND installer — Debian 13 (amd64) and Raspberry Pi OS Lite 64-bit (Pi 4/5).
#
#   curl -fsSL https://github.com/GermainChavigny/rewind/releases/latest/download/install.sh | bash
#
# Run it as the user who will own the TV (it asks for the sudo password), or as
# root with --user NAME. After the first install it lives in /opt/rewind:
#
#   /opt/rewind/install.sh update       install the latest release (no root needed)
#   /opt/rewind/install.sh rollback     go back to the previous release
#   /opt/rewind/install.sh status       installed version, kiosk mode
#   /opt/rewind/install.sh uninstall    remove REWIND (keeps your data; --purge too)
#
# Without curl (stock Debian): wget -qO- <same URL> | bash
# Options after `| bash -s --`, e.g. `| bash -s -- --kiosk boot-menu`.
# While the repository is private, set GITHUB_TOKEN (kept for the updates).
#
# Options: --from FILE (a local rewind.tar.gz), --version X.Y.Z, --user NAME,
#          --kiosk service|boot-menu|none, --port N, --no-ublock, --no-jackett, --yes
#
# Layout: /opt/rewind/releases/<version>-<timestamp>/ (venv, frontend, deploy),
# /opt/rewind/current → the active one, owned by the TV user so that updates
# from the phone need no password. Settings and data stay in the user's
# ~/.config/rewind and ~/.local/share/rewind, untouched by updates.
set -euo pipefail

REPO="${REWIND_REPO:-GermainChavigny/rewind}"
PREFIX="${REWIND_PREFIX:-/opt/rewind}"
SYSROOT="${REWIND_SYSROOT:-}"     # tests: fake root for /etc and /usr/local
PYTHON="${REWIND_PYTHON:-python3}"
ASSET="rewind.tar.gz"
KEEP_RELEASES=2

# --- output ----------------------------------------------------------------------

if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B= G= Y= R= N=; fi
step() { printf '%s==>%s %s\n' "$B" "$N" "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '%s!!%s  %s\n' "$Y" "$N" "$*" >&2; }
die() { printf '%sError:%s %s\n' "$R" "$N" "$*" >&2; state failed "$*"; exit 1; }

usage() { sed -n '2,24p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

# --- arguments -------------------------------------------------------------------

CMD=install FROM= WANT_VERSION= TARGET_USER= KIOSK=auto PORT= UBLOCK=1 JACKETT=1 YES=0 PURGE=0
WITH_JACKETT_DEPS=0   # only the first install adds Jackett's system library (ICU)
case "${1:-}" in
  install|update|rollback|status|uninstall) CMD="$1"; shift ;;
esac
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="$(realpath "$2")"; shift ;;
    --version) WANT_VERSION="${2#v}"; shift ;;
    --user) TARGET_USER="$2"; shift ;;
    --kiosk) KIOSK="$2"; shift ;;
    --port) PORT="$2"; shift ;;
    --no-ublock) UBLOCK=0 ;;
    --no-jackett) JACKETT=0 ;;
    --purge) PURGE=1 ;;
    -y|--yes) YES=1 ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; usage 2 ;;
  esac
  shift
done
case "$KIOSK" in auto|service|boot-menu|none) ;; *) die "--kiosk must be service, boot-menu or none" ;; esac

# --- who does what ---------------------------------------------------------------

if [ "$(id -u)" = 0 ]; then
  TARGET_USER="${TARGET_USER:-${SUDO_USER:-}}"
  [ -n "$TARGET_USER" ] && [ "$TARGET_USER" != root ] ||
    { echo "Run as root, pass --user NAME: the TV user (not root)." >&2; exit 2; }
  AS_ROOT=1
else
  if [ -n "$TARGET_USER" ] && [ "$TARGET_USER" != "$(id -un)" ]; then
    echo "--user is only for root; run the installer as $TARGET_USER instead." >&2; exit 2
  fi
  TARGET_USER="$(id -un)"
  AS_ROOT=0
fi
USER_HOME="${REWIND_USER_HOME:-$(getent passwd "$TARGET_USER" | cut -d: -f6)}"
[ -d "$USER_HOME" ] || { echo "No home directory for $TARGET_USER." >&2; exit 2; }
USER_UID="$(id -u "$TARGET_USER")"
DATA_DIR="$USER_HOME/.local/share/rewind"
UNIT_DIR="$USER_HOME/.config/systemd/user"
STATE_DIR="$PREFIX/.state"

# Root commands: direct as root, through sudo otherwise.
root() {
  if [ "$AS_ROOT" = 1 ]; then "$@"; else sudo "$@"; fi
}
# Commands for the TV user: direct as that user, runuser as root.
as_user() {
  if [ "$AS_ROOT" = 1 ]; then runuser -u "$TARGET_USER" -- env HOME="$USER_HOME" "$@"; else "$@"; fi
}
user_systemctl() {
  if [ "$AS_ROOT" = 1 ]; then systemctl --user -M "$TARGET_USER@" "$@"
  else XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$USER_UID}" systemctl --user "$@"; fi
}

# update.json: what the phone admin shows while an update runs.
state() {
  [ "$CMD" = update ] && [ -d "$PREFIX" ] && [ -w "$PREFIX" ] || return 0
  local msg="${2:-}"
  msg="${msg//\\/\\\\}"; msg="${msg//\"/\\\"}"
  printf '{"state": "%s", "message": "%s", "version": "%s", "time": %s}\n' \
    "$1" "$msg" "${NEW_VERSION:-}" "$(date +%s)" > "$PREFIX/update.json.tmp" &&
    mv -f "$PREFIX/update.json.tmp" "$PREFIX/update.json"
}

# --- downloads -------------------------------------------------------------------

TOKEN="${GITHUB_TOKEN:-}"
[ -z "$TOKEN" ] && [ -r "$PREFIX/github-token" ] && TOKEN="$(cat "$PREFIX/github-token")"

fetch() { # fetch URL OUT [accept]
  local url="$1" out="$2" accept="${3:-application/vnd.github+json}" auth=()
  if [ -n "$TOKEN" ] && [[ "$url" == https://api.github.com/* ]]; then auth=(-H "Authorization: Bearer $TOKEN"); fi
  if command -v curl >/dev/null; then
    curl -fsSL --retry 3 -H "Accept: $accept" "${auth[@]}" -o "$out" "$url"
  elif command -v wget >/dev/null; then
    local wauth=(); [ ${#auth[@]} -gt 0 ] && wauth=(--header "${auth[1]}")
    wget -q --tries=3 --header "Accept: $accept" "${wauth[@]}" -O "$out" "$url"
  else
    die "neither curl nor wget is installed (sudo apt install curl)"
  fi
}

# Prints "<version> <asset api url>" of the wanted (or latest) release.
release_info() {
  local api="https://api.github.com/repos/$REPO/releases/latest" json
  [ -n "$WANT_VERSION" ] && api="https://api.github.com/repos/$REPO/releases/tags/v$WANT_VERSION"
  json="$WORK/release.json"
  fetch "$api" "$json" || die "cannot reach GitHub ($api). Private repository? Set GITHUB_TOKEN."
  "$PYTHON" - "$json" "$ASSET" <<'PY'
import json, sys
release = json.load(open(sys.argv[1]))
asset = next((a for a in release.get("assets", []) if a["name"] == sys.argv[2]), None)
if asset is None:
    sys.exit(f"release {release.get('tag_name')} has no {sys.argv[2]}")
print(release["tag_name"].lstrip("v"), asset["url"])
PY
}

# Downloads (or copies) the release and unpacks it; sets SRC and NEW_VERSION.
get_release() {
  local tarball="$WORK/$ASSET"
  if [ -n "$FROM" ]; then
    cp "$FROM" "$tarball"
  else
    local info url
    info="$(release_info)" || die "no usable release found"
    url="${info#* }"
    step "Downloading REWIND ${info%% *}"
    fetch "$url" "$tarball" application/octet-stream || die "download failed: $url"
  fi
  tar -xzf "$tarball" -C "$WORK" || die "corrupt archive"
  SRC="$(find "$WORK" -mindepth 1 -maxdepth 1 -type d -name 'rewind-*' | head -1)"
  [ -n "$SRC" ] && [ -f "$SRC/VERSION" ] || die "not a REWIND release archive"
  NEW_VERSION="$(cat "$SRC/VERSION")"
}

latest_version() {
  local info; info="$(release_info)" || return 1
  echo "${info%% *}"
}

current_version() { cat "$PREFIX/current/VERSION" 2>/dev/null || true; }

# --- system checks and packages --------------------------------------------------

check_system() {
  [ "$(uname -s)" = Linux ] || die "REWIND runs on Linux (Debian 13 or Raspberry Pi OS)"
  command -v apt-get >/dev/null || die "apt not found: Debian 13 or Raspberry Pi OS (64-bit) is required"
  local arch; arch="$(dpkg --print-architecture)"
  case "$arch" in amd64|arm64) ;; *) die "unsupported architecture $arch (amd64 or arm64)";; esac
  "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null ||
    die "Python 3.11+ is required (Debian 13 / Raspberry Pi OS trixie)"
}

wanted_packages() {
  grep -v '^\s*#' "$SRC/deploy/apt-packages" | sed '/^\s*$/d'
  # Jackett (.NET) needs ICU, whose package name carries its version (libicu76…).
  if [ "$WITH_JACKETT_DEPS" = 1 ]; then
    apt-cache pkgnames libicu 2>/dev/null | grep -E '^libicu[0-9]+$' | sort -V | tail -1
  fi
  # Keep a PulseAudio that is already there (e.g. next to REWIND v1), otherwise PipeWire.
  if dpkg-query -W -f='${Status}' pulseaudio 2>/dev/null | grep -q 'install ok installed'; then
    echo pulseaudio
  else
    echo pipewire-pulse; echo wireplumber
  fi
}

missing_packages() {
  local p
  for p in $(wanted_packages); do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || echo "$p"
  done
}

install_packages() {
  local missing; missing="$(missing_packages | tr '\n' ' ')"
  if [ -z "${missing// /}" ]; then info "system packages: all there"; return; fi
  step "Installing system packages: $missing"
  root env DEBIAN_FRONTEND=noninteractive apt-get update -q
  # shellcheck disable=SC2086
  root env DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends $missing
}

# --- the release itself ----------------------------------------------------------

build_release() { # → sets REL (directory name under releases/)
  REL="$NEW_VERSION-$(date +%Y%m%d%H%M%S)"
  local dir="$PREFIX/releases/$REL"
  step "Installing REWIND $NEW_VERSION in $dir"
  as_user mkdir -p "$PREFIX/releases"
  # Built in place (venv scripts hold absolute paths); `.complete` marks a
  # usable release: an interrupted build is never activated nor rolled back to.
  as_user cp -r "$SRC" "$dir"
  as_user "$PYTHON" -m venv --system-site-packages "$dir/venv" || die "cannot create the Python environment"
  info "Python packages (a few minutes on a Raspberry Pi)…"
  as_user "$dir/venv/bin/pip" install --quiet --disable-pip-version-check --no-input \
    --require-hashes -r "$dir/requirements.txt" || die "Python packages failed to install"
  as_user "$dir/venv/bin/pip" install --quiet --disable-pip-version-check --no-input --no-deps \
    "$dir"/rewind-*.whl || die "REWIND failed to install"
  as_user "$dir/venv/bin/python" -c 'import rewind, libtorrent' ||
    die "the Python environment is broken (libtorrent missing?)"
  as_user touch "$dir/.complete"
}

activate_release() { # activate_release <dir name>
  as_user ln -sfn "releases/$1" "$PREFIX/current.new"
  as_user mv -Tf "$PREFIX/current.new" "$PREFIX/current"
  as_user cp "$PREFIX/current/install.sh" "$PREFIX/install.sh"
  as_user chmod +x "$PREFIX/install.sh"
}

current_release() { readlink "$PREFIX/current" 2>/dev/null | sed 's|^releases/||'; }

# Complete releases other than the current one, newest first.
other_releases() {
  local current d; current="$(current_release)"
  for d in $(ls -1t "$PREFIX/releases" 2>/dev/null); do
    [ "$d" != "$current" ] && [ -f "$PREFIX/releases/$d/.complete" ] && echo "$d"
  done
  return 0
}

prune_releases() {
  # Keep the current release and the previous one (for rollback).
  local keep d; keep="$(other_releases | head -n $((KEEP_RELEASES - 1)))"
  for d in $(ls -1 "$PREFIX/releases"); do
    [ "$d" = "$(current_release)" ] && continue
    printf '%s\n' "$keep" | grep -qx "$d" && continue
    as_user rm -rf "${PREFIX:?}/releases/$d"
  done
}

write_env() {
  local port="${PORT:-$(sed -n 's/^REWIND_PORT=//p' "$PREFIX/rewind.env" 2>/dev/null)}"
  as_user tee "$PREFIX/rewind.env" >/dev/null <<ENV
# Written by install.sh. Read by rewind.service and the kiosk.
REWIND_PORT=${port:-8080}
REWIND_INSTALL_DIR=$PREFIX
REWIND_FRONTEND_DIR=$PREFIX/current/frontend
REWIND_REPO=$REPO
ENV
}

install_user_unit() {
  as_user mkdir -p "$UNIT_DIR"
  sed "s|@PREFIX@|$PREFIX|g" "$PREFIX/current/deploy/systemd/rewind.service" |
    as_user tee "$UNIT_DIR/rewind.service" >/dev/null
  user_systemctl daemon-reload
}

restart_backend() {
  if [ "$(kiosk_mode)" = service ]; then
    user_systemctl enable --quiet rewind.service
    user_systemctl restart rewind.service
  else
    # Next to v1 (boot menu): the kiosk starts it when v2 is chosen.
    user_systemctl try-restart rewind.service || true
  fi
}

kiosk_mode() { cat "$STATE_DIR/kiosk" 2>/dev/null || echo none; }

# --- uBlock Origin Lite (ads in the YouTube channels) ----------------------------

install_ublock() {
  [ "$UBLOCK" = 1 ] || return 0
  [ -f "$USER_HOME/ublock_extension/manifest.json" ] && return 0   # v1's copy, also used by v2
  [ -f "$DATA_DIR/ublock/manifest.json" ] && return 0
  step "Downloading uBlock Origin Lite (blocks YouTube ads)"
  local json="$WORK/ubol.json" zip="$WORK/ubol.zip" url
  local saved="$TOKEN"; TOKEN=""   # a public repository: never send our token there
  if fetch https://api.github.com/repos/uBlockOrigin/uBOL-home/releases/latest "$json" &&
     url="$("$PYTHON" -c 'import json,sys
r = json.load(open(sys.argv[1]))
print(next(a["browser_download_url"] for a in r["assets"] if a["name"].endswith(".chromium.zip")))' "$json")" &&
     fetch "$url" "$zip" application/octet-stream; then
    as_user mkdir -p "$DATA_DIR/ublock"
    as_user "$PYTHON" -m zipfile -e "$zip" "$DATA_DIR/ublock/" && info "uBlock Origin Lite installed"
  else
    warn "uBlock Origin Lite could not be downloaded: YouTube channels will show ads"
  fi
  TOKEN="$saved"
}

# --- Jackett (torrent indexer for the movie search) -----------------------------

JACKETT_UNIT="jackett.service"

install_jackett() {
  [ "$JACKETT" = 1 ] || return 0
  local unit="$UNIT_DIR/$JACKETT_UNIT" dir= origin
  if [ -f "$unit" ]; then
    origin="$(cat "$STATE_DIR/jackett" 2>/dev/null || echo external)"
    info "Jackett: already installed ($JACKETT_UNIT)"
  elif [ -x "$USER_HOME/Jackett/jackett_launcher.sh" ]; then
    origin=external dir="$USER_HOME/Jackett"
    info "Jackett: using $dir"
  else
    origin=managed dir="$PREFIX/jackett"
    download_jackett "$dir" || { warn "Jackett could not be installed: add it later from the phone"; return 0; }
  fi
  echo "$origin" | as_user tee "$STATE_DIR/jackett" >/dev/null
  if [ -n "$dir" ]; then
    as_user mkdir -p "$UNIT_DIR"
    sed "s|@JACKETT@|$dir|g" "$SRC/deploy/systemd/jackett.service" | as_user tee "$unit" >/dev/null
    user_systemctl daemon-reload
  fi
  user_systemctl enable --quiet "$JACKETT_UNIT"
  user_systemctl start "$JACKETT_UNIT" || true
  jackett_into_rewind
}

download_jackett() { # download_jackett <dir>
  local arch json="$WORK/jackett.json" tarball="$WORK/jackett.tar.gz" url
  case "$(dpkg --print-architecture)" in amd64) arch=LinuxAMDx64 ;; arm64) arch=LinuxARM64 ;; esac
  step "Downloading Jackett (about 50 MB)"
  local saved="$TOKEN"; TOKEN=""   # a public repository: never send our token there
  fetch https://api.github.com/repos/Jackett/Jackett/releases/latest "$json" &&
    url="$("$PYTHON" -c 'import json,sys
r = json.load(open(sys.argv[1]))
print(next(a["browser_download_url"] for a in r["assets"] if a["name"] == sys.argv[2]))' \
      "$json" "Jackett.Binaries.$arch.tar.gz")" &&
    fetch "$url" "$tarball" application/octet-stream
  local ok=$?; TOKEN="$saved"
  [ $ok = 0 ] || return 1
  mkdir -p "$WORK/jackett" && tar -xzf "$tarball" -C "$WORK/jackett" || return 1
  [ -x "$WORK/jackett/Jackett/jackett_launcher.sh" ] || return 1
  as_user rm -rf "$1"
  as_user cp -r "$WORK/jackett/Jackett" "$1"
}

# Jackett writes its key on first start: put it in REWIND's settings, and let
# the phone open Jackett's page (to add sites) — it is on the home network only.
jackett_config() { # jackett_config read|allow-external
  as_user "$PYTHON" - "$USER_HOME/.config/Jackett/ServerConfig.json" "$1" <<'PY'
import json, sys
path, action = sys.argv[1:3]
try:
    cfg = json.load(open(path, encoding="utf-8-sig"))
except (OSError, ValueError):
    sys.exit(1)
if action == "allow-external":
    cfg["AllowExternal"] = True
    json.dump(cfg, open(path, "w"), indent=2)
print(cfg.get("APIKey") or "-", cfg.get("Port", 9117), int(cfg.get("AllowExternal") is True))
PY
}

jackett_into_rewind() {
  local i=0 wait="${REWIND_JACKETT_WAIT:-120}" out
  until out="$(jackett_config read 2>/dev/null)"; do
    [ $i -ge "$wait" ] && { warn "Jackett did not start: enter its key from the phone"; return 0; }
    sleep 1; i=$((i + 1))
  done
  local key port external
  read -r key port external <<< "$out"
  if [ "$external" != 1 ]; then
    # Stopped first: Jackett would write its own settings back.
    user_systemctl stop "$JACKETT_UNIT" || true
    jackett_config allow-external >/dev/null || true
    user_systemctl start "$JACKETT_UNIT" || true
  fi
  [ "$key" != - ] || return 0
  as_user "$PREFIX/current/venv/bin/rewind" setup-indexer --url "http://127.0.0.1:$port" \
    --api-key "$key" --unit "$JACKETT_UNIT" >/dev/null &&
    info "Jackett installed and connected to REWIND: add sites at http://<tv-ip>:$port"
}

# --- system integration (root, first install only) -------------------------------

detect_kiosk() {
  [ "$KIOSK" != auto ] && { echo "$KIOSK"; return; }
  if grep -q 'Generated by REWIND (install-boot-menu)' "$USER_HOME/.bash_profile" 2>/dev/null; then
    echo boot-menu   # REWIND v1 still in use on this TV: keep its boot menu
  else
    echo service
  fi
}

setup_system() {
  local mode="$1"
  step "System setup (kiosk: $mode)"
  root mkdir -p "$PREFIX"
  root chown "$TARGET_USER:" "$PREFIX"
  as_user mkdir -p "$STATE_DIR"
  echo "$mode" | as_user tee "$STATE_DIR/kiosk" >/dev/null

  # The user's services (backend, PipeWire) run without anybody logged in.
  if [ ! -f "$STATE_DIR/linger-before" ]; then
    loginctl show-user "$TARGET_USER" -p Linger --value 2>/dev/null | as_user tee "$STATE_DIR/linger-before" >/dev/null || true
  fi
  root loginctl enable-linger "$TARGET_USER"
  root systemctl start "user@$USER_UID.service" || true

  # The phone's "turn the computer off" key: the backend is a user service,
  # outside the TV's login session, so polkit needs a rule.
  root mkdir -p "$SYSROOT/etc/polkit-1/rules.d"
  sed "s|@USER@|$TARGET_USER|g" "$SRC/deploy/polkit/50-rewind.rules" |
    root tee "$SYSROOT/etc/polkit-1/rules.d/50-rewind.rules" >/dev/null

  root mkdir -p "$SYSROOT/usr/local/bin"
  root ln -sfn "$PREFIX/current/venv/bin/rewind" "$SYSROOT/usr/local/bin/rewind"

  if [ "$mode" = service ]; then
    sed -e "s|@PREFIX@|$PREFIX|g" -e "s|@USER@|$TARGET_USER|g" "$SRC/deploy/systemd/rewind-kiosk.service" |
      root tee "$SYSROOT/etc/systemd/system/rewind-kiosk.service" >/dev/null
    root systemctl daemon-reload
    root systemctl enable --quiet rewind-kiosk.service
  fi
}

# --- commands --------------------------------------------------------------------

WORK="$(mktemp -d)"; chmod 755 "$WORK"
trap 'rm -rf "$WORK"' EXIT

cmd_install() {
  check_system
  get_release
  local old; old="$(current_version)"
  [ -n "$old" ] && info "REWIND $old is installed: it will be replaced by $NEW_VERSION"
  local mode; mode="$( [ -f "$STATE_DIR/kiosk" ] && [ "$KIOSK" = auto ] && kiosk_mode || detect_kiosk)"
  [ "$JACKETT" = 1 ] && [ ! -f "$UNIT_DIR/$JACKETT_UNIT" ] && WITH_JACKETT_DEPS=1
  if [ "$AS_ROOT" = 0 ]; then
    info "Some steps need administrator rights: sudo will ask for your password."
    sudo -v || die "sudo is required (or run as root with --user NAME)"
  fi
  install_packages
  setup_system "$mode"
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    # Private repository (before the public release): updates need the token too.
    (umask 077; printf '%s\n' "$GITHUB_TOKEN" | as_user tee "$PREFIX/github-token" >/dev/null)
  fi
  build_release
  activate_release "$REL"
  write_env
  install_user_unit
  install_ublock
  install_jackett
  restart_backend
  prune_releases

  local ip; ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  local port; port="$(sed -n 's/^REWIND_PORT=//p' "$PREFIX/rewind.env")"
  printf '\n%sREWIND %s is installed.%s\n' "$G$B" "$NEW_VERSION" "$N"
  case "$mode" in
    service) info "Reboot to start the TV:  sudo reboot" ;;
    boot-menu) info "Pick REWIND v2 in the boot menu (or: tv-switch v2 --now)." ;;
    none) info "No kiosk: start the TV screen yourself with $PREFIX/current/deploy/kiosk/rewind-kiosk" ;;
  esac
  info "Then set it up from your phone: http://${ip:-<tv-ip>}:$port/admin/  (the TV shows a QR code)"
  info "Update later from the phone, or: $PREFIX/install.sh update"
}

cmd_update() {
  [ -L "$PREFIX/current" ] || die "REWIND is not installed in $PREFIX"
  check_system
  local old; old="$(current_version)"
  state running "checking"
  if [ -z "$FROM" ]; then
    NEW_VERSION="$(latest_version)" || die "cannot check for updates"
    if [ "$NEW_VERSION" = "$old" ]; then
      info "REWIND $old is up to date."; state done "up to date"; return
    fi
  fi
  state running "download"
  get_release
  local missing; missing="$(missing_packages | tr '\n' ' ')"
  if [ -n "${missing// /}" ]; then
    if [ "$AS_ROOT" = 1 ] || [ -t 0 ]; then
      install_packages
    else
      die "new system packages needed ($missing): run $PREFIX/install.sh update on the TV"
    fi
  fi
  state running "install"
  build_release
  activate_release "$REL"
  write_env
  install_user_unit
  state running "restart"
  prune_releases
  state done "updated from $old"
  info "REWIND updated: $old → $NEW_VERSION"
  # Last: this restarts the backend that may have started us (systemd-run keeps us alive).
  restart_backend
}

cmd_rollback() {
  [ -L "$PREFIX/current" ] || die "REWIND is not installed in $PREFIX"
  local prev; prev="$(other_releases | head -1)"
  [ -n "$prev" ] || die "no previous release to go back to"
  activate_release "$prev"
  write_env
  install_user_unit
  restart_backend
  info "Back to REWIND $(current_version)"
}

cmd_status() {
  if [ ! -L "$PREFIX/current" ]; then echo "REWIND is not installed in $PREFIX"; return 1; fi
  echo "REWIND $(current_version) in $PREFIX (kiosk: $(kiosk_mode), Jackett: $(cat "$STATE_DIR/jackett" 2>/dev/null || echo none))"
  echo "Releases: $(ls -1t "$PREFIX/releases" | tr '\n' ' ')"
}

cmd_uninstall() {
  [ -d "$PREFIX" ] || die "REWIND is not installed in $PREFIX"
  if [ "$YES" != 1 ]; then
    local what="the program"; [ "$PURGE" = 1 ] && what="the program AND your settings, movies and series"
    printf 'Remove %s? [y/N] ' "$what"; read -r answer < /dev/tty || answer=
    case "$answer" in y|Y|o|O|yes|oui) ;; *) echo "Cancelled."; return 1 ;; esac
  fi
  [ "$AS_ROOT" = 1 ] || sudo -v || die "sudo is required"
  local jackett; jackett="$(cat "$STATE_DIR/jackett" 2>/dev/null || true)"
  step "Removing REWIND"
  if [ "$(kiosk_mode)" = service ]; then
    root systemctl disable --now --quiet rewind-kiosk.service 2>/dev/null || true
    root rm -f "$SYSROOT/etc/systemd/system/rewind-kiosk.service"
    root systemctl daemon-reload
  fi
  user_systemctl disable --now --quiet rewind.service 2>/dev/null || true
  if [ "$jackett" = managed ]; then
    user_systemctl disable --now --quiet "$JACKETT_UNIT" 2>/dev/null || true
    as_user rm -f "$UNIT_DIR/$JACKETT_UNIT"
    [ "$PURGE" = 1 ] && as_user rm -rf "$USER_HOME/.config/Jackett"
  fi
  as_user rm -f "$UNIT_DIR/rewind.service"
  user_systemctl daemon-reload 2>/dev/null || true
  root rm -f "$SYSROOT/etc/polkit-1/rules.d/50-rewind.rules"
  [ "$(readlink "$SYSROOT/usr/local/bin/rewind" 2>/dev/null)" = "$PREFIX/current/venv/bin/rewind" ] &&
    root rm -f "$SYSROOT/usr/local/bin/rewind"
  [ "$(cat "$STATE_DIR/linger-before" 2>/dev/null)" = yes ] || root loginctl disable-linger "$TARGET_USER" || true
  root rm -rf "$PREFIX"
  if [ "$PURGE" = 1 ]; then
    as_user rm -rf "$USER_HOME/.config/rewind" "$DATA_DIR"
    info "Settings, movies and series removed."
  else
    info "Your settings and library are kept in ~/.config/rewind and ~/.local/share/rewind."
  fi
  [ "$jackett" = external ] && info "Jackett was there before REWIND: it is left as it was."
  info "System packages (cage, chromium…) are left installed."
  printf '%sREWIND removed.%s\n' "$G" "$N"
}

SRC= NEW_VERSION= REL=
"cmd_$CMD"
