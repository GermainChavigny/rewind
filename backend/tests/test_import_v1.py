import hashlib
import json
import os

import pytest

from rewind.tools.import_v1 import import_v1


def _tree_fingerprint(root):
    """Empreinte (chemin, taille, mtime, contenu) de toute une arborescence."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            st = p.stat()
            out[str(p.relative_to(root))] = (
                st.st_size,
                st.st_mtime_ns,
                hashlib.sha256(p.read_bytes()).hexdigest(),
            )
    return out


@pytest.fixture
def v1(tmp_path):
    tv_data = tmp_path / "tv_data"
    movies = tmp_path / "movies"
    (tv_data / "posters").mkdir(parents=True)
    movies.mkdir()
    (tv_data / "library.json").write_text(json.dumps({"heat-1995": {"title": "Heat"}}))
    (tv_data / "alarm.json").write_text('{"time": "08:50", "enabled": false}')
    (tv_data / "secrets.json").write_text("{}")
    os.chmod(tv_data / "secrets.json", 0o600)
    (tv_data / "posters" / "heat-1995.jpg").write_bytes(b"jpg")
    (movies / "heat-1995.mp4").write_bytes(b"video" * 100)
    (movies / "heat-1995.fr.vtt").write_text("WEBVTT")
    (movies / "ffmpeg.exe").write_bytes(b"MZ")
    return tv_data, movies


def test_import_never_touches_v1(v1, paths):
    tv_data, movies = v1
    before = (_tree_fingerprint(tv_data), _tree_fingerprint(movies))
    report = import_v1(tv_data, movies, paths)
    import_v1(tv_data, movies, paths)  # relançable
    assert report.ok, report.summary()
    assert (_tree_fingerprint(tv_data), _tree_fingerprint(movies)) == before


def test_snapshot_and_links(v1, paths):
    tv_data, movies = v1
    report = import_v1(tv_data, movies, paths)
    snap = paths.import_v1
    assert json.loads((snap / "library.json").read_text())["heat-1995"]["title"] == "Heat"
    assert (snap / "posters" / "heat-1995.jpg").exists()
    assert oct((snap / "secrets.json").stat().st_mode & 0o777) == "0o600"
    assert os.path.samefile(paths.media / "heat-1995.mp4", movies / "heat-1995.mp4")
    assert not (paths.media / "ffmpeg.exe").exists()
    assert report.linked == 2


def test_deleting_in_v2_keeps_v1_file(v1, paths):
    tv_data, movies = v1
    import_v1(tv_data, movies, paths)
    (paths.media / "heat-1995.mp4").unlink()
    assert (movies / "heat-1995.mp4").read_bytes() == b"video" * 100


def test_rerun_refreshes_snapshot(v1, paths):
    tv_data, movies = v1
    import_v1(tv_data, movies, paths)
    (paths.import_v1 / "stale.txt").write_text("x")
    report = import_v1(tv_data, movies, paths)
    assert not (paths.import_v1 / "stale.txt").exists()
    assert report.already_linked == 2 and report.linked == 0


def test_refuses_overlap(v1, tmp_path):
    from rewind.paths import Paths

    tv_data, movies = v1
    bad = Paths(data=tv_data / "v2", config=tmp_path / "c", media=tmp_path / "m").ensure()
    with pytest.raises(ValueError):
        import_v1(tv_data, movies, bad)
