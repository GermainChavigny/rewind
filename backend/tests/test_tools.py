"""Admin helpers: service checks, model lists, hardware, TV events, virtual remote."""

import asyncio
import threading

import httpx

from rewind import hardware
from rewind.config import AdvisorProvider, IndexerConfig, masked
from rewind.events import EventBus
from tests.conftest import sample_config

PACTL = """Card #0
\tName: alsa_card.pci-0000_00_0e.0
\tProperties:
\t\tdevice.description = "Audio interne"
\tPorts:
\t\tanalog-input-mic: Microphone (type: Mic, priority: 8700, latency offset: 0 usec, not available)
\t\t\tPart of profile(s): input:analog-stereo
\t\tanalog-output-headphones: Casque audio (type: Headphones, priority: 9900, latency offset: 200000 usec, available)
\t\thdmi-output-1: HDMI 2 (type: HDMI, priority: 5800, latency offset: 0 usec, not available)
\tActive Profile: output:analog-stereo
"""  # noqa: E501


def test_audio_ports_and_live_offset():
    calls = []

    def run(args):
        calls.append(args)
        return PACTL

    ports = hardware.audio_ports(run)
    assert [(p["name"], p["available"], p["offset_ms"]) for p in ports] == [
        ("analog-output-headphones", True, 200),
        ("hdmi-output-1", False, 0),
    ]
    assert ports[0]["card_description"] == "Audio interne"
    assert hardware.apply_av_offset("analog-output-headphones", -40, run)
    assert calls[-1] == [
        "pactl", "set-port-latency-offset", "alsa_card.pci-0000_00_0e.0",
        "analog-output-headphones", "-40000",
    ]  # fmt: skip
    assert not hardware.apply_av_offset("nope", 10, run)


def test_displays_from_sysfs(tmp_path):
    for name, status, modes in (
        ("card0-HDMI-A-1", "disconnected", ""),
        ("card0-HDMI-A-2", "connected", "1280x720\n720x576\n720x576\n"),
    ):
        d = tmp_path / name
        d.mkdir()
        (d / "status").write_text(status + "\n")
        (d / "modes").write_text(modes)
    shown = hardware.displays(tmp_path)
    assert shown[0] == {"name": "HDMI-A-2", "connected": True, "modes": ["1280x720", "720x576"]}


def test_check_uses_typed_values_and_stored_secrets(make_client, web):
    cfg = sample_config()
    cfg.tmdb.api_key = "stored-key"
    client = make_client(cfg)
    web.routes["https://api.themoviedb.org/3/configuration"] = httpx.Response(200, json={})
    draft = masked(cfg)
    assert client.post("/api/admin/check", json={"service": "tmdb", "config": draft}).json()["ok"]
    assert "api_key=stored-key" in str(web.calls[-1].url)
    web.routes["https://api.themoviedb.org/3/configuration"] = httpx.Response(401)
    draft["tmdb"]["api_key"] = "typed"
    res = client.post("/api/admin/check", json={"service": "tmdb", "config": draft}).json()
    assert res["ok"] is False and "refusée" in res["message"]
    assert "api_key=typed" in str(web.calls[-1].url)


def test_check_indexer_and_advisor(make_client, web):
    cfg = sample_config()
    cfg.indexers = [IndexerConfig(url="http://jackett:9117", api_key="k")]
    cfg.advisor = [
        AdvisorProvider(name="Groq", kind="openai", base_url="https://ai.test/v1", api_key="k",
                        model="m")
    ]  # fmt: skip
    client = make_client(cfg)
    draft = masked(cfg)
    web.routes["http://jackett:9117/"] = httpx.Response(200, text="<caps><server/></caps>")
    body = {"service": "indexer", "index": 0, "config": draft}
    assert client.post("/api/admin/check", json=body).json()["ok"]
    web.routes["http://jackett:9117/"] = httpx.Response(
        200, text='<error code="100" description="Invalid API Key"/>'
    )
    res = client.post("/api/admin/check", json=body).json()
    assert not res["ok"] and "Invalid API Key" in res["message"]

    web.routes["https://ai.test/v1/chat/completions"] = httpx.Response(
        200, json={"choices": [{"message": {"content": '{"ok": true}'}}]}
    )
    body = {"service": "advisor", "index": 0, "config": draft}
    assert client.post("/api/admin/check", json=body).json()["ok"]
    assert client.post("/api/admin/check", json={**body, "index": 3}).status_code == 404

    web.routes["https://ai.test/v1/models"] = httpx.Response(
        200, json={"data": [{"id": "b-model"}, {"id": "a-model"}]}
    )
    models = client.post("/api/admin/models", json={"index": 0, "config": draft}).json()
    assert models == ["a-model", "b-model"]


def test_learning_accepts_numbered_actions(make_client):
    client = make_client(sample_config())
    assert client.post("/api/admin/learn", json={"action": "channel_1"}).status_code == 200


def test_av_offset_applied_live_and_on_save(make_client):
    client = make_client(sample_config())
    applied = []
    client.app.state.apply_av = lambda port, ms: applied.append((port, ms)) or True
    res = client.post("/api/admin/av-offset", json={"port": "analog-output-headphones", "ms": 40})
    assert res.json() == {"applied": True}
    cfg = client.get("/api/admin/config").json()
    cfg["audio"]["output_port"] = "analog-output-headphones"
    cfg["audio"]["av_offset_ms"] = 120
    client.put("/api/admin/config", json=cfg)
    client.put("/api/admin/config", json=cfg)  # unchanged: not applied again
    assert applied == [("analog-output-headphones", 40), ("analog-output-headphones", 120)]


def test_virtual_remote_layout_and_press(make_client):
    client = make_client(sample_config())
    got = client.get("/api/remote/layout").json()
    assert got["layouts"] == {"tv": None, "movies": None}
    assert "channel_1" in got["actions"] and got["extra"] == ["home", "machine_power"]
    layout = {"cols": 4, "rows": 9, "cells": {"channel_1": 0, "tv_power": 3, "bogus": 1}}
    assert client.put("/api/remote/layout/tv", json=layout).json()["cells"] == {
        "channel_1": 0, "tv_power": 3,
    }  # fmt: skip
    movies = {"cols": 4, "rows": 4, "cells": {"home": 0, "play_pause": 5}}
    assert client.put("/api/remote/layout/movies", json=movies).json()["cells"] == movies["cells"]
    got = client.get("/api/remote/layout").json()["layouts"]
    assert got["tv"]["cells"] == {"channel_1": 0, "tv_power": 3}
    assert got["movies"]["rows"] == 4
    clash = {"cols": 4, "rows": 9, "cells": {"channel_1": 0, "tv_power": 0}}
    assert client.put("/api/remote/layout/tv", json=clash).status_code == 422
    assert client.put("/api/remote/layout/radio", json=layout).status_code == 422
    press = client.post("/api/remote/press", json={"action": "channel_2"})
    assert press.json() == {"delivered": False}
    assert client.post("/api/remote/press", json={"action": "home"}).status_code == 200
    assert client.post("/api/remote/press", json={"action": "nope"}).status_code == 404
    assert (
        client.post("/api/admin/tv-event", json={"type": "chime", "chime": "dawn"}).status_code
        == 200
    )


def test_pointer_text_and_tv_report(make_client):
    client = make_client(sample_config())
    bus: EventBus = client.app.state.events
    sent = []
    bus.publish = lambda event: sent.append(event) or 1
    assert client.post("/api/remote/pointer", json={"dx": 4, "dy": -2}).json()["delivered"]
    assert (
        client.post("/api/remote/text", json={"text": "alien", "submit": True}).status_code == 200
    )
    assert sent == [
        {"type": "pointer", "dx": 4, "dy": -2, "click": False, "scroll": 0},
        {"type": "text", "text": "alien", "submit": True},
    ]
    phones = []
    client.app.state.remote_events.publish = lambda event: phones.append(event) or 1
    report = {"mode": "movies", "keyboard": {"text": "ali", "purpose": "series"}}
    assert client.put("/api/tv/report", json=report).status_code == 200
    assert phones[-1]["mode"] == "movies" and phones[-1]["keyboard"]["text"] == "ali"
    assert client.put("/api/tv/report", json={"mode": "radio"}).status_code == 422


def test_admin_url_points_at_the_lan(make_client, monkeypatch):
    from rewind import system

    client = make_client(sample_config())
    monkeypatch.setattr(system, "lan_address", lambda: "192.168.0.42")
    assert client.get("/api/remote/admin-url").json() == {
        "url": "http://192.168.0.42/admin/", "lan": True,
    }  # fmt: skip


def test_shutdown(make_client, monkeypatch):
    from rewind.routes import remote

    monkeypatch.setattr(remote, "SHUTDOWN_CARD_S", 0)
    cfg = sample_config()
    cfg.power.provider = "fake"
    client = make_client(cfg)
    done = threading.Event()
    modes = []
    # Recorder only: the real poweroff is never reachable from this test.
    client.app.state.poweroff = lambda mode: modes.append(mode) or done.set() or True
    tv_events = []
    client.app.state.events.publish = lambda event: tv_events.append(event) or 1
    assert client.post("/api/remote/shutdown").json()["started"]
    assert done.wait(2)
    assert modes == ["poweroff"] and tv_events[0] == {"type": "shutdown"}

    cfg.system.shutdown = "none"
    client = make_client(cfg)
    client.app.state.poweroff = lambda mode: modes.append(mode) or True
    assert client.post("/api/remote/shutdown").status_code == 404
    assert client.get("/api/remote/layout").json()["extra"] == ["home"]
    assert modes == ["poweroff"]


def test_poweroff_modes():
    from rewind import system

    calls = []
    assert system.poweroff("fake", run=calls.append) and calls == []
    assert not system.poweroff("none", run=calls.append)
    assert system.poweroff("poweroff", run=calls.append) and len(calls) == 1

    def fail(args):
        raise OSError("denied")

    assert not system.poweroff("poweroff", run=fail)


def test_event_bus_delivers_to_subscribers():
    async def scenario():
        bus = EventBus()
        stream = bus.stream()
        assert await anext(stream) == ": connected\n\n"
        assert bus.listeners == 1
        first = bus.stream(first={"type": "state"})
        assert await anext(first) == ": connected\n\n"
        assert await anext(first) == 'data: {"type": "state"}\n\n'
        await first.aclose()
        assert bus.publish({"type": "action", "action": "next"}) == 1
        assert await anext(stream) == 'data: {"type": "action", "action": "next"}\n\n'
        await stream.aclose()
        assert bus.listeners == 0

    asyncio.run(scenario())


def test_check_indexer_counts_jackett_sites():
    from rewind.checks import check_indexer

    sites = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["t"] == "caps":
            return httpx.Response(200, text="<caps><server/></caps>")
        items = "".join(f'<indexer id="s{i}"/>' for i in range(sites["n"]))
        return httpx.Response(200, text=f"<indexers>{items}</indexers>")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    ix = IndexerConfig(url="http://jackett:9117", api_key="k")
    res = check_indexer(ix, http)  # freshly installed: no site yet
    assert not res["ok"] and "Add indexer" in res["message"]
    sites["n"] = 3
    res = check_indexer(ix, http)
    assert res["ok"] and "3 sites" in res["message"]
