"""Size-and-time batching.

Events are accumulated until either ``max_size`` is reached or ``max_wait``
seconds have passed since the batch was opened, whichever comes first. No
event ever waits longer than ``max_wait``.
"""

import asyncio
import time


class Batcher:
    """Groups events into batches before flushing them downstream."""

    def __init__(self, flush, max_size=100, max_wait=5.0):
        self.flush = flush
        self.max_size = max_size
        self.max_wait = max_wait
        self._buffer = []
        self._opened_at = None
        self._timer = None

    async def add(self, event):
        """Add an event, flushing if the batch is now full."""
        if not self._buffer:
            self._opened_at = time.time()
            self._timer = asyncio.create_task(self._flush_after_wait())

        self._buffer.append(event)

        if len(self._buffer) > self.max_size:
            await self._do_flush()

    async def _flush_after_wait(self):
        await asyncio.sleep(self.max_wait)
        await self._do_flush()

    async def _do_flush(self):
        if not self._buffer:
            return []
        batch = self._buffer
        await self.flush(batch)
        self._buffer = []
        self._opened_at = None
        return batch

    async def close(self):
        """Flush whatever is left."""
        if self._timer:
            self._timer.cancel()
        return await self._do_flush()

    def age(self):
        """How long the open batch has been waiting, in seconds."""
        if self._opened_at is None:
            return 0
        return time.time() - self._opened_at

    def pending(self):
        return len(self._buffer)
