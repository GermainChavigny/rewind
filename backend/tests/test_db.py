from rewind.db import MIGRATIONS, Database


def test_migrations_and_kv(tmp_path):
    db = Database(tmp_path / "t.db")
    assert db.migrate() == len(MIGRATIONS)
    assert db.get_kv("x", 5) == 5
    db.set_kv("x", {"a": 1})
    assert db.get_kv("x") == {"a": 1}


def test_playlist_progress(tmp_path):
    db = Database(tmp_path / "t.db")
    db.save_playlist_progress("PL", "v1", 0, 10.5)
    db.save_playlist_progress("PL", "v2", 1, 3)
    p = db.get_playlist_progress("PL")
    assert p["video_id"] == "v2" and p["video_index"] == 1
    assert p["videos"] == {"v1": 10.5, "v2": 3}


def test_media_upsert_keeps_children(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_media({"id": "show", "kind": "series", "title": "Show", "status": "ready"})
    db.upsert_media(
        {"id": "ep", "kind": "episode", "parent_id": "show", "title": "E1", "status": "ready",
         "subtitles": {"fr": "ep.fr.vtt"}}
    )  # fmt: skip
    # Updating the parent must not cascade-delete its episodes.
    db.patch_media("show", {"overview": "new"})
    assert db.get_media("ep")["subtitles"] == {"fr": "ep.fr.vtt"}
    assert db.get_media("show")["overview"] == "new"
    assert [m["id"] for m in db.list_media(parent_id="show")] == ["ep"]
