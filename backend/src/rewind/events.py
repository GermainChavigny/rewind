"""Events pushed to the TV page (Server-Sent Events): virtual remote presses,
the A/V sync test, chime previews. Publishing works from any thread."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import AsyncIterator

KEEPALIVE_S = 15


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []

    @property
    def listeners(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def publish(self, event: dict) -> int:
        """Sends the event to every connected TV page; returns how many got it."""
        with self._lock:
            subscribers = list(self._subscribers)
        for loop, queue in subscribers:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        return len(subscribers)

    async def stream(self) -> AsyncIterator[str]:
        """SSE lines for one subscriber, with keep-alive comments."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        entry = (loop, queue)
        with self._lock:
            self._subscribers.append(entry)
        try:
            yield ": connected\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), KEEPALIVE_S)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            with self._lock:
                self._subscribers.remove(entry)
