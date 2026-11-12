from rewind.config import Config
from rewind.learn import KeyLearner
from tests.conftest import sample_config


def test_status_reports_first_run(make_client):
    client = make_client()
    assert client.get("/api/admin/status").json()["first_run"] is True
    client = make_client(sample_config())
    status = client.get("/api/admin/status").json()
    assert status["first_run"] is False and status["channels"] == 3


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
