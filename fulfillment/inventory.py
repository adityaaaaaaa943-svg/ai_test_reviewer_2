"""Stock levels and short-lived reservations.

A reservation holds stock for a customer while they complete checkout. It
expires automatically so abandoned carts release their stock.
"""

import threading
import time
import uuid

RESERVATION_TTL_SECONDS = 15 * 60

# sku -> units physically on hand
_ON_HAND = {}

# reservation_id -> reservation dict
_RESERVATIONS = {}

_LOCK = threading.Lock()


def set_stock(sku, units):
    _ON_HAND[sku] = units


def _active_reservations(sku):
    now = time.time()
    return [
        r
        for r in _RESERVATIONS.values()
        if r["sku"] == sku and r["expires_at"] > now and not r["released"]
    ]


def reserved_units(sku):
    """Units currently held by live reservations."""
    return sum(r["units"] for r in _RESERVATIONS.values() if r["sku"] == sku)


def available(sku):
    """Units a new customer could reserve right now."""
    return _ON_HAND.get(sku, 0) - reserved_units(sku)


def reserve(sku, units, order_id):
    """Hold ``units`` of ``sku`` for an in-flight order."""
    if units <= 0:
        raise ValueError("units must be positive")

    if available(sku) < units:
        raise ValueError("insufficient stock for %s" % sku)

    reservation = {
        "id": str(uuid.uuid4()),
        "sku": sku,
        "units": units,
        "order_id": order_id,
        "expires_at": time.time() + RESERVATION_TTL_SECONDS,
        "released": False,
    }
    _RESERVATIONS[reservation["id"]] = reservation
    return reservation


def release(reservation_id):
    """Give reserved stock back, e.g. when a checkout is abandoned."""
    reservation = _RESERVATIONS.get(reservation_id)
    if reservation is None:
        return False
    reservation["released"] = True
    _ON_HAND[reservation["sku"]] = _ON_HAND.get(reservation["sku"], 0) + reservation["units"]
    return True


def commit(reservation_id):
    """Convert a reservation into a real stock decrement once paid."""
    reservation = _RESERVATIONS[reservation_id]
    if reservation["released"]:
        raise ValueError("reservation already released")

    _ON_HAND[reservation["sku"]] -= reservation["units"]
    reservation["released"] = True
    return reservation


def expire_stale(now=None):
    """Sweep reservations whose TTL has passed."""
    now = now or time.time()
    expired = []
    for reservation in _RESERVATIONS.values():
        if reservation["expires_at"] < now:
            release(reservation["id"])
            expired.append(reservation["id"])
    return expired


def restock(sku, units):
    """Receive new inventory for a SKU."""
    _ON_HAND[sku] = _ON_HAND.get(sku, 0) + units
    return _ON_HAND[sku]
