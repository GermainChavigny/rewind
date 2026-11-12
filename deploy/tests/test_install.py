"""
Run deploy/install.sh for real in a throw-away root: install, update, rollback,
uninstall. sudo, apt, systemctl, loginctl and GitHub are stubbed; the files the
installer writes (releases, units, polkit rule, symlinks) are checked.

Run with: python3 deploy/tests/test_install.py
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[1]
INSTALL = DEPLOY / "install.sh"
REAL_PYTHON = shutil.which("python3")

STUBS = {
    # Root commands just run (everything stays inside the temporary tree).
    "sudo": 'if [ "$1" = -v ] || [ "$1" = -n ]; then exit 0; fi; exec "$@"',
    "apt-get": 'echo "apt-get $*" >> "$STUB_LOG"',
    "systemctl": 'echo "systemctl $*" >> "$STUB_LOG"',
    "loginctl": 'echo "loginctl $*" >> "$STUB_LOG"; [ "$1" = show-user ] && echo no; exit 0',
    "chown": 'echo "chown $*" >> "$STUB_LOG"',
    "hostname": "echo 192.0.2.10",
    "dpkg": "echo amd64",
    # Every package is installed except the ones listed in $MISSING_PKGS.
    "dpkg-query": 'for p in $MISSING_PKGS; do [ "$p" = "$3" ] && exit 1; done; '
    'printf "install ok installed"',
    # python3 -m venv DIR → a fake venv whose pip only logs.
    "python3": f"""
if [ "$1" = -m ] && [ "$2" = venv ]; then
  for d; do dir="$d"; done
  mkdir -p "$dir/bin"
  printf '#!/bin/sh\\necho "pip $*" >> "$STUB_LOG"\\n' > "$dir/bin/pip"
  printf '#!/bin/sh\\nexit 0\\n' > "$dir/bin/python"
  printf '#!/bin/sh\\necho rewind\\n' > "$dir/bin/rewind"
  chmod +x "$dir/bin/"*
  exit 0
fi
exec {REAL_PYTHON} "$@"
""",
    # GitHub: the API answers from $GH_DIR/<path>, assets are local files.
    "curl": r"""
out= url=
while [ $# -gt 0 ]; do
  case "$1" in -o) out="$2"; shift ;; -H) shift ;; -*) ;; *) url="$1" ;; esac
  shift
done
echo "curl $url" >> "$STUB_LOG"
case "$url" in
  https://api.github.com/repos/*/releases/assets/*) cp "$GH_DIR/assets/${url##*/}" "$out" ;;
  https://api.github.com/*) f="$GH_DIR/${url#https://api.github.com/}.json"; [ -f "$f" ] || exit 22; cp "$f" "$out" ;;
  *) exit 22 ;;
esac
""",
}


class Box:
    """A fake TV: stub commands, a home, /opt/rewind and / inside a temp dir."""

    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rewind-install-"))
        self.bin = self.tmp / "bin"
        self.home = self.tmp / "home"
        self.prefix = self.tmp / "opt" / "rewind"
        self.sysroot = self.tmp / "root"
        self.gh = self.tmp / "github"
        self.log = self.tmp / "stub.log"
        for d in (self.bin, self.home, self.sysroot / "etc/systemd/system", self.gh / "assets"):
            d.mkdir(parents=True)
        self.log.touch()
        for name, body in STUBS.items():
            path = self.bin / name
            path.write_text("#!/bin/bash\n" + body + "\n")
            path.chmod(0o755)
        self.missing = ""

    def release(self, version: str) -> Path:
        """A minimal release tarball, laid out like scripts/build-release.sh's."""
        top = self.tmp / "build" / f"rewind-{version}"
        (top / "frontend").mkdir(parents=True)
        (top / "frontend" / "index.html").write_text("<html></html>")
        shutil.copytree(DEPLOY / "kiosk", top / "deploy" / "kiosk")
        shutil.copytree(DEPLOY / "systemd", top / "deploy" / "systemd")
        shutil.copytree(DEPLOY / "polkit", top / "deploy" / "polkit")
        shutil.copy(DEPLOY / "apt-packages", top / "deploy" / "apt-packages")
        shutil.copy(INSTALL, top / "install.sh")
        (top / "requirements.txt").write_text("fastapi==0 \\\n    --hash=sha256:00\n")
        (top / f"rewind-{version}-py3-none-any.whl").write_text("wheel")
        (top / "VERSION").write_text(version + "\n")
        tarball = self.tmp / f"rewind-{version}.tar.gz"
        with tarfile.open(tarball, "w:gz") as tar:
            tar.add(top, arcname=top.name)
        shutil.rmtree(top)
        return tarball

    def publish(self, version: str) -> None:
        """Makes `version` the latest GitHub release."""
        asset_id = version.replace(".", "")
        shutil.copy(self.release(version), self.gh / "assets" / asset_id)
        api = self.gh / "repos" / "GermainChavigny" / "rewind" / "releases"
        api.mkdir(parents=True, exist_ok=True)
        (api / "latest.json").write_text(
            json.dumps(
                {
                    "tag_name": f"v{version}",
                    "assets": [
                        {
                            "name": "rewind.tar.gz",
                            "url": "https://api.github.com/repos/GermainChavigny/rewind"
                            f"/releases/assets/{asset_id}",
                        }
                    ],
                }
            )
        )

    def run(self, *args: str, script: Path | None = None, check: bool = True):
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "REWIND_USER_HOME": str(self.home),
            "REWIND_PREFIX": str(self.prefix),
            "REWIND_SYSROOT": str(self.sysroot),
            "REWIND_PYTHON": str(self.bin / "python3"),
            "XDG_RUNTIME_DIR": str(self.tmp),
            "STUB_LOG": str(self.log),
            "GH_DIR": str(self.gh),
            "MISSING_PKGS": self.missing,
        }
        proc = subprocess.run(
            ["bash", str(script or INSTALL), *args],
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
        )
        if check and proc.returncode != 0:
            raise AssertionError(f"install.sh {args} failed:\n{proc.stdout}\n{proc.stderr}")
        return proc

    def version(self) -> str:
        return (self.prefix / "current" / "VERSION").read_text().strip()

    def releases(self) -> list[str]:
        return sorted(p.name for p in (self.prefix / "releases").iterdir())

    def calls(self) -> str:
        return self.log.read_text()

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def test_fresh_install_sets_up_the_kiosk_service():
    box = Box()
    try:
        box.missing = "cage wlr-randr"
        out = box.run("install", "--from", str(box.release("0.5.0")), "--no-ublock").stdout
        assert box.version() == "0.5.0"
        rel = box.prefix / "current"
        assert (rel / ".complete").is_file() and (rel / "frontend" / "index.html").is_file()
        assert (box.prefix / "install.sh").stat().st_mode & 0o111
        env = (box.prefix / "rewind.env").read_text()
        assert "REWIND_PORT=8080" in env and f"REWIND_INSTALL_DIR={box.prefix}" in env

        unit = (box.home / ".config/systemd/user/rewind.service").read_text()
        assert f"ExecStart={box.prefix}/current/venv/bin/rewind serve" in unit
        kiosk = (box.sysroot / "etc/systemd/system/rewind-kiosk.service").read_text()
        user = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()
        assert f"User={user}" in kiosk and "@" not in kiosk.split("[Service]")[1]
        rule = (box.sysroot / "etc/polkit-1/rules.d/50-rewind.rules").read_text()
        assert f'subject.user == "{user}"' in rule
        link = box.sysroot / "usr/local/bin/rewind"
        assert os.readlink(link) == f"{box.prefix}/current/venv/bin/rewind"

        calls = box.calls()
        assert "apt-get install -y -q --no-install-recommends cage wlr-randr" in calls
        assert "--require-hashes -r" in calls
        assert "systemctl enable --quiet rewind-kiosk.service" in calls
        assert "systemctl --user enable --quiet rewind.service" in calls
        assert f"loginctl enable-linger {user}" in calls
        assert "sudo reboot" in out and "/admin/" in out
    finally:
        box.cleanup()


def test_next_to_v1_the_boot_menu_is_kept():
    box = Box()
    try:
        (box.home / ".bash_profile").write_text("# Generated by REWIND (install-boot-menu).\n")
        out = box.run("--from", str(box.release("0.5.0")), "--no-ublock").stdout
        assert (box.prefix / ".state" / "kiosk").read_text().strip() == "boot-menu"
        assert not (box.sysroot / "etc/systemd/system/rewind-kiosk.service").exists()
        assert "rewind-kiosk.service" not in box.calls()
        # The backend is not started at boot: the kiosk starts it when v2 is picked.
        assert "systemctl --user enable" not in box.calls()
        assert "boot menu" in out
    finally:
        box.cleanup()


def test_update_rollback_and_pruning():
    box = Box()
    try:
        box.run("--from", str(box.release("0.5.0")), "--no-ublock")
        updater = box.prefix / "install.sh"

        box.publish("0.5.0")
        assert "up to date" in box.run("update", script=updater).stdout
        assert json.loads((box.prefix / "update.json").read_text())["state"] == "done"

        box.publish("0.5.1")
        box.run("update", script=updater)
        assert box.version() == "0.5.1"
        status = json.loads((box.prefix / "update.json").read_text())
        assert status["state"] == "done" and status["version"] == "0.5.1"
        assert "systemctl --user restart rewind.service" in box.calls()

        box.publish("0.6.0")
        box.run("update", script=updater)
        assert box.version() == "0.6.0"
        names = box.releases()
        assert len(names) == 2 and names[0].startswith("0.5.1-"), names

        box.run("rollback", script=updater)
        assert box.version() == "0.5.1"
        assert "0.5.1 in" in box.run("status", script=updater).stdout
    finally:
        box.cleanup()


def test_update_needing_new_packages_waits_for_root():
    box = Box()
    try:
        box.run("--from", str(box.release("0.5.0")), "--no-ublock")
        box.publish("0.5.1")
        box.missing = "cage"
        proc = box.run("update", script=box.prefix / "install.sh", check=False)
        assert proc.returncode != 0
        assert box.version() == "0.5.0"
        status = json.loads((box.prefix / "update.json").read_text())
        assert status["state"] == "failed" and "cage" in status["message"]
    finally:
        box.cleanup()


def test_interrupted_build_is_never_rolled_back_to():
    box = Box()
    try:
        box.run("--from", str(box.release("0.5.0")), "--no-ublock")
        (box.prefix / "releases" / "0.4.9-broken").mkdir()  # no .complete
        proc = box.run("rollback", script=box.prefix / "install.sh", check=False)
        assert proc.returncode != 0 and "no previous release" in proc.stderr
        assert box.version() == "0.5.0"
    finally:
        box.cleanup()


def test_uninstall_keeps_the_library():
    box = Box()
    try:
        box.run("--from", str(box.release("0.5.0")), "--no-ublock")
        data = box.home / ".local/share/rewind"
        data.mkdir(parents=True)
        (data / "rewind.db").write_text("db")
        box.run("uninstall", "--yes", script=box.prefix / "install.sh")
        assert not box.prefix.exists()
        assert not (box.sysroot / "etc/systemd/system/rewind-kiosk.service").exists()
        assert not (box.sysroot / "etc/polkit-1/rules.d/50-rewind.rules").exists()
        assert not (box.sysroot / "usr/local/bin/rewind").is_symlink()
        assert not (box.home / ".config/systemd/user/rewind.service").exists()
        assert (data / "rewind.db").is_file()
        assert "loginctl disable-linger" in box.calls()
    finally:
        box.cleanup()


if __name__ == "__main__":
    failed = 0
    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            try:
                test()
                print(f"ok    {name}")
            except AssertionError as err:
                failed += 1
                print(f"FAIL  {name}: {err}")
    sys.exit(1 if failed else 0)
