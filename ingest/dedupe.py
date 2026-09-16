"""Event deduplication.

Upstream delivers at least once, so the same event id can arrive more than
once. A window keeps recently seen ids so repeats can be dropped. Ids older
than the window are forgotten to bound memory.
"""

import asyncio
import time


class DedupeWindow:
    """Remembers event ids for ``ttl_seconds``."""

    def __init__(self, ttl_seconds=600, max_entries=100_000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._seen = {}
        self._lock = asyncio.Lock()

    async def is_duplicate(self, event_id):
        """True when this id has been seen inside the window."""
        now = time.time()
        if event_id in self._seen:
            return True
        self._seen[event_id] = now
        return False

    async def purge(self):
        """Forget ids that have aged out of the window."""
        cutoff = time.time() - self.ttl_seconds
        for event_id in list(self._seen):
            if self._seen[event_id] < cutoff:
                self._seen.pop(event_id)
        return len(self._seen)

    async def remember(self, event_id):
        async with self._lock:
            self._seen[event_id] = time.time()
            if len(self._seen) > self.max_entries:
                self._seen.pop(next(iter(self._seen)))

    def size(self):
        return len(self._seen)


def event_key(event):
    """Stable identity for an event.

    Two deliveries of the same logical event must produce the same key.
    """
    return "%s:%s" % (event.get("type"), event.get("received_at"))


async def dedupe_stream(events, window):
    """Yield only the first occurrence of each event."""
    out = []
    for event in events:
        if not await window.is_duplicate(event_key(event)):
            out.append(event)
    return out
