"""
External sources: Torznab indexers (Jackett, Prowlarr…) and TMDB metadata,
plus the release-name helpers (episode numbers, clean titles, magnets).
"""

from __future__ import annotations

import logging
import re
import socket
import subprocess
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from threading import Lock
from urllib.parse import quote, urlparse

import httpx

from rewind.config import IndexerConfig

log = logging.getLogger(__name__)

# Public trackers appended to magnets built from a bare info-hash.
DEFAULT_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://tracker.torrent.eu.org:451/announce",
]

# Torznab TV categories (5000 = TV and its sub-categories).
CAT_TV = "5000,5010,5020,5030,5040,5045,5050,5060,5070,5080"


# --- release names ------------------------------------------------------------------


def magnet_hash(magnet: str | None) -> str | None:
    """Info-hash (btih) of a magnet, lowercase — the de-duplication key."""
    m = re.search(r"btih:([0-9a-zA-Z]+)", magnet or "")
    return m.group(1).lower() if m else None


def build_magnet(info_hash: str, name: str | None = None) -> str:
    magnet = f"magnet:?xt=urn:btih:{info_hash}"
    if name:
        magnet += f"&dn={quote(name)}"
    return magnet + "".join(f"&tr={quote(tr)}" for tr in DEFAULT_TRACKERS)


def human_size(num_bytes: int | None) -> str | None:
    if not num_bytes:
        return None
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


_EPISODE = [
    re.compile(r"\bS(\d{1,2})[\s._-]*E(\d{1,3})", re.I),  # S02E03, S02.E03
    re.compile(r"\b(\d{1,2})x(\d{1,3})\b", re.I),  # 2x03
    re.compile(r"\bSeason[\s._-]*(\d{1,2})[\s._-]*Episode[\s._-]*(\d{1,3})", re.I),
]
_SEASON = [
    re.compile(r"\bS(\d{1,2})\b(?![\s._-]*E\d)", re.I),  # S02 (season pack)
    re.compile(r"\bSeason[\s._-]*(\d{1,2})\b", re.I),
]


def parse_episode(name: str | None) -> tuple[int, int | None] | None:
    """(season, episode) from a release or file name; episode is None for a season pack."""
    for pattern in _EPISODE:
        if m := pattern.search(name or ""):
            return int(m.group(1)), int(m.group(2))
    for pattern in _SEASON:
        if m := pattern.search(name or ""):
            return int(m.group(1)), None
    return None


_TAGS = re.compile(
    r"\b(720p|1080p|2160p|480p|4k|x264|x265|h\.?264|h\.?265|hevc|xvid|divx|"
    r"blu-?ray|brrip|bdrip|web-?rip|web-?dl|hdtv|dvd-?rip|hd-?rip|remux|"
    r"aac|ac3|dts|dd5\.?1|opus|10bits?|hdr10?|dv|"
    r"yify|yts|rarbg|extended|remastered|proper|repack|unrated|directors?\.?cut|"
    r"multi|vff|vfq|vostfr|truefrench|french|ita|eng|dual|lat).*$",
    re.I,
)


def clean_title(raw: str | None) -> tuple[str, int | None]:
    """'Leon The Professional Extended (1994) [1080p]' → ('Leon The Professional', 1994)."""
    year_match = re.search(r"\b(19|20)\d{2}\b", raw or "")
    year = int(year_match.group(0)) if year_match else None
    title = re.split(r"[([]", raw or "")[0]
    title = re.sub(r"[._]+", " ", title)
    title = _TAGS.sub("", title)
    title = re.sub(r"\b(19|20)\d{2}\b", "", title)
    return re.sub(r"\s+", " ", title).strip(" -"), year


def slugify(title: str, year: int | None = None) -> str:
    """'SOS Fantômes', 1984 → 'sos-fantomes-1984' (ids and file names)."""
    ascii_title = unicodedata.normalize("NFKD", str(title)).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-") or "item"
    return f"{slug}-{year}" if year else slug


# --- indexers -----------------------------------------------------------------------


@dataclass
class Release:
    title: str
    magnet: str
    seeders: int
    size: int | None
    imdb_id: str | None = None

    @property
    def hash(self) -> str | None:
        return magnet_hash(self.magnet)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "magnet": self.magnet,
            "hash": self.hash,
            "seeders": self.seeders,
            "size": self.size,
            "size_label": human_size(self.size),
            "imdb_id": self.imdb_id,
        }


_TZ = "{http://torznab.com/schemas/2015/feed}"
_kick_lock = Lock()


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


class Indexers:
    """Search the configured Torznab indexers; one failing indexer never breaks a search."""

    def __init__(self, configs: list[IndexerConfig], http: httpx.Client):
        self.configs = configs
        self.http = http

    def available(self) -> bool:
        return bool(self.configs)

    def search(self, query: str, limit: int = 20, cat: str | None = None) -> list[Release]:
        results: list[Release] = []
        for cfg in self.configs:
            self.ensure_up(cfg)
            try:
                results.extend(self._torznab(cfg, query, limit, cat))
            except (httpx.HTTPError, ET.ParseError) as err:
                # httpx puts the full URL (API key included) in its messages.
                log.warning("indexer %s failed: %s", cfg.name, _redact(str(err), cfg.api_key))
        results.sort(key=lambda r: r.seeders, reverse=True)
        return results[:limit]

    def _torznab(
        self, cfg: IndexerConfig, query: str, limit: int, cat: str | None
    ) -> list[Release]:
        url = f"{cfg.url.rstrip('/')}/api/v2.0/indexers/{cfg.indexer}/results/torznab/api"
        params = {"apikey": cfg.api_key, "t": "search", "q": query}
        if cat:
            params["cat"] = cat
        resp = self.http.get(url, params=params, timeout=cfg.timeout_s)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        max_bytes = int(cfg.max_size_gb * 1024**3) if cfg.max_size_gb else None
        fitting: list[Release] = []
        oversized: list[Release] = []
        seen: set[str] = set()
        for item in root.iter("item"):
            title = (item.findtext("title") or "?").strip()
            attrs = {a.get("name"): a.get("value") for a in item.findall(f"{_TZ}attr")}
            # Magnet: magneturl, else a magnet <link>/<enclosure>, else rebuilt from
            # the info-hash. Plain .torrent HTTP links are ignored.
            magnet = attrs.get("magneturl")
            link = item.findtext("link") or ""
            if not magnet and link.startswith("magnet:"):
                magnet = link
            enclosure = item.find("enclosure")
            enc_url = (enclosure.get("url") or "") if enclosure is not None else ""
            if not magnet and enc_url.startswith("magnet:"):
                magnet = enc_url
            if not magnet and attrs.get("infohash"):
                magnet = build_magnet(attrs["infohash"], title)
            if not magnet:
                continue
            key = magnet_hash(magnet) or magnet
            if key in seen:
                continue
            seen.add(key)
            seeders = _int(attrs.get("seeders"))
            if seeders < cfg.min_seeders:
                continue
            size = _int(item.findtext("size") or attrs.get("size")) or None
            release = Release(
                title, magnet, seeders, size, attrs.get("imdb") or attrs.get("imdbid")
            )
            (oversized if max_bytes and size and size > max_bytes else fitting).append(release)
        # Prefer releases under the size cap, but keep big ones if nothing else exists
        # (the transcoder brings them down to 720p anyway).
        chosen = fitting or oversized
        chosen.sort(key=lambda r: r.seeders, reverse=True)
        return chosen[:limit]

    @staticmethod
    def ensure_up(cfg: IndexerConfig, wait_s: float = 12) -> bool:
        """
        If the indexer's port is closed and a systemd user unit is configured,
        start it and wait a bit (v1: Jackett could die after a self-update and
        searches then returned nothing, instantly).
        """
        url = urlparse(cfg.url)
        host, port = url.hostname or "127.0.0.1", url.port or 9117
        if _port_open(host, port) or not cfg.systemd_unit:
            return True
        with _kick_lock:
            if _port_open(host, port):
                return True
            log.warning(
                "indexer %s:%s down → systemctl --user start %s", host, port, cfg.systemd_unit
            )
            try:
                subprocess.run(
                    ["systemctl", "--user", "start", cfg.systemd_unit],
                    capture_output=True,
                    timeout=10,
                )
            except (OSError, subprocess.SubprocessError) as err:
                log.warning("could not start %s: %s", cfg.systemd_unit, err)
                return False
            deadline = time.monotonic() + wait_s
            while time.monotonic() < deadline:
                time.sleep(1)
                if _port_open(host, port):
                    return True
        return False


def _port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


# --- TMDB ---------------------------------------------------------------------------


class Tmdb:
    """Movie and series metadata (posters, overviews, seasons). Free API key required."""

    BASE = "https://api.themoviedb.org/3"
    IMG = "https://image.tmdb.org/t/p"

    def __init__(self, api_key: str, language: str, http: httpx.Client):
        self.api_key = api_key
        self.language = language
        self.http = http

    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, **params: object) -> dict | None:
        if not self.api_key:
            return None
        params = {"api_key": self.api_key, "language": self.language, **params}
        try:
            resp = self.http.get(f"{self.BASE}{path}", params=params, timeout=8)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as err:
            log.warning("TMDB %s failed: %s", path, _redact(str(err), self.api_key))
            return None

    def _poster(self, path: str | None, size: str = "w500") -> str | None:
        return f"{self.IMG}/{size}{path}" if path else None

    @staticmethod
    def _year(date: str | None) -> int | None:
        y = (date or "")[:4]
        return int(y) if y.isdigit() else None

    def _movie(self, m: dict) -> dict:
        return {
            "tmdb_id": m.get("id"),
            "title": m.get("title"),
            "original_title": m.get("original_title") or m.get("title"),
            "year": self._year(m.get("release_date")),
            "poster_url": self._poster(m.get("poster_path")),
            "overview": m.get("overview") or None,
        }

    def _show(self, m: dict) -> dict:
        return {
            "tmdb_id": m.get("id"),
            "title": m.get("name"),
            "original_title": m.get("original_name") or m.get("name"),
            "year": self._year(m.get("first_air_date")),
            "poster_url": self._poster(m.get("poster_path")),
            "overview": m.get("overview") or None,
        }

    def search_movie(self, query: str, year: int | None = None) -> dict | None:
        params = {"query": query, **({"year": year} if year else {})}
        results = (self._get("/search/movie", **params) or {}).get("results") or []
        return self._movie(results[0]) if results else None

    def english_title(self, tmdb_id: int | None, kind: str = "movie") -> str | None:
        """Title in English, by id (torrent searches work best with it)."""
        if not tmdb_id:
            return None
        data = self._get(f"/{'tv' if kind == 'series' else 'movie'}/{tmdb_id}", language="en-US")
        return (data or {}).get("name" if kind == "series" else "title")

    def movie_overview(self, tmdb_id: int) -> str | None:
        return (self._get(f"/movie/{tmdb_id}") or {}).get("overview") or None

    def search_tv(self, query: str, year: int | None = None, limit: int = 10) -> list[dict]:
        params = {"query": query, **({"first_air_date_year": year} if year else {})}
        results = (self._get("/search/tv", **params) or {}).get("results") or []
        return [self._show(m) for m in results[:limit]]

    def tv_details(self, tmdb_id: int) -> dict | None:
        d = self._get(f"/tv/{tmdb_id}")
        if not d:
            return None
        return {
            **self._show(d),
            "tmdb_status": d.get("status"),
            "number_of_seasons": d.get("number_of_seasons"),
            # Real seasons only (season 0 = specials).
            "seasons": [
                {
                    "season_number": s.get("season_number"),
                    "episode_count": s.get("episode_count"),
                    "name": s.get("name"),
                }
                for s in d.get("seasons") or []
                if s.get("season_number")
            ],
        }

    def tv_season(self, tmdb_id: int, season: int) -> list[dict] | None:
        d = self._get(f"/tv/{tmdb_id}/season/{season}")
        if d is None:
            return None
        return [
            {
                "episode": e.get("episode_number"),
                "title": e.get("name"),
                "overview": e.get("overview") or None,
                "still": self._poster(e.get("still_path"), "w300"),
            }
            for e in d.get("episodes") or []
            if e.get("episode_number")
        ]

    def download(self, url: str | None, dest) -> bool:
        """Download a poster (or any image) to `dest`."""
        if not url:
            return False
        try:
            resp = self.http.get(url, timeout=15)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return True
        except (httpx.HTTPError, OSError) as err:
            log.warning("poster download failed: %s", err)
            return False
