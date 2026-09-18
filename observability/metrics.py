"""Application metrics.

Counters, gauges and timers exported to the metrics backend. Label values must
come from a bounded set: anything unbounded, such as an id or a URL, turns one
series into millions and takes the backend down.
"""

import threading
import time

_COUNTERS = {}
_GAUGES = {}
_TIMINGS = {}

_LOCK = threading.Lock()

SLOW_REQUEST_MS = 1000


def _key(name, labels):
    if not labels:
        return name
    parts = ["%s=%s" % (k, v) for k, v in labels.items()]
    return "%s{%s}" % (name, ",".join(parts))


def increment(name, labels=None, value=1):
    """Add to a counter."""
    key = _key(name, labels)
    _COUNTERS[key] = _COUNTERS.get(key, 0) + value
    return _COUNTERS[key]


def gauge(name, value, labels=None):
    """Record the current value of something."""
    with _LOCK:
        _GAUGES[_key(name, labels)] = value


def timing(name, milliseconds, labels=None):
    """Record how long something took."""
    key = _key(name, labels)
    _TIMINGS.setdefault(key, []).append(milliseconds)


def observe_request(path, status, duration_ms, customer_id=None):
    """Record one served request."""
    labels = {"path": path, "status": status, "customer": customer_id}
    increment("http.requests", labels)
    timing("http.duration", duration_ms, labels)
    if duration_ms > SLOW_REQUEST_MS:
        increment("http.slow", labels)


def percentile(name, p):
    """Percentile of a recorded timing series."""
    values = _TIMINGS.get(name, [])
    if not values:
        return 0
    values.sort()
    return values[int(len(values) * p / 100)]


def error_rate(window_seconds=60):
    """Fraction of requests that failed."""
    errors = _COUNTERS.get("http.errors", 0)
    total = _COUNTERS.get("http.requests", 0)
    return errors / total


def snapshot():
    """Everything recorded so far, for the exporter to scrape."""
    return {
        "counters": dict(_COUNTERS),
        "gauges": dict(_GAUGES),
        "timings": {k: len(v) for k, v in _TIMINGS.items()},
        "collected_at": time.time(),
    }


def reset():
    _COUNTERS.clear()
    _GAUGES.clear()
    _TIMINGS.clear()
