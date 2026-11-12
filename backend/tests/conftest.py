import httpx
import pytest
from fastapi.testclient import TestClient

from rewind.app import create_app
from rewind.config import Channel, Config, ConfigStore
from rewind.paths import Paths


def _no_spawn(args):
    raise AssertionError(f"tests must not run {args}")


@pytest.fixture
def paths(tmp_path):
    return Paths(
        data=tmp_path / "v2data", config=tmp_path / "v2conf", media=tmp_path / "v2data" / "media"
    ).ensure()


class FakeWeb:
    """Records outgoing HTTP calls and answers with canned responses."""

    def __init__(self):
        self.calls: list[httpx.Request] = []
        self.routes: dict[str, httpx.Response] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        for prefix, response in self.routes.items():
            if str(request.url).startswith(prefix):
                return response
        return httpx.Response(404)


@pytest.fixture
def web():
    return FakeWeb()


@pytest.fixture
def make_client(paths, web):
    def make(config: Config | None = None) -> TestClient:
        if config is not None:
            ConfigStore(paths.config / "config.toml").save(config)
        app = create_app(paths, http=httpx.Client(transport=httpx.MockTransport(web.handler)))
        app.state.poweroff = lambda mode: True  # never turn the test machine off
        app.state.updater.spawn = _no_spawn  # never start a real update
        return TestClient(app)

    return make


def sample_config() -> Config:
    return Config(
        channels=[
            Channel(id="news", name="News", playlist_id="PLnews", save_progress=False),
            Channel(id="wake-up", name="Wake Up", playlist_id="PLwake", alarm=True),
            Channel(id="movies", name="Movies", kind="library"),
        ]
    )
