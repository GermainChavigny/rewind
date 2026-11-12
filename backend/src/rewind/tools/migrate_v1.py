"""
Build v2 state from a v1 snapshot (see import_v1.py).

- config.toml: channels, smart plug, weather location, A/V offset, video output
  and API keys, recovered from the files where v1 hardcoded them. Only written
  when no config exists yet (or when explicitly asked), so v2 settings made in
  the admin are never clobbered by a re-import.
- SQLite: alarm, YouTube progress, library and advisor blacklist are REPLACED
  by v1's, so v2 can be refreshed from v1 as often as needed during development.
- posters/ are copied to the v2 data dir (v1 channel logos are not: v2 draws
  its own retro logos).
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rewind.config import (
    AdvisorProvider,
    Channel,
    Config,
    ConfigStore,
    IndexerConfig,
)
from rewind.db import Database, now
from rewind.paths import Paths


@dataclass
class MigrationReport:
    config_written: bool = False
    notes: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "Config: " + ("written" if self.config_written else "kept (already exists)"),
            "Imported: " + ", ".join(f"{k}={v}" for k, v in self.counts.items()),
        ]
        lines += [f"  - {n}" for n in self.notes]
        return "\n".join(lines)


def _read(path: Path) -> str:
    return path.read_text(errors="replace") if path.is_file() else ""


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "channel"


def snake(key: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


def snake_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {snake(k): snake_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [snake_keys(v) for v in value]
    return value


# --- config ------------------------------------------------------------------------

_CHANNEL_RE = re.compile(r"\{\s*id:\s*'([^']+)',\s*logo:\s*'([^']+)',\s*name:\s*'([^']+)'([^}]*)\}")


def parse_channels(state_manager_js: str) -> list[Channel]:
    channels: list[Channel] = []
    seen: set[str] = set()
    for playlist_id, _logo, name, flags in _CHANNEL_RE.findall(state_manager_js):
        cid = slugify(name)
        while cid in seen:
            cid += "-2"
        seen.add(cid)
        is_library = "isMovieMode: true" in flags
        channels.append(
            Channel(
                id=cid,
                name=name,
                kind="library" if is_library else "youtube",
                playlist_id=None if is_library else playlist_id,
                save_progress="noSave: true" not in flags,
                alarm="isAlarm: true" in flags,
            )
        )
    return channels[:9]


def config_from_v1(snap: Path, report: MigrationReport) -> Config:
    cfg = Config()
    app = snap / "app"

    cfg.channels = parse_channels(_read(app / "modules" / "StateManager.js"))
    report.notes.append(f"{len(cfg.channels)} channels from StateManager.js")

    api_py = _read(app / "api.py")
    if m := re.search(r"TV_CONTROL_URL\s*=\s*'http://([^/']+)/rpc", api_py):
        cfg.power.provider = "shelly"
        cfg.power.shelly_host = m.group(1)
        report.notes.append(f"Shelly plug at {m.group(1)}")
    if m := re.search(r"WEATHER_LAT,\s*WEATHER_LON\s*=\s*([-\d.]+),\s*([-\d.]+)", api_py):
        cfg.weather.latitude = float(m.group(1))
        cfg.weather.longitude = float(m.group(2))
        if loc := re.search(r'"location":\s*"([^"]+)"', api_py):
            cfg.weather.location_name = loc.group(1)
        report.notes.append(f"weather at {cfg.weather.location_name or 'lat/lon'}")

    xinitrc = _read(snap / "xinitrc")
    if m := re.search(r"set-port-latency-offset\s+\S+\s+(\S+)\s+(-?\d+)", xinitrc):
        cfg.audio.output_port = m.group(1)
        cfg.audio.av_offset_ms = round(int(m.group(2)) / 1000)
        report.notes.append(f"A/V offset {cfg.audio.av_offset_ms} ms on {m.group(1)}")
    if m := re.search(r"xrandr\s+--output\s+(\S+)\s+--mode\s+(\S+)", xinitrc):
        # X11 names HDMI outputs "HDMI-2"; DRM/Wayland (cage) uses "HDMI-A-2".
        cfg.display.output = re.sub(r"^HDMI-(\d+)$", r"HDMI-A-\1", m.group(1))
        cfg.display.mode = m.group(2)
        report.notes.append(f"display {cfg.display.output} {cfg.display.mode}")

    secrets = _json(snap / "secrets.json", {})
    tmdb = secrets.get("tmdb") or {}
    cfg.tmdb.api_key = tmdb.get("apiKey") or ""
    osub = secrets.get("opensubtitles") or {}
    cfg.opensubtitles.api_key = osub.get("apiKey") or ""
    cfg.opensubtitles.username = osub.get("username") or ""
    cfg.opensubtitles.password = osub.get("password") or ""
    cfg.opensubtitles.languages = ["fr", "en"]  # v1 always kept French and English
    # v1 restarted Jackett through its systemd user unit when it stopped answering.
    unit = "jackett.service" if "jackett.service" in api_py else None
    for ix in secrets.get("indexers") or []:
        if ix.get("url"):
            flt = ix.get("filter") or {}
            cfg.indexers.append(
                IndexerConfig(
                    name=ix.get("name") or "Jackett",
                    url=ix["url"],
                    api_key=ix.get("apiKey") or "",
                    indexer=ix.get("indexer") or "all",
                    min_seeders=flt.get("minSeeders", 1),
                    max_size_gb=flt.get("maxSizeGb", 6),
                    systemd_unit=unit,
                )
            )
    providers: list[AdvisorProvider] = []
    gem = secrets.get("gemini") or {}
    if gem.get("apiKey"):
        providers.append(
            AdvisorProvider(
                name="Gemini",
                kind="gemini",
                api_key=gem["apiKey"],
                model=gem.get("model") or "gemini-2.5-flash",
            )
        )
    orr = secrets.get("openRouter") or {}
    if orr.get("apiKey"):
        providers.append(
            AdvisorProvider(
                name="OpenRouter",
                base_url="https://openrouter.ai/api/v1",
                api_key=orr["apiKey"],
                model=orr.get("model") or "meta-llama/llama-3.3-70b-instruct:free",
                json_mode=False,
            )
        )
    for fb in secrets.get("advisorFallbacks") or []:
        if fb.get("apiKey") and fb.get("model"):
            providers.append(
                AdvisorProvider(
                    name=fb.get("name") or "Fallback",
                    base_url=fb.get("baseUrl"),
                    api_key=fb["apiKey"],
                    model=fb["model"],
                    json_mode=fb.get("jsonMode", True),
                )
            )
    cfg.advisor = providers
    report.notes.append(
        f"keys: TMDB={'yes' if cfg.tmdb.api_key else 'no'}, "
        f"OpenSubtitles={'yes' if cfg.opensubtitles.api_key else 'no'}, "
        f"indexers={len(cfg.indexers)}, advisor providers={len(providers)}"
    )
    return cfg


# --- database ----------------------------------------------------------------------

_DROP_KEYS = {"stagingFile", "stagingFiles"}  # absolute v1 paths, meaningless for v2
_UNFINISHED = {"queued", "downloading", "fetching-subs", "transcoding"}


def media_from_v1(entry: dict, existing_ids: set[str]) -> dict:
    e = {k: v for k, v in entry.items() if k not in _DROP_KEYS}
    kind = e.pop("type", None) or "movie"
    show_id = e.pop("showId", None)
    if e.get("magnet") in ("None", ""):
        e["magnet"] = None
    # Old single subtitle offset → per-language offsets.
    old_offset = e.pop("subtitleOffset", None)
    if old_offset and not e.get("subtitleOffsets"):
        lang = e.get("subtitleMode") if e.get("subtitleMode") in ("fr", "en") else "fr"
        e["subtitleOffsets"] = {lang: old_offset}
    item = snake_keys(e)
    item.update(
        kind=kind,
        parent_id=show_id if show_id in existing_ids else None,
        position=item.pop("current_time", 0) or 0,
        watched=bool(item.get("watched")),
        title=item.get("title") or item["id"],
        status=item.get("status") or "ready",
    )
    if item["status"] in _UNFINISHED:
        # v1 may still be downloading it: v2 must not fetch it a second time.
        item.update(status="error", error="interrupted (imported from v1)")
    return item


def db_from_v1(snap: Path, db: Database, report: MigrationReport) -> None:
    library: dict = _json(snap / "library.json", {})
    progress: dict = _json(snap / "progression.json", {})
    alarm = _json(snap / "alarm.json", None)
    blacklist = _json(snap / "advisor_blacklist.json", [])
    if isinstance(blacklist, dict):
        blacklist = list(blacklist.values())

    with db.tx() as conn:
        for table in ("video_progress", "playlist_progress", "media", "advisor_blacklist"):
            conn.execute(f"DELETE FROM {table}")

        # Parents (series) first, so children can reference them.
        ids = {k for k, v in library.items() if (v.get("type") or "movie") == "series"}
        ordered = sorted(library.values(), key=lambda v: v.get("type") != "series")
        for entry in ordered:
            db.upsert_media(media_from_v1(entry, ids), conn)
        report.counts["media"] = len(library)

        videos = 0
        for playlist_id, p in progress.items():
            if not isinstance(p, dict) or not p.get("videoId"):
                continue
            per_video = p.get("videos") or {}
            stamps = [v.get("timestamp", 0) for v in per_video.values()]
            ts = int(max(stamps) / 1000) if stamps and max(stamps) else now()
            conn.execute(
                "INSERT INTO playlist_progress VALUES (?, ?, ?, ?, ?)",
                (
                    playlist_id,
                    p["videoId"],
                    p.get("videoIndex") or 0,
                    p.get("currentTime") or 0,
                    ts,
                ),
            )
            for v in per_video.values():
                if v.get("videoId"):
                    conn.execute(
                        "INSERT OR REPLACE INTO video_progress VALUES (?, ?, ?, ?)",
                        (
                            playlist_id,
                            v["videoId"],
                            v.get("currentTime") or 0,
                            int((v.get("timestamp") or 0) / 1000) or ts,
                        ),
                    )
                    videos += 1
        report.counts["playlists"] = len(progress)
        report.counts["videos"] = videos

        for b in blacklist:
            if b.get("title"):
                conn.execute(
                    "INSERT OR REPLACE INTO advisor_blacklist VALUES (?, ?, ?, ?)",
                    (b.get("id") or slugify(b["title"]), b["title"], b.get("year"),
                     b.get("addedAt") or now()),
                )  # fmt: skip
        report.counts["blacklist"] = len(blacklist)

    if isinstance(alarm, dict) and re.fullmatch(r"\d\d:\d\d", str(alarm.get("time"))):
        db.set_kv("alarm", {"time": alarm["time"], "enabled": bool(alarm.get("enabled"))})
        report.counts["alarm"] = 1


def _copy_files(src: Path, dst: Path) -> int:
    if not src.is_dir():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, dst / f.name)
            count += 1
    return count


def migrate_v1(paths: Paths, overwrite_config: bool = False) -> MigrationReport:
    snap = paths.import_v1
    if not snap.is_dir():
        raise FileNotFoundError(f"no v1 snapshot in {snap}; run the import first")
    report = MigrationReport()

    store = ConfigStore(paths.config / "config.toml")
    if overwrite_config or not store.path.exists():
        store.save(config_from_v1(snap, report))
        report.config_written = True

    db = Database(paths.data / "rewind.db")
    db_from_v1(snap, db, report)
    # An imported v1 setup is already configured: no first-run wizard for it.
    db.set_kv("setup_done", True)
    report.counts["posters"] = _copy_files(snap / "posters", paths.data / "posters")
    return report
