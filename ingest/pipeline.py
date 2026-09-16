"""End-to-end ingestion pipeline.

Events arrive from the transport, are deduplicated, batched and handed to the
sink. The pipeline owns the lifecycle of every component it creates and must
shut all of them down cleanly.
"""

import asyncio
import logging

from ingest import batch, dedupe, queue, retry, worker

log = logging.getLogger(__name__)


class Pipeline:
    """Wires the ingestion components together."""

    def __init__(self, sink, concurrency=10, batch_size=100):
        self.sink = sink
        self.queue = queue.EventQueue(maxsize=5000)
        self.window = dedupe.DedupeWindow(ttl_seconds=600)
        self.batcher = batch.Batcher(self._write, max_size=batch_size)
        self.breaker = retry.CircuitBreaker(threshold=5)
        self.policy = retry.RetryPolicy(attempts=4)
        self.pool = worker.WorkerPool(self.queue, self._process, concurrency)
        self.dropped = 0
        self._purger = None

    async def _write(self, events):
        """Send one batch to the sink, through the breaker and retry policy."""
        return await self.breaker.guard(self.policy.call, self.sink.write, events)

    async def _process(self, event):
        """Handle a single event: dedupe, then hand to the batcher."""
        key = dedupe.event_key(event)
        if await self.window.is_duplicate(key):
            self.dropped += 1
            return None
        await self.batcher.add(event)
        return event

    async def ingest(self, events):
        """Accept a page of events from the transport."""
        for event in events:
            await self.queue.put(event)
        return len(events)

    async def start(self):
        await self.pool.start()
        self._purger = asyncio.create_task(self._purge_loop())

    async def _purge_loop(self):
        while True:
            await asyncio.sleep(60)
            await self.window.purge()

    async def stop(self):
        """Shut the pipeline down without losing buffered events."""
        await self.pool.stop()
        await self.batcher.close()
        self.queue.close()
        return True

    async def status(self):
        pool = await self.pool.health()
        return {
            "queue": self.queue.stats(),
            "pool": pool,
            "batch_pending": self.batcher.pending(),
            "dedupe_size": self.window.size(),
            "breaker": self.breaker.state,
            "dropped": self.dropped,
        }
