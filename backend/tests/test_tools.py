"""Admin helpers: service checks, model lists, hardware, TV events, virtual remote."""

import asyncio

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
    assert got["layout"] is None and "channel_1" in got["actions"]
    layout = {"cols": 4, "rows": 9, "cells": {"channel_1": 0, "tv_power": 3, "bogus": 1}}
    assert client.put("/api/remote/layout", json=layout).json()["cells"] == {
        "channel_1": 0, "tv_power": 3,
    }  # fmt: skip
    clash = {"cols": 4, "rows": 9, "cells": {"channel_1": 0, "tv_power": 0}}
    assert client.put("/api/remote/layout", json=clash).status_code == 422
    assert client.post("/api/remote/press", json={"action": "channel_2"}).json() == {"delivered": 0}
    assert client.post("/api/remote/press", json={"action": "nope"}).status_code == 404
    assert (
        client.post("/api/admin/tv-event", json={"type": "chime", "chime": "dawn"}).status_code
        == 200
    )


def test_event_bus_delivers_to_subscribers():
    async def scenario():
        bus = EventBus()
        stream = bus.stream()
        assert await anext(stream) == ": connected\n\n"
        assert bus.listeners == 1
        assert bus.publish({"type": "action", "action": "next"}) == 1
        assert await anext(stream) == 'data: {"type": "action", "action": "next"}\n\n'
        await stream.aclose()
        assert bus.listeners == 0

    asyncio.run(scenario())
