"""
BitTorrent downloads (libtorrent) and the magnet reachability probe.

libtorrent is optional (no wheel for every platform): without it, downloads
are reported as unavailable and everything else keeps working.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from pathlib import Path

try:
    import libtorrent as lt
except ImportError:  # pragma: no cover - depends on the platform
    lt = None

log = logging.getLogger(__name__)

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".webm", ".ts", ".wmv", ".flv"}
MIN_VIDEO_BYTES = 60 * 1024 * 1024  # smaller files are samples

ProgressCb = Callable[[float], None]


class Cancelled(RuntimeError):
    pass


def _session(port: int):
    return lt.session(
        {
            "listen_interfaces": f"0.0.0.0:{port},[::]:{port}",
            "enable_dht": True,
            "enable_lsd": True,  # peers on the local network
            "user_agent": "rewind/0.1",
        }
    )


class TorrentClient:
    """One shared libtorrent session; each download has its own handle (thread-safe)."""

    def __init__(self, downloads_dir: Path, port: int):
        self.dir = downloads_dir
        self.port = port
        self._session = None
        self._lock = threading.Lock()

    @staticmethod
    def available() -> bool:
        return lt is not None

    def _ensure(self):
        with self._lock:
            if self._session is None:
                self._session = _session(self.port)
            return self._session

    def download(
        self,
        magnet: str,
        progress: ProgressCb | None = None,
        cancelled: Callable[[], bool] = lambda: False,
        meta_timeout: float = 120,
        poll: float = 1.0,
    ) -> list[Path]:
        """Download a magnet; returns its video files sorted by name (samples excluded)."""
        if lt is None:
            raise RuntimeError("libtorrent is not installed")
        session = self._ensure()
        self.dir.mkdir(parents=True, exist_ok=True)
        params = lt.parse_magnet_uri(magnet)
        params.save_path = str(self.dir)
        handle = session.add_torrent(params)
        # Sequential: the files of a season pack complete in order.
        handle.set_flags(lt.torrent_flags.sequential_download)
        try:
            deadline = time.monotonic() + meta_timeout
            while not handle.status().has_metadata:
                if cancelled():
                    raise Cancelled("cancelled")
                if time.monotonic() > deadline:
                    raise RuntimeError("no metadata (dead magnet?)")
                time.sleep(0.5)
            while True:
                if cancelled():
                    raise Cancelled("cancelled")
                status = handle.status()
                if progress:
                    progress(min(1.0, status.progress))
                if status.is_finished or status.progress >= 1.0:
                    break
                time.sleep(poll)
            videos = self._videos(handle)
        except BaseException:
            session.remove_torrent(handle, lt.session.delete_files)
            raise
        session.remove_torrent(handle)  # keep the files, no seeding
        if not videos:
            raise RuntimeError("no video file in the torrent")
        return videos

    def _videos(self, handle) -> list[Path]:
        info = handle.torrent_file()
        if info is None:
            return []
        files = info.files()
        out = []
        for i in range(files.num_files()):
            path = Path(files.file_path(i))
            if path.suffix.lower() not in VIDEO_EXTS or "sample" in path.name.lower():
                continue
            if files.file_size(i) < MIN_VIDEO_BYTES:
                continue
            out.append(self.dir / path)
        return sorted(out, key=lambda p: str(p).lower())


class Prober:
    """
    Can a magnet's metadata be fetched quickly (= are there reachable peers)?
    Private-tracker magnets show many seeders but no peer without a passkey.
    Several probes run in parallel, most-seeded first; results are cached.
    A dedicated session (another port) leaves the downloads alone.
    """

    TIMEOUT = 25
    WORKERS = 4
    CACHE_TTL = 600

    def __init__(self, probe_dir: Path, port: int):
        self.dir = probe_dir
        self.port = port
        self._session = None
        self._lock = threading.Lock()
        self._results: dict[str, dict] = {}
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._seq = 0

    def _ensure(self) -> None:
        with self._lock:
            if self._session is not None:
                return
            self._session = _session(self.port)
            self.dir.mkdir(parents=True, exist_ok=True)
            for _ in range(self.WORKERS):
                threading.Thread(target=self._worker, daemon=True, name="probe").start()

    def submit(self, items: list[dict]) -> None:
        """items: [{hash, magnet, seeders}]; skips hashes probed recently."""
        if lt is None:
            return
        now = time.time()
        with self._lock:
            for it in items:
                h = (it.get("hash") or "").lower()
                if not h or not it.get("magnet"):
                    continue
                known = self._results.get(h)
                if known and (known["state"] == "pending" or now - known["at"] < self.CACHE_TTL):
                    continue
                self._results[h] = {"state": "pending", "at": now}
                self._seq += 1
                self._queue.put((-(it.get("seeders") or 0), self._seq, h, it["magnet"]))
        self._ensure()

    def status(self, hashes: list[str]) -> dict[str, str]:
        """reachable | unreachable | pending | unknown, per hash."""
        with self._lock:
            return {
                h.lower(): self._results.get(h.lower(), {}).get("state", "unknown") for h in hashes
            }

    def _worker(self) -> None:
        while True:
            _, _, h, magnet = self._queue.get()
            try:
                state = self._probe(magnet)
            except Exception:  # noqa: BLE001 - a probe must never kill its worker
                state = "unreachable"
            with self._lock:
                self._results[h] = {"state": state, "at": time.time()}

    def _probe(self, magnet: str) -> str:
        params = lt.parse_magnet_uri(magnet)
        params.save_path = str(self.dir)
        handle = self._session.add_torrent(params)
        try:
            deadline = time.monotonic() + self.TIMEOUT
            while time.monotonic() < deadline:
                if handle.status().has_metadata:
                    return "reachable"
                time.sleep(0.5)
            return "unreachable"
        finally:
            self._session.remove_torrent(handle, lt.session.delete_files)
