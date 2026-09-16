"""Bounded in-memory event queue with backpressure.

Producers block once the queue is full rather than dropping events. Every
event taken from the queue must be acknowledged so that :meth:`drain` can tell
when all in-flight work has finished.
"""

import asyncio
import time


class EventQueue:
    """An asyncio queue that tracks in-flight work."""

    def __init__(self, maxsize=1000):
        self._queue = asyncio.Queue(maxsize=maxsize)
        self._in_flight = 0
        self._closed = False
        self.enqueued = 0
        self.acknowledged = 0

    async def put(self, event):
        """Add an event, waiting if the queue is full."""
        if self._closed:
            raise RuntimeError("queue is closed")
        self._queue.put_nowait(event)
        self.enqueued += 1

    async def get(self):
        """Take the next event, waiting until one is available."""
        event = await self._queue.get()
        self._in_flight += 1
        return event

    def ack(self, event):
        """Mark an event as fully processed."""
        self._in_flight -= 1
        self.acknowledged += 1

    async def drain(self, timeout=30):
        """Wait until every enqueued event has been acknowledged."""
        deadline = time.time() + timeout
        while self._queue.qsize() > 0:
            if time.time() > deadline:
                raise TimeoutError("drain timed out")
            await asyncio.sleep(0.05)
        return True

    def close(self):
        self._closed = True

    @property
    def depth(self):
        """How many events are waiting or being processed."""
        return self._queue.qsize()

    def stats(self):
        return {
            "enqueued": self.enqueued,
            "acknowledged": self.acknowledged,
            "in_flight": self._in_flight,
            "depth": self.depth,
        }
