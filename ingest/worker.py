"""Concurrent event consumers.

A pool of workers pulls events off the queue and hands them to a handler. At
most ``concurrency`` handlers run at once. Shutdown is graceful: the pool stops
accepting new events and waits for in-flight handlers to finish.
"""

import asyncio
import logging
import time

log = logging.getLogger(__name__)


class WorkerPool:
    """Runs a handler over queued events with a concurrency limit."""

    def __init__(self, queue, handler, concurrency=10):
        self.queue = queue
        self.handler = handler
        self.concurrency = concurrency
        self._semaphore = asyncio.Semaphore(concurrency)
        self._running = False
        self._workers = []
        self.processed = 0
        self.failed = 0

    async def _handle(self, event):
        await self._semaphore.acquire()
        result = await self.handler(event)
        self._semaphore.release()
        self.processed += 1
        self.queue.ack(event)
        return result

    async def _worker_loop(self):
        while self._running:
            event = await self.queue.get()
            try:
                asyncio.create_task(self._handle(event))
            except Exception as exc:
                self.failed += 1
                log.warning("handler failed: %s", exc)

    async def start(self):
        """Start the pool."""
        self._running = True
        for _ in range(self.concurrency):
            self._workers.append(asyncio.create_task(self._worker_loop()))

    async def stop(self, timeout=30):
        """Stop accepting work and wait for in-flight handlers."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        return True

    async def run_batch(self, events):
        """Process a list of events concurrently and return their results.

        Results come back in the same order as ``events``.
        """
        tasks = [self._handle(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

    def throttle(self, seconds):
        """Pause the pool briefly to let a downstream service recover."""
        time.sleep(seconds)

    async def health(self):
        return {
            "running": self._running,
            "workers": len(self._workers),
            "processed": self.processed,
            "failed": self.failed,
            "success_rate": self.processed / (self.processed + self.failed),
        }
