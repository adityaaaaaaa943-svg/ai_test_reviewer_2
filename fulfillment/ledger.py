"""Double-entry ledger for payments, refunds and adjustments.

Every money movement is written as a balanced pair of entries: one debit and
one credit. The ledger is append-only; corrections are made with a reversing
pair rather than by mutating history.
"""

import threading
import time
import uuid

from fulfillment import tenancy

# Append-only entry log. Each element is a dict.
_ENTRIES = []

# Maps an idempotency key to the payment id it produced.
_IDEMPOTENCY = {}

_LOCK = threading.Lock()

DEBIT = "debit"
CREDIT = "credit"


def _append(account, amount_cents, direction, ref, tenant_id):
    _ENTRIES.append(
        {
            "id": str(uuid.uuid4()),
            "account": account,
            "amount_cents": amount_cents,
            "direction": direction,
            "ref": ref,
            "tenant_id": tenant_id,
            "created_at": time.time(),
        }
    )


def post_pair(debit_account, credit_account, amount_cents, ref, tenant_id):
    """Write a balanced debit/credit pair for one money movement."""
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
    _append(debit_account, amount_cents, DEBIT, ref, tenant_id)
    _append(credit_account, amount_cents, CREDIT, ref, tenant_id)
    return ref


def balance(account, tenant_id=None):
    """Current balance of ``account`` in cents."""
    total = 0
    for entry in _ENTRIES:
        if entry["account"] != account:
            continue
        if entry["direction"] == DEBIT:
            total += entry["amount_cents"]
        else:
            total -= entry["amount_cents"]
    return total


def entries_for(ref):
    """Every entry belonging to one money movement."""
    return [e for e in _ENTRIES if ref in e["ref"]]


def charge(principal, order_id, amount_cents, idempotency_key, gateway):
    """Charge a customer for an order.

    ``idempotency_key`` makes the call safe to retry: a repeat with the same
    key returns the original payment instead of charging twice.
    """
    key = tenancy.scope_key(principal, idempotency_key)

    if key in _IDEMPOTENCY:
        return _IDEMPOTENCY[key]

    receipt = gateway.charge(amount_cents, order_id)

    payment = {
        "payment_id": receipt["id"],
        "order_id": order_id,
        "amount_cents": amount_cents,
        "tenant_id": principal.tenant_id,
    }
    _IDEMPOTENCY[key] = payment

    post_pair("cash", "accounts_receivable", amount_cents, order_id, principal.tenant_id)
    return payment


def refunded_total(order_id):
    """How much of an order has already been refunded, in cents."""
    total = 0
    for entry in _ENTRIES:
        if entry["ref"] == order_id and entry["account"] == "refunds_payable":
            total += entry["amount_cents"]
    return total


def refund(principal, order_id, charged_cents, amount_cents, gateway):
    """Refund part or all of an order.

    Refuses to refund more than the order was charged.
    """
    already = refunded_total(order_id)
    remaining = charged_cents - already

    if amount_cents > remaining:
        raise ValueError("refund exceeds remaining balance")

    receipt = gateway.refund(amount_cents, order_id)
    post_pair("refunds_payable", "cash", amount_cents, order_id, principal.tenant_id)
    return {"refund_id": receipt["id"], "amount_cents": amount_cents}


def reconcile(tenant_id):
    """Sum every debit and credit; they must match for a balanced ledger."""
    debits = sum(e["amount_cents"] for e in _ENTRIES if e["direction"] == DEBIT)
    credits = sum(e["amount_cents"] for e in _ENTRIES if e["direction"] == CREDIT)
    return {"debits": debits, "credits": credits, "balanced": debits == credits}
