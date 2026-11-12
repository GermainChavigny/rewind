import json
import subprocess

import httpx
import pytest

from rewind import hardware
from rewind.updates import STALE_S, Updater, parse_version

LATEST = "https://api.github.com/repos/GermainChavigny/rewind/releases/latest"


def release(tag="v0.6.0"):
    return httpx.Response(
        200, json={"tag_name": tag, "body": "New: things\n", "html_url": "https://gh/r"}
    )


@pytest.fixture
def install_dir(tmp_path):
    d = tmp_path / "opt-rewind"
    d.mkdir()
    (d / "install.sh").write_text("#!/bin/sh\n")
    return d


def make(web, install_dir=None, now=1000.0, spawned=None):
    clock = {"now": now}
    spawned = spawned if spawned is not None else []
    updater = Updater(
        httpx.Client(transport=httpx.MockTransport(web.handler)),
        "0.5.0",
        install_dir,
        spawn=spawned.append,
        clock=lambda: clock["now"],
    )
    return updater, clock, spawned


def test_parse_version():
    assert parse_version("v0.5.10") > parse_version("0.5.9")
    assert parse_version("1.0.0-rc1") == (1, 0, 0)
    assert parse_version("dev") == (0,)


def test_newer_release_is_available(web, install_dir):
    web.routes[LATEST] = release("v0.6.0")
    updater, _, _ = make(web, install_dir)
    status = updater.status()
    assert status["current"] == "0.5.0" and status["latest"] == "0.6.0"
    assert status["available"] and status["can_update"]
    assert status["notes"] == "New: things"


def test_same_or_older_release_is_not_offered(web, install_dir):
    web.routes[LATEST] = release("v0.5.0")
    updater, _, _ = make(web, install_dir)
    assert not updater.status()["available"]


def test_latest_is_cached_unless_asked(web, install_dir):
    web.routes[LATEST] = release()
    updater, clock, _ = make(web, install_dir)
    updater.status()
    updater.status()
    assert len(web.calls) == 1
    updater.status(check=True)
    assert len(web.calls) == 2
    clock["now"] += 3601
    updater.status()
    assert len(web.calls) == 3


def test_github_down_or_no_release(web, install_dir):
    updater, _, _ = make(web, install_dir)  # FakeWeb answers 404
    status = updater.status()
    assert status["latest"] is None and status["error"] == "no_release"
    web.routes[LATEST] = httpx.Response(500)
    assert updater.status(check=True)["error"] == "unreachable"


def test_token_sent_while_the_repository_is_private(web, install_dir):
    (install_dir / "github-token").write_text("secret\n")
    web.routes[LATEST] = release()
    make(web, install_dir)[0].status()
    assert web.calls[0].headers["Authorization"] == "Bearer secret"


def test_start_runs_install_sh_in_a_transient_unit(web, install_dir):
    updater, _, spawned = make(web, install_dir)
    assert updater.start() is None
    assert spawned == [
        [
            "systemd-run",
            "--user",
            "--unit=rewind-update",
            "--collect",
            "--quiet",
            str(install_dir / "install.sh"),
            "update",
        ]
    ]
    assert updater.progress()["state"] == "running"
    assert updater.start() == "running"  # no second update meanwhile


def test_a_git_checkout_cannot_update_itself(web):
    updater, _, spawned = make(web, None)
    assert updater.start() == "not_installed" and not spawned
    assert not updater.status()["can_update"]


def test_spawn_failure_is_reported(web, install_dir):
    def fail(args):
        raise subprocess.CalledProcessError(1, args)

    updater = Updater(
        httpx.Client(transport=httpx.MockTransport(web.handler)), "0.5.0", install_dir, spawn=fail
    )
    assert updater.start() == "spawn_failed"
    assert updater.progress()["state"] == "failed"


def test_progress_written_by_install_sh(web, install_dir):
    updater, clock, _ = make(web, install_dir)
    (install_dir / "update.json").write_text(
        json.dumps({"state": "running", "message": "install", "version": "0.6.0", "time": 1000})
    )
    assert updater.progress()["message"] == "install"
    clock["now"] += STALE_S + 1  # install.sh never finished (power cut)
    assert updater.progress()["state"] == "failed"
    assert not updater.running()


def test_admin_routes(make_client, web):
    client = make_client()
    web.routes[LATEST] = release()
    status = client.get("/api/admin/update").json()
    assert status["latest"] == "0.6.0" and status["can_update"] is False
    res = client.post("/api/admin/update")
    assert res.status_code == 409 and res.json()["detail"] == "not_installed"


def test_display_switches_under_cage_first():
    calls = []

    def run(args):
        calls.append(args)
        return ""

    assert hardware.apply_display("HDMI-A-2", "720x576", run, wayland=["wayland-0"])
    assert calls == [
        [
            "env",
            "WAYLAND_DISPLAY=wayland-0",
            "wlr-randr",
            "--output",
            "HDMI-A-2",
            "--mode",
            "720x576",
        ]
    ]


def test_display_falls_back_to_xrandr():
    calls = []

    def run(args):
        calls.append(args)
        if "wlr-randr" in args:
            raise subprocess.CalledProcessError(1, args)
        return ""

    assert hardware.apply_display("HDMI-A-2", None, run, wayland=["wayland-0"])
    assert calls[-1] == ["xrandr", "--output", "HDMI-2", "--auto"]
