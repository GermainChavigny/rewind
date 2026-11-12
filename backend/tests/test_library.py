import json
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from rewind.config import AdvisorProvider, Config, ConfigStore, IndexerConfig
from rewind.db import Database
from rewind.library import advisor as adv
from rewind.library.jobs import JobWorker, priority
from rewind.library.sources import Indexers, build_magnet, clean_title, magnet_hash, parse_episode
from rewind.library.transcoder import Transcoder

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


# --- release names --------------------------------------------------------------------


def test_parse_episode():
    assert parse_episode("Show.S02E03.720p.mkv") == (2, 3)
    assert parse_episode("show 2x03") == (2, 3)
    assert parse_episode("Show Season 2 Episode 3") == (2, 3)
    assert parse_episode("Show.S02.COMPLETE.1080p") == (2, None)
    assert parse_episode("Movie (1999)") is None


def test_clean_title():
    assert clean_title("Leon The Professional Extended (1994) [1080p]") == (
        "Leon The Professional",
        1994,
    )
    assert clean_title("The.Matrix.1999.1080p.BluRay.x264") == ("The Matrix", 1999)


def test_slugify():
    from rewind.library.sources import slugify

    assert slugify("SOS Fantômes", 1984) == "sos-fantomes-1984"
    assert slugify("L'Été en pente douce") == "l-ete-en-pente-douce"


def test_magnets():
    m = build_magnet("ABCDEF0123", "Some Movie")
    assert magnet_hash(m) == "abcdef0123"
    assert "dn=Some%20Movie" in m and "&tr=" in m


# --- indexers -------------------------------------------------------------------------

TORZNAB = """<?xml version="1.0"?>
<rss xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>Big.Movie.1999.1080p</title><size>2000000000</size>
  <torznab:attr name="seeders" value="50"/><torznab:attr name="infohash" value="AAA111"/></item>
<item><title>Big.Movie.1999.2160p</title><size>20000000000</size>
  <torznab:attr name="seeders" value="900"/>
  <torznab:attr name="magneturl" value="magnet:?xt=urn:btih:bbb222"/></item>
<item><title>Big.Movie.1999.720p</title><size>900000000</size>
  <torznab:attr name="seeders" value="0"/><torznab:attr name="infohash" value="ccc333"/></item>
<item><title>Dup</title><link>magnet:?xt=urn:btih:AAA111</link>
  <torznab:attr name="seeders" value="5"/></item>
</channel></rss>"""


def test_torznab_filters_and_sorts(web):
    web.routes["http://jackett:9117/"] = httpx.Response(200, text=TORZNAB)
    http = httpx.Client(transport=httpx.MockTransport(web.handler))
    cfg = IndexerConfig(url="http://jackett:9117", api_key="SECRET", max_size_gb=6)
    releases = Indexers([cfg], http).search("big movie")
    # Oversized (20 GB) and seedless releases are dropped, duplicates merged.
    assert [r.hash for r in releases] == ["aaa111"]
    assert web.calls[0].url.params["apikey"] == "SECRET"


def test_torznab_keeps_oversized_when_nothing_else(web):
    web.routes["http://jackett:9117/"] = httpx.Response(200, text=TORZNAB)
    http = httpx.Client(transport=httpx.MockTransport(web.handler))
    cfg = IndexerConfig(url="http://jackett:9117", max_size_gb=0.5)
    assert [r.hash for r in Indexers([cfg], http).search("x")] == ["bbb222", "aaa111"]


def test_indexer_failure_is_not_fatal(web):
    http = httpx.Client(transport=httpx.MockTransport(web.handler))  # every call → 404
    assert Indexers([IndexerConfig(url="http://jackett:9117")], http).search("x") == []


# --- routes ---------------------------------------------------------------------------


def test_search_needs_an_indexer(make_client):
    client = make_client(Config())
    assert client.post("/api/library/search", json={"query": "x"}).status_code == 503
    assert client.post("/api/advisor/recommend", json={}).status_code == 503
    assert client.get("/api/library/features").json() == {
        "search": False,
        "series": False,
        "advisor": False,
    }


def test_library_disabled_is_404(make_client):
    cfg = Config()
    cfg.library.enabled = False
    client = make_client(cfg)
    assert client.get("/api/library").status_code == 404
    assert client.get("/api/library/jobs").status_code == 404


def test_search_enriched_with_tmdb(make_client, web):
    web.routes["http://jackett:9117/"] = httpx.Response(200, text=TORZNAB)
    web.routes["https://api.themoviedb.org/3/search/movie"] = httpx.Response(
        200,
        json={"results": [{"id": 7, "title": "Le Grand Film", "release_date": "1999-05-01",
                           "poster_path": "/p.jpg", "overview": "Un film."}]},
    )  # fmt: skip
    cfg = Config(indexers=[IndexerConfig(url="http://jackett:9117")])
    cfg.tmdb.api_key = "k"
    client = make_client(cfg)
    [result] = client.post("/api/library/search", json={"query": "big movie"}).json()
    assert result["title"] == "Le Grand Film" and result["year"] == 1999
    assert result["poster_url"].endswith("/w500/p.jpg")
    assert result["torrent"]["seeders"] == 50
    # The cleaned release name is what TMDB is asked about.
    tmdb_call = next(c for c in web.calls if "themoviedb" in str(c.url))
    assert tmdb_call.url.params["query"] == "Big Movie"


def test_delete_purges_files_and_episodes(make_client, paths):
    client = make_client()
    db = Database(paths.data / "rewind.db")
    (paths.media / "ep.mp4").write_text("v")
    (paths.media / "ep.fr.vtt").write_text("s")
    (paths.data / "posters").mkdir(exist_ok=True)
    (paths.data / "posters" / "show.jpg").write_text("p")
    db.upsert_media({"id": "show", "kind": "series", "title": "Show", "status": "ready",
                     "poster": "show.jpg"})  # fmt: skip
    db.upsert_media({"id": "show-s01e01", "kind": "episode", "parent_id": "show",
                     "title": "E1", "status": "ready", "file": "ep.mp4",
                     "subtitles": {"fr": "ep.fr.vtt"}})  # fmt: skip
    assert client.delete("/api/library/show").status_code == 200
    assert db.list_media() == []
    assert not (paths.media / "ep.mp4").exists() and not (paths.media / "ep.fr.vtt").exists()
    assert not (paths.data / "posters" / "show.jpg").exists()


def test_delete_never_leaves_the_media_dir(make_client, paths, tmp_path):
    client = make_client()
    outside = tmp_path / "precious.mp4"
    outside.write_text("keep me")
    Database(paths.data / "rewind.db").upsert_media(
        {"id": "m", "kind": "movie", "title": "M", "status": "ready", "file": "../../precious.mp4"}
    )
    client.delete("/api/library/m")
    assert outside.exists()


def test_playback_started_and_watched(make_client, paths):
    client = make_client()
    Database(paths.data / "rewind.db").upsert_media(
        {"id": "m", "kind": "movie", "title": "M", "status": "ready", "duration": 100}
    )
    item = client.patch("/api/library/m/playback", json={"started": True}).json()
    assert item["last_played_at"] > 0 and not item["watched"]
    item = client.patch("/api/library/m/playback", json={"position": 95}).json()
    assert item["watched"]
    r = client.patch("/api/library/m/playback", json={"subtitle_mode": "xx"})
    assert r.status_code == 422


# --- advisor --------------------------------------------------------------------------


def test_advisor_prompt_and_parse():
    prompt = adv.build_prompt({"mood": "Laugh", "era": "Any"}, ["Heat"], "Bill Murray", "movie")
    assert "Mood: Laugh" in prompt and "Era" not in prompt
    assert "Heat" in prompt and "Bill Murray" in prompt and "French" in prompt
    text = '```json\n{"recommendations": [{"title": "A", "year": 1990}, {"x": 1}]}\n```'
    assert adv.parse(text) == [{"title": "A", "year": 1990}]
    assert adv.clip("mot " * 60).endswith("…")


def test_advisor_falls_back_to_next_provider(make_client, web, paths):
    answer = {"recommendations": [{"title": "Un Jour sans fin", "year": 1993, "description": "x"}]}
    web.routes["https://gem.example/"] = httpx.Response(503, json={"error": {"message": "busy"}})
    web.routes["https://oai.example/"] = httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(answer)}}]}
    )
    cfg = Config(
        advisor=[
            AdvisorProvider(name="G", kind="gemini", base_url="https://gem.example", api_key="a",
                            model="m"),
            AdvisorProvider(name="O", base_url="https://oai.example", api_key="b", model="m"),
        ]
    )  # fmt: skip
    adv.Provider.BACKOFF_S = 0
    client = make_client(cfg)
    Database(paths.data / "rewind.db").upsert_media(
        {"id": "heat", "kind": "movie", "title": "Heat", "status": "ready"}
    )
    client.post("/api/advisor/forget", json={"title": "Alien", "year": 1979})
    [rec] = client.post("/api/advisor/recommend", json={"criteria": {"mood": "Laugh"}}).json()
    assert rec["title"] == "Un Jour sans fin" and rec["id"] == "un-jour-sans-fin-1993"
    prompt = json.loads(web.calls[-1].content)["messages"][0]["content"]
    assert "Heat" in prompt and "Alien" in prompt  # owned + forgotten are excluded
    # The Gemini key goes in a header, never in the URL.
    gem = next(c for c in web.calls if "gem.example" in str(c.url))
    assert gem.headers["x-goog-api-key"] == "a" and "key=" not in str(gem.url)


# --- jobs -----------------------------------------------------------------------------


class FakeTorrent:
    def __init__(self, files: list[Path]):
        self.files = files

    def download(self, magnet, progress=None, cancelled=lambda: False, meta_timeout=0, poll=0):
        for f in self.files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"x")
        if progress:
            progress(1.0)
        return self.files


class FakeTranscoder:
    def extract_subtitles(self, src, out_dir, base):
        return {"en": f"{base}.en.vtt"}

    def prepare(self, src, dst, progress=None):
        dst.write_bytes(src.read_bytes())
        return "remux"

    def duration(self, path):
        return 1200.0

    def audio_tracks(self, path):
        return [{"index": 0, "lang": "eng", "title": ""}]

    def cancel(self):
        pass


def _wait(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_pack_maps_files_to_episodes(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    media, downloads = tmp_path / "media", tmp_path / "dl"
    media.mkdir()
    pack_dir = downloads / "Show.S01"
    torrent = FakeTorrent([pack_dir / "Show.S01E01.mkv", pack_dir / "Show.S01E02.mkv"])
    worker = JobWorker(db, media, downloads, torrent, FakeTranscoder(), lambda: None,
                       lambda: ["fr", "en"])  # fmt: skip
    missing: list = []
    worker.on_pack_missing = lambda pack, targets: missing.extend(targets)
    db.upsert_media({"id": "show", "kind": "series", "title": "Show", "status": "ready"})
    targets = [
        {"season": 1, "episode": n, "episode_id": f"show-s01e{n:02d}", "title": f"E{n}"}
        for n in (1, 2, 3)
    ]
    db.upsert_media({"id": "show-pack-s01", "kind": "pack", "parent_id": "show", "title": "S01",
                     "status": "queued", "season": 1, "show_title": "Show", "fallback": True,
                     "candidates": ["magnet:?xt=urn:btih:aa"], "targets": targets})  # fmt: skip
    worker.start()
    assert _wait(lambda: db.get_media("show-pack-s01") is None)  # pack done → removed
    eps = {e["id"]: e for e in db.list_media(kind="episode")}
    assert sorted(eps) == ["show-s01e01", "show-s01e02"]
    assert eps["show-s01e01"]["status"] == "ready" and eps["show-s01e01"]["duration"] == 1200
    assert eps["show-s01e01"]["subtitles"] == {"en": "show-s01e01.en.vtt"}
    assert (media / "show-s01e01.mp4").exists()
    assert [t["episode"] for t in missing] == [3]  # → single-episode fallback
    assert not pack_dir.exists()  # staging cleaned


def test_priority():
    assert priority({"kind": "movie"}) == 0
    assert priority({"kind": "episode", "season": 2, "episode": 3}) == 2003
    assert priority({"kind": "pack", "targets": [{"season": 1, "episode": 5}]}) == 1005


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_transcoder_plans(tmp_path):
    def make(name, vcodec, acodec):
        path = tmp_path / name
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10:duration=1",
             "-f", "lavfi", "-i", "sine=duration=1",
             "-c:v", vcodec, "-c:a", acodec, "-shortest", str(path)],
            check=True,
        )  # fmt: skip
        return path

    t = Transcoder()
    web = make("web.mp4", "libx264", "aac")
    assert t.plan(web) == "remux"
    assert t.plan(make("ac3.mkv", "libx264", "ac3")) == "audio"
    old = make("old.avi", "mpeg4", "mp3")
    assert t.plan(old) == "full"
    out = tmp_path / "out.mp4"
    ratios: list[float] = []
    assert t.prepare(old, out, ratios.append) == "full"
    assert t.plan(out) == "remux" and ratios[-1] == 1.0
    assert 0.5 < t.duration(out) < 2 and t.audio_tracks(out)[0]["index"] == 0


def test_migrated_unfinished_jobs_are_not_resumed(tmp_path):
    from rewind.tools.migrate_v1 import media_from_v1

    item = media_from_v1({"id": "x", "title": "X", "status": "downloading"}, set())
    assert item["status"] == "error" and "v1" in item["error"]


def test_config_store_roundtrip_new_fields(tmp_path):
    store = ConfigStore(tmp_path / "c.toml")
    cfg = Config(indexers=[IndexerConfig(url="http://x", systemd_unit="jackett.service")])
    store.save(cfg)
    again = ConfigStore(tmp_path / "c.toml").get()
    assert again.indexers[0].systemd_unit == "jackett.service"
    assert again.library.torrent_port == 6891


def test_local_advisor_needs_no_key():
    from rewind.config import AdvisorProvider
    from rewind.library.advisor import Provider

    local = AdvisorProvider(name="Ollama", kind="openai", base_url="http://127.0.0.1:11434/v1",
                            model="llama3.2")  # fmt: skip
    remote = AdvisorProvider(name="X", kind="openai", base_url="https://api.x.ai/v1", model="m")
    assert Provider(local, None).available()
    assert not Provider(remote, None).available()
