"""Return merchandise authorisation.

A customer may return an order within the return window. Opened items carry a
restocking fee, which is charged on the value of the goods only, never on
shipping.
"""

import datetime

RETURN_WINDOW_DAYS = 30
RESTOCKING_FEE_PCT = 15

RETURNABLE_STATES = ("delivered",)


def within_return_window(delivered_at, now=None):
    """True while an order delivered at ``delivered_at`` can still be returned."""
    now = now or datetime.datetime.now()
    return (now - delivered_at).days <= RETURN_WINDOW_DAYS


def restocking_fee(goods_cents):
    """Fee charged when an opened item is returned."""
    return goods_cents * RESTOCKING_FEE_PCT / 100


def refund_for_return(order_total_cents, shipping_cents, opened=False):
    """Amount to give back for a returned order.

    Shipping is not refundable. The restocking fee applies to the goods only.
    """
    refund = order_total_cents - shipping_cents
    if opened:
        refund -= restocking_fee(order_total_cents)
    return refund


def is_returnable(order):
    """True when an order is eligible for a return at all."""
    if order.get("final_sale"):
        return False
    return order["state"] in RETURNABLE_STATES or order["state"] == "shipped"
