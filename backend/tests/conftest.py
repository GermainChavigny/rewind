import pytest

from rewind.paths import Paths


@pytest.fixture
def paths(tmp_path):
    return Paths(
        data=tmp_path / "v2data", config=tmp_path / "v2conf", media=tmp_path / "v2data" / "media"
    ).ensure()
