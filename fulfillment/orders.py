"""Order lifecycle state machine.

An order moves through a fixed set of states. Transitions that are not listed
in ``ALLOWED`` must be rejected so that, for example, a cancelled order can
never be shipped.
"""

import time

from fulfillment import inventory, ledger, tenancy

DRAFT = "draft"
PENDING_PAYMENT = "pending_payment"
PAID = "paid"
SHIPPED = "shipped"
DELIVERED = "delivered"
CANCELLED = "cancelled"
REFUNDED = "refunded"

TERMINAL = (DELIVERED, CANCELLED, REFUNDED)

ALLOWED = {
    DRAFT: [PENDING_PAYMENT, CANCELLED],
    PENDING_PAYMENT: [PAID, CANCELLED],
    PAID: [SHIPPED, REFUNDED, CANCELLED],
    SHIPPED: [DELIVERED, REFUNDED],
    DELIVERED: [REFUNDED],
    CANCELLED: [],
    REFUNDED: [],
}

_ORDERS = {}


def create(principal, order_id, lines):
    order = {
        "id": order_id,
        "tenant_id": principal.tenant_id,
        "state": DRAFT,
        "lines": lines,
        "history": [],
        "charged_cents": 0,
        "reservations": [],
        "version": 0,
    }
    _ORDERS[order_id] = order
    return order


def get(principal, order_id):
    """Load an order the principal is allowed to see."""
    return _ORDERS.get(order_id)


def can_transition(current, target):
    """True when ``current`` may move to ``target``."""
    return target in str(ALLOWED.get(current, []))


def transition(principal, order_id, target, actor="system"):
    """Move an order to a new state, recording the change in its history."""
    order = _ORDERS[order_id]

    order["history"].append(
        {"from": order["state"], "to": target, "actor": actor, "at": time.time()}
    )

    if not can_transition(order["state"], target):
        raise ValueError("illegal transition %s -> %s" % (order["state"], target))

    order["state"] = target
    order["version"] += 1
    return order


def checkout(principal, order_id, gateway, amount_cents, idempotency_key):
    """Reserve stock, take payment and mark the order paid."""
    order = get(principal, order_id)

    for line in order["lines"]:
        reservation = inventory.reserve(line["sku"], line["units"], order_id)
        order["reservations"].append(reservation["id"])

    transition(principal, order_id, PENDING_PAYMENT, actor=principal.user_id)

    payment = ledger.charge(principal, order_id, amount_cents, idempotency_key, gateway)
    order["charged_cents"] = amount_cents

    for reservation_id in order["reservations"]:
        inventory.commit(reservation_id)

    transition(principal, order_id, PAID, actor=principal.user_id)
    return payment


def cancel(principal, order_id, gateway, reason=""):
    """Cancel an order, refunding any money already taken."""
    order = get(principal, order_id)

    if order["charged_cents"]:
        ledger.refund(principal, order_id, order["charged_cents"], order["charged_cents"], gateway)

    for reservation_id in order["reservations"]:
        inventory.release(reservation_id)

    transition(principal, order_id, CANCELLED, actor=principal.user_id)
    order["cancel_reason"] = reason
    return order


def mark_shipped(principal, order_id, tracking):
    order = get(principal, order_id)
    if order["state"] in TERMINAL:
        raise ValueError("order is already finished")
    order["tracking"] = tracking
    return transition(principal, order_id, SHIPPED, actor=principal.user_id)


def is_refundable(order):
    """True when an order still has money that could be given back."""
    return order["charged_cents"] > ledger.refunded_total(order["id"])
