import json

import pytest

from rewind.config import ConfigStore
from rewind.db import Database
from rewind.tools.import_v1 import import_v1
from rewind.tools.migrate_v1 import migrate_v1

STATE_MANAGER_JS = """
    this.playlists = [
      {id: 'PLnews', logo: 'newsTV.png', name: 'News', noSave: true},
      {id: 'PLdunk', logo: 'dunkTV.png', name: 'Basketball'},
      {id: 'PLwake', logo: 'WakeUpTV.png', name: 'Wake Up', isAlarm: true},
      {id: 'movies', logo: 'MovieTV.png', name: 'Movies', isMovieMode: true},
    ];
"""
API_PY = """
TV_CONTROL_URL = 'http://192.168.1.19/rpc/Switch.Set'
WEATHER_LAT, WEATHER_LON = 47.39, 0.69
            "code": codes[idx], "hour": times[idx][11:16], "location": "Tours",
"""
XINITRC = """
  xrandr --output HDMI-2 --mode 720x576
  pactl set-port-latency-offset alsa_card.pci-0000_00_0e.0 analog-output-headphones 200000
"""
SECRETS = {
    "tmdb": {"apiKey": "tmdb-k"},
    "opensubtitles": {"apiKey": "os-k", "username": "me", "password": "pw"},
    "gemini": {"apiKey": "gem-k", "model": "gemini-2.5-flash"},
    "openRouter": {"apiKey": "", "model": "x"},
    "advisorFallbacks": [
        {"name": "Groq", "baseUrl": "https://api.groq.com/openai/v1", "apiKey": "g", "model": "l"}
    ],
    "indexers": [
        {"name": "Jackett", "type": "torznab", "url": "http://127.0.0.1:9117", "apiKey": "j",
         "indexer": "all", "filter": {"minSeeders": 2, "maxSizeGb": 8}}
    ],
}  # fmt: skip
LIBRARY = {
    "heat-1995": {
        "id": "heat-1995", "title": "Heat", "year": 1995, "tmdbId": 949, "poster": "heat-1995.jpg",
        "file": "heat-1995.mp4", "subtitles": {"fr": "heat-1995.fr.vtt"}, "duration": 10000,
        "status": "ready", "currentTime": 1234.5, "watched": False, "subtitleMode": "fr",
        "subtitleOffset": 0.3, "stagingFile": "/home/tv/tv_data/downloads/x.mkv",
        "addedAt": 1784052631, "lastPlayedAt": 1794419284, "magnet": "magnet:?xt=1",
    },
    "show-1989-s03e10": {
        "id": "show-1989-s03e10", "type": "episode", "showId": "show-1989", "season": 3,
        "episode": 10, "title": "Show S03E10", "status": "ready", "magnet": "None",
        "file": "show-1989-s03e10.mp4", "addedAt": 1787040335, "currentTime": 0.0,
        "audioTracks": [{"index": 0, "lang": "eng", "title": ""}],
    },
    "show-1989": {
        "id": "show-1989", "type": "series", "title": "Show", "originalTitle": "The Show",
        "numberOfSeasons": 38, "seasons": [{"seasonNumber": 1, "episodeCount": 13}],
        "status": "ready", "addedAt": 1784488020,
    },
    "show-1989-pack-s03": {
        "id": "show-1989-pack-s03", "type": "pack", "showId": "show-1989", "season": 3,
        "title": "Show — Saison 3", "status": "error", "error": "dead magnet",
        "targets": [{"season": 3, "episode": 1}], "addedAt": 1787000000,
    },
}  # fmt: skip
PROGRESS = {
    "PLdunk": {
        "currentTime": 117.3, "videoId": "v6", "videoIndex": 8,
        "videos": {
            "PLdunk|v6": {"currentTime": 117.3, "timestamp": 1791675886555, "videoId": "v6"},
            "PLdunk|v5": {"currentTime": 64.9, "timestamp": 1791675758544, "videoId": "v5"},
        },
    }
}  # fmt: skip


@pytest.fixture
def v1(tmp_path):
    tv_data, movies, app = tmp_path / "tv_data", tmp_path / "movies", tmp_path / "app_tv"
    (tv_data / "posters").mkdir(parents=True)
    movies.mkdir()
    (app / "modules").mkdir(parents=True)
    (app / "logos").mkdir()
    (tv_data / "library.json").write_text(json.dumps(LIBRARY))
    (tv_data / "progression.json").write_text(json.dumps(PROGRESS))
    (tv_data / "alarm.json").write_text('{"time": "08:50", "enabled": true}')
    (tv_data / "secrets.json").write_text(json.dumps(SECRETS))
    (tv_data / "advisor_blacklist.json").write_text(
        json.dumps({"x-1999": {"id": "x-1999", "title": "X", "year": 1999, "addedAt": 1}})
    )
    (tv_data / "posters" / "heat-1995.jpg").write_bytes(b"jpg")
    (movies / "heat-1995.mp4").write_bytes(b"v")
    (app / "modules" / "StateManager.js").write_text(STATE_MANAGER_JS)
    (app / "api.py").write_text(API_PY)
    (app / "config.js").write_text("")
    (app / "logos" / "newsTV.png").write_bytes(b"png")
    (tmp_path / "xinitrc").write_text(XINITRC)
    return tv_data, movies, app, tmp_path / "xinitrc"


def run(v1, paths, **kw):
    tv_data, movies, app, xinitrc = v1
    assert import_v1(tv_data, movies, paths, app, xinitrc).ok
    return migrate_v1(paths, **kw)


def test_config_from_v1(v1, paths):
    report = run(v1, paths)
    assert report.config_written
    cfg = ConfigStore(paths.config / "config.toml").get()
    assert [(c.id, c.kind, c.save_progress, c.alarm) for c in cfg.channels] == [
        ("news", "youtube", False, False),
        ("basketball", "youtube", True, False),
        ("wake-up", "youtube", True, True),
        ("movies", "library", True, False),
    ]
    assert cfg.channels[0].logo == "custom:newsTV.png" and cfg.channels[0].playlist_id == "PLnews"
    assert cfg.power.provider == "shelly" and cfg.power.shelly_host == "192.168.1.19"
    assert (cfg.weather.latitude, cfg.weather.longitude) == (47.39, 0.69)
    assert cfg.weather.location_name == "Tours"
    assert cfg.audio.av_offset_ms == 200 and cfg.audio.output_port == "analog-output-headphones"
    assert (cfg.display.output, cfg.display.mode) == ("HDMI-A-2", "720x576")
    assert cfg.tmdb.api_key == "tmdb-k" and cfg.opensubtitles.password == "pw"
    assert [(i.url, i.min_seeders, i.max_size_gb) for i in cfg.indexers] == [
        ("http://127.0.0.1:9117", 2, 8)
    ]
    assert [(p.name, p.kind) for p in cfg.advisor] == [("Gemini", "gemini"), ("Groq", "openai")]


def test_db_from_v1(v1, paths):
    run(v1, paths)
    db = Database(paths.data / "rewind.db")
    heat = db.get_media("heat-1995")
    assert heat["kind"] == "movie" and heat["position"] == 1234.5
    assert heat["last_played_at"] == 1794419284 and heat["tmdb_id"] == 949
    assert heat["subtitle_offsets"] == {"fr": 0.3}
    assert "staging_file" not in heat and "stagingFile" not in heat
    ep = db.get_media("show-1989-s03e10")
    assert ep["parent_id"] == "show-1989" and ep["magnet"] is None and ep["season"] == 3
    show = db.get_media("show-1989")
    assert show["original_title"] == "The Show" and show["seasons"][0]["episode_count"] == 13
    assert db.get_media("show-1989-pack-s03")["parent_id"] == "show-1989"
    p = db.get_playlist_progress("PLdunk")
    assert p["video_id"] == "v6" and p["videos"] == {"v6": 117.3, "v5": 64.9}
    assert db.get_kv("alarm") == {"time": "08:50", "enabled": True}
    assert [b["title"] for b in db.blacklist()] == ["X"]
    assert (paths.data / "posters" / "heat-1995.jpg").exists()
    assert (paths.data / "logos" / "newsTV.png").exists()


def test_rerun_refreshes_db_but_keeps_config(v1, paths):
    run(v1, paths)
    store = ConfigStore(paths.config / "config.toml")
    cfg = store.get()
    cfg.weather.location_name = "Edited in v2"
    store.save(cfg)
    db = Database(paths.data / "rewind.db")
    db.patch_media("heat-1995", {"position": 1})

    report = run(v1, paths)
    assert not report.config_written
    assert ConfigStore(paths.config / "config.toml").get().weather.location_name == "Edited in v2"
    assert db.get_media("heat-1995")["position"] == 1234.5  # refreshed from v1

    assert run(v1, paths, overwrite_config=True).config_written
    assert ConfigStore(paths.config / "config.toml").get().weather.location_name == "Tours"
