import httpx

from rewind.config import Config, ConfigStore
from rewind.db import Database
from tests.conftest import sample_config


def test_modules_hidden_when_not_configured(make_client):
    client = make_client()
    states = {m["id"]: m["configured"] for m in client.get("/api/modules").json()}
    assert states == {
        "channels": False, "alarm": False, "power": False, "weather": False, "library": True,
    }  # fmt: skip
    assert client.get("/api/alarm").status_code == 404
    assert client.get("/api/weather").status_code == 404
    assert client.post("/api/tv/power", json={"on": True}).status_code == 404


def test_channels_numbered(make_client):
    client = make_client(sample_config())
    chans = client.get("/api/channels").json()
    assert [(c["number"], c["id"]) for c in chans] == [(1, "news"), (2, "wake-up"), (3, "movies")]


def test_progress(make_client):
    client = make_client(sample_config())
    assert client.get("/api/progress/PL1").json() == {}
    r = client.put(
        "/api/progress/PL1", json={"video_id": "abc", "video_index": 2, "position": 12.5}
    )
    assert r.status_code == 200
    p = client.get("/api/progress/PL1").json()
    assert p["video_id"] == "abc" and p["videos"] == {"abc": 12.5}
    # An empty or partial payload can never overwrite saved progress.
    assert client.put("/api/progress/PL1", json={}).status_code == 422
    assert client.get("/api/progress/PL1").json()["video_id"] == "abc"


def test_state_persists(make_client):
    client = make_client()
    assert client.get("/api/state").json() == {"darkness": 0.0, "volume": 100.0}
    client.patch("/api/state", json={"darkness": 0.85})
    assert client.get("/api/state").json()["darkness"] == 0.85
    assert client.patch("/api/state", json={"darkness": 2}).status_code == 422


def test_alarm(make_client):
    client = make_client(sample_config())
    assert client.get("/api/alarm").json() == {"time": "08:00", "enabled": False}
    assert client.put("/api/alarm", json={"time": "07:30", "enabled": True}).status_code == 200
    assert client.get("/api/alarm").json() == {"time": "07:30", "enabled": True}
    assert client.put("/api/alarm", json={"time": "25:00", "enabled": True}).status_code == 422


def test_fake_power(make_client):
    cfg = Config()
    cfg.power.provider = "fake"
    client = make_client(cfg)
    assert client.post("/api/tv/power", json={"on": False}).json() == {"on": False}
    assert client.get("/api/tv/power").json() == {"on": False}


def test_shelly_power(make_client, web):
    cfg = Config()
    cfg.power.provider = "shelly"
    cfg.power.shelly_host = "192.168.1.19"
    web.routes["http://192.168.1.19/rpc/Switch.Set"] = httpx.Response(200, json={"was_on": True})
    web.routes["http://192.168.1.19/rpc/Switch.GetStatus"] = httpx.Response(
        200, json={"output": True}
    )
    client = make_client(cfg)
    assert client.post("/api/tv/power", json={"on": False}).json() == {"on": False}
    assert web.calls[-1].url.params["on"] == "false"
    assert client.get("/api/tv/power").json() == {"on": True}


def test_shelly_unreachable(make_client):
    cfg = Config()
    cfg.power.provider = "shelly"
    cfg.power.shelly_host = "10.0.0.1"
    client = make_client(cfg)
    assert client.post("/api/tv/power", json={"on": True}).status_code == 504


def _forecast():
    from datetime import UTC, datetime, timedelta

    start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=30)
    times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(72)]
    return {
        "utc_offset_seconds": 0,
        "hourly": {"time": times, "weather_code": [3] * 72, "temperature_2m": [12.4] * 72},
        "daily": {"weather_code": [61], "temperature_2m_max": [16.6], "temperature_2m_min": [8.2]},
    }


def test_weather(make_client, web):
    cfg = Config()
    cfg.weather.latitude, cfg.weather.longitude, cfg.weather.location_name = 47.39, 0.69, "Tours"
    web.routes["https://api.open-meteo.com/"] = httpx.Response(200, json=_forecast())
    client = make_client(cfg)
    w = client.get("/api/weather").json()
    assert w["location"] == "Tours" and w["code"] == 3
    assert w["day"] == {"code": 61, "hi": 17, "lo": 8}
    assert [p["id"] for p in w["periods"]] == ["morning", "afternoon", "evening"]
    client.get("/api/weather")
    assert len(web.calls) == 1  # cached


def test_library_and_playback(make_client, paths):
    client = make_client()
    db = Database(paths.data / "rewind.db")
    db.upsert_media(
        {"id": "heat-1995", "kind": "movie", "title": "Heat", "status": "ready",
         "file": "heat-1995.mp4", "duration": 1000}
    )  # fmt: skip
    assert [m["id"] for m in client.get("/api/library").json()] == ["heat-1995"]
    item = client.patch("/api/library/heat-1995/playback", json={"position": 500}).json()
    assert item["position"] == 500 and not item["watched"] and item["last_played_at"]
    item = client.patch("/api/library/heat-1995/playback", json={"position": 950}).json()
    assert item["watched"]  # ≥ 92%
    assert client.patch("/api/library/nope/playback", json={"position": 1}).status_code == 404


def test_media_range_and_traversal(make_client, paths):
    client = make_client()
    (paths.media / "clip.mp4").write_bytes(bytes(range(256)) * 4)
    r = client.get("/media/clip.mp4", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206 and r.content == bytes(range(10, 20))
    assert r.headers["content-type"] == "video/mp4"
    assert client.get("/media/..%2F..%2Fv2conf%2Fconfig.toml").status_code in (400, 404)
    assert client.get("/media/../rewind.db").status_code in (400, 404)


def test_admin_config_masks_and_pin(make_client, paths):
    cfg = sample_config()
    cfg.tmdb.api_key = "secret-key"
    client = make_client(cfg)
    shown = client.get("/api/admin/config").json()
    assert shown["tmdb"]["api_key"] == "********"
    shown["weather"]["latitude"] = 48.0
    shown["admin"]["pin"] = "1234"
    assert client.put("/api/admin/config", json=shown).status_code == 200
    stored = ConfigStore(paths.config / "config.toml").get()
    assert stored.tmdb.api_key == "secret-key" and stored.weather.latitude == 48.0
    # PIN is now required.
    assert client.get("/api/admin/config").status_code == 401
    assert client.get("/api/admin/config", headers={"X-Rewind-Pin": "1234"}).status_code == 200
    bad = client.put(
        "/api/admin/config", json={"channels": "nope"}, headers={"X-Rewind-Pin": "1234"}
    )
    assert bad.status_code == 422


def test_logos(make_client, paths):
    client = make_client()
    (paths.data / "logos").mkdir()
    (paths.data / "logos" / "Making of TV.png").write_bytes(b"png")
    (paths.data / "logos" / "notes.txt").write_text("x")
    logos = client.get("/api/logos").json()
    assert logos == [{"id": "custom:Making of TV.png", "url": "/api/logos/Making%20of%20TV.png"}]
    assert client.get(logos[0]["url"]).content == b"png"
    assert client.get("/api/logos/notes.txt").status_code == 400


def test_ui_settings(make_client):
    ui = make_client(sample_config()).get("/api/ui").json()
    assert ui["language"] == "fr" and ui["keymap"]["tv_power"] == ["AudioVolumeMute"]
    assert ui["alarm"]["step_minutes"] == 10
    assert "admin" not in ui and "tmdb" not in ui


def test_serves_frontend(make_client, paths, tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>REWIND</title>")
    monkeypatch.setenv("REWIND_FRONTEND_DIR", str(dist))
    client = make_client()
    assert "REWIND" in client.get("/").text
    assert client.get("/api/health").json()["status"] == "ok"
