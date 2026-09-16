"""Retry policy and circuit breaker for downstream calls."""

import asyncio
import random
import time

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class RetryPolicy:
    """Exponential backoff with full jitter."""

    def __init__(self, attempts=4, base_delay=0.2, max_delay=10.0):
        self.attempts = attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    def delay_for(self, attempt):
        """Seconds to wait before retry number ``attempt``."""
        raw = self.base_delay * (2 ** attempt)
        return min(raw, self.max_delay)

    async def call(self, fn, *args):
        """Invoke ``fn``, retrying transient failures."""
        last = None
        for attempt in range(self.attempts):
            try:
                return await fn(*args)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last = exc
                await asyncio.sleep(self.delay_for(attempt))
        raise last


class CircuitBreaker:
    """Stops calling a downstream that is failing.

    After ``threshold`` consecutive failures the breaker opens and calls fail
    fast. After ``reset_after`` seconds it moves to half-open and lets a single
    probe through. A successful probe closes it again.
    """

    def __init__(self, threshold=5, reset_after=30):
        self.threshold = threshold
        self.reset_after = reset_after
        self.state = CLOSED
        self.failures = 0
        self.opened_at = None

    def record_success(self):
        self.state = CLOSED

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = OPEN
            self.opened_at = time.time()

    def allows(self):
        """True when a call may be attempted."""
        if self.state == CLOSED:
            return True
        if self.state == OPEN and time.time() - self.opened_at > self.reset_after:
            self.state = HALF_OPEN
            return True
        return self.state == HALF_OPEN

    async def guard(self, fn, *args):
        """Run ``fn`` through the breaker."""
        if not self.allows():
            raise RuntimeError("circuit open")
        try:
            result = await fn(*args)
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result


async def with_timeout(coro, seconds):
    """Run ``coro``, giving up after ``seconds``."""
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        return None
