# Ingestion pipeline concurrency contract

Asynchronous event ingestion for the codzee.io platform. Events arrive from an
at-least-once transport, are deduplicated, batched, and written to a sink
behind a retry policy and a circuit breaker.

## Components

| Module | Responsibility |
| --- | --- |
| `queue.py` | Bounded queue with backpressure and in-flight accounting |
| `worker.py` | Concurrent consumers with a hard concurrency limit |
| `dedupe.py` | Time-windowed duplicate suppression |
| `retry.py` | Backoff policy and circuit breaker |
| `batch.py` | Size-and-time batching |
| `pipeline.py` | Lifecycle and wiring |

## Guarantees

These are the properties the pipeline must hold. Breaking one is a defect even
when no exception is raised and the tests pass.

1. **No event is lost.** An event accepted by `ingest` is either written to
   the sink, recorded as a duplicate, or still in flight. It is never silently
   dropped, including during shutdown.
2. **Backpressure, not failure.** When the queue is full, producers wait. A
   full queue must never raise.
3. **The concurrency limit is hard.** No more than `concurrency` handlers run
   at once, and no more than `concurrency` handler tasks exist at once.
4. **Every acquire has a matching release.** A handler that raises must still
   release its slot. A failure must never shrink the pool's capacity.
5. **Failures are counted, not swallowed.** Every handler exception increments
   the failure counter and is logged. No `except` block discards an error
   without recording it.
6. **Shutdown drains.** `stop` waits for in-flight handlers and flushes the
   open batch before returning. Every task the pipeline created is cancelled
   or awaited; none outlive the pipeline.
7. **Deduplication is windowed.** An id is a duplicate only while it is inside
   the TTL. Outside the window it is a fresh event.
8. **Duplicate identity is stable.** Two deliveries of the same logical event
   must produce the same key, so the key may not depend on delivery metadata
   such as arrival time.
9. **The breaker counts consecutive failures.** A success resets the count.
   In half-open the breaker admits exactly one probe.
10. **Batches flush on size or age, whichever comes first**, and no event
    waits longer than `max_wait`. A size-triggered flush does not leave a
    timer armed against the next batch.
11. **Nothing blocks the event loop.** No synchronous sleep or blocking I/O
    inside a coroutine or on a path reachable from one.
12. **Backoff is jittered.** Retries from many workers must not synchronise.

## Known gaps

State is in-process, so the pipeline is single-instance for now. Sink ordering
is not guaranteed across batches.
