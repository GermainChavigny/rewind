from fastapi.testclient import TestClient

from rewind.app import create_app


def test_health(paths):
    client = TestClient(create_app(paths))
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
