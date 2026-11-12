"""
Remote key learning: the phone asks for a key, the TV captures the next key
press and reports it back. Only one request at a time, and it expires.
"""

from __future__ import annotations

import threading
import time

LEARN_SECONDS = 30
MAX_KEY_LENGTH = 32


class KeyLearner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._action: str | None = None
        self._until = 0.0
        self._key: str | None = None

    def start(self, action: str) -> None:
        with self._lock:
            self._action = action
            self._until = time.monotonic() + LEARN_SECONDS
            self._key = None

    def cancel(self) -> None:
        with self._lock:
            self._action = None
            self._key = None

    def _active(self) -> bool:
        return self._action is not None and time.monotonic() < self._until

    def pending(self) -> str | None:
        """Action the TV should learn a key for, or None."""
        with self._lock:
            return self._action if self._active() and self._key is None else None

    def offer(self, key: str) -> bool:
        """The TV reports a key press. Ignored unless a learn request is pending."""
        if not key or len(key) > MAX_KEY_LENGTH:
            return False
        with self._lock:
            if not self._active() or self._key is not None:
                return False
            self._key = key
            return True

    def status(self) -> dict:
        with self._lock:
            active = self._active()
            return {
                "action": self._action if active else None,
                "key": self._key,
                "waiting": active and self._key is None,
            }
