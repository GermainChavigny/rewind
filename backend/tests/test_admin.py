from rewind.learn import KeyLearner
from tests.conftest import sample_config


def test_status_reports_first_run(make_client, paths):
    from rewind.db import Database

    client = make_client(sample_config())
    # A saved config is not enough: the wizard counts as done only when it finishes.
    assert client.get("/api/admin/status").json()["first_run"] is True
    assert client.post("/api/admin/setup/complete").status_code == 200
    status = client.get("/api/admin/status").json()
    assert status["first_run"] is False and status["channels"] == 3
    assert Database(paths.data / "rewind.db").get_kv("setup_done") is True


def test_pin_protects_admin_only(make_client):
    cfg = sample_config()
    cfg.admin.pin = "1234"
    client = make_client(cfg)
    assert client.get("/api/admin/config").status_code == 401
    assert client.get("/api/admin/config", headers={"X-Rewind-Pin": "0000"}).status_code == 401
    assert client.get("/api/admin/config", headers={"X-Rewind-Pin": "1234"}).status_code == 200
    # The TV side never asks for the PIN.
    assert client.get("/api/remote/learn").status_code == 200


def test_key_learning_round_trip(make_client):
    client = make_client(sample_config())
    assert client.post("/api/admin/learn", json={"action": "nope"}).status_code == 404
    client.post("/api/admin/learn", json={"action": "darker"})
    assert client.get("/api/remote/learn").json() == {"action": "darker"}
    # The TV reports the key it heard; the admin sees it.
    assert client.post("/api/remote/learn", json={"key": "F7"}).json() == {"accepted": True}
    assert client.get("/api/remote/learn").json() == {"action": None}
    assert client.get("/api/admin/learn").json()["key"] == "F7"
    # A second key press is ignored once one was captured.
    assert client.post("/api/remote/learn", json={"key": "F8"}).json() == {"accepted": False}


def test_learner_ignores_when_idle_and_expires():
    learner = KeyLearner()
    assert learner.offer("F1") is False
    learner.start("alarm_toggle")
    assert learner.offer("") is False and learner.offer("k" * 40) is False
    learner._until = 0  # expired
    assert learner.offer("F1") is False and learner.pending() is None


def test_config_put_rejects_unknown_fields(make_client):
    client = make_client(sample_config())
    cfg = client.get("/api/admin/config").json()
    cfg["channels"][0]["name"] = "Actualités"
    assert client.put("/api/admin/config", json=cfg).status_code == 200
    cfg["bogus"] = 1
    assert client.put("/api/admin/config", json=cfg).status_code == 422


def test_geocode_shapes_places(make_client, web):
    import httpx

    web.routes["https://geocoding-api.open-meteo.com/"] = httpx.Response(
        200,
        json={"results": [{"name": "Paris", "admin1": "Île-de-France", "country": "France",
                           "latitude": 48.85661, "longitude": 2.35222}]},
    )  # fmt: skip
    client = make_client(sample_config())
    assert client.get("/api/admin/geocode", params={"q": "Paris"}).json() == [
        {
            "name": "Paris",
            "detail": "Île-de-France, France",
            "latitude": 48.8566,
            "longitude": 2.3522,
        }
    ]
    assert client.get("/api/admin/geocode", params={"q": "T"}).json() == []
    web.routes.clear()
    assert client.get("/api/admin/geocode", params={"q": "Paris"}).status_code == 502


def test_saving_applies_live_and_tells_the_tv(make_client):
    client = make_client(sample_config())
    app = client.app
    events: list[dict] = []
    app.state.events.publish = lambda e: events.append(e) or 1
    calls: list = []
    app.state.apply_display = lambda output, mode: calls.append((output, mode)) or False
    cfg = client.get("/api/admin/config").json()
    cfg["display"]["output"] = "HDMI-A-2"
    cfg["display"]["mode"] = "720x576"
    assert client.put("/api/admin/config", json=cfg).status_code == 200
    assert calls == [("HDMI-A-2", "720x576")]
    assert {"type": "config"} in events
    # xrandr failed: the admin is told the display waits for a restart.
    assert client.get("/api/admin/status").json()["restart_needed"] == ["display"]
    app.state.apply_display = lambda output, mode: True
    cfg["display"]["mode"] = "640x480"
    client.put("/api/admin/config", json=cfg)
    assert client.get("/api/admin/status").json()["restart_needed"] == []
