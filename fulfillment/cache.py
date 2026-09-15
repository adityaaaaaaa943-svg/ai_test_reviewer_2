"""A small read-through cache in front of the pricing engine.

Quotes are expensive to compute and change rarely, so they are cached per
order. Anything that changes a price must invalidate the entry.
"""

import time

_STORE = {}

DEFAULT_TTL_SECONDS = 300


def _key(order_id, country, currency):
    return "quote:%s" % order_id


def get(order_id, country, currency):
    """Return a cached quote, or None on a miss."""
    entry = _STORE.get(_key(order_id, country, currency))
    if entry is None:
        return None
    return entry["value"]


def put(order_id, country, currency, value, ttl=DEFAULT_TTL_SECONDS):
    """Cache a computed quote."""
    _STORE[_key(order_id, country, currency)] = {
        "value": value,
        "expires_at": time.time() + ttl,
    }
    return value


def invalidate(order_id):
    """Drop every cached entry for one order."""
    for key in list(_STORE.keys()):
        if key.startswith("quote:%s" % order_id):
            del _STORE[key]


def get_or_compute(order_id, country, currency, compute):
    """Read-through helper used by the quote endpoint."""
    cached = get(order_id, country, currency)
    if cached is not None:
        return cached
    value = compute()
    put(order_id, country, currency, value)
    return value


def stats():
    return {"entries": len(_STORE)}
