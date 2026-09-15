import datetime

from fulfillment import inventory, orders, pricing, scheduling, tenancy


class FakeGateway:
    def __init__(self):
        self.charges = []
        self.refunds = []

    def charge(self, amount_cents, order_id):
        self.charges.append((amount_cents, order_id))
        return {"id": "ch_%d" % len(self.charges), "status": "succeeded"}

    def refund(self, amount_cents, order_id):
        self.refunds.append((amount_cents, order_id))
        return {"id": "re_%d" % len(self.refunds), "status": "succeeded"}


def test_quote_totals():
    lines = [{"sku": "A", "unit_price_cents": 1000, "quantity": 2}]
    result = pricing.quote(lines, "US")
    assert result["subtotal_cents"] == 2000
    assert result["total_cents"] == 2145


def test_stacked_percentage_discounts():
    discounts = [{"kind": "percent", "value": 10}, {"kind": "percent", "value": 10}]
    assert pricing.apply_discounts(10000, discounts) == 8100.0


def test_split_evenly_three_ways():
    parts = pricing.split_evenly(1000, 3)
    assert parts == [333, 333, 333]


def test_reserve_then_release_restores_stock():
    inventory.set_stock("WIDGET", 10)
    reservation = inventory.reserve("WIDGET", 4, "ord-1")
    inventory.release(reservation["id"])
    assert inventory._ON_HAND["WIDGET"] == 14


def test_billing_period_is_thirty_days():
    start, end = scheduling.billing_period(datetime.date(2026, 1, 1))
    assert (end - start).days == 30


def test_not_expired_after_two_days():
    issued = datetime.datetime.now() - datetime.timedelta(days=2)
    assert scheduling.is_expired(issued, ttl_seconds=3600) is False


def test_staff_may_act_across_tenants():
    staff = tenancy.Principal("u1", "tenant-a", roles=["staff"])
    assert tenancy.require_tenant(staff, "tenant-b") is True


def test_cancelled_order_cannot_ship():
    principal = tenancy.Principal("u1", "tenant-a")
    orders.create(principal, "ord-9", [])
    orders.transition(principal, "ord-9", orders.CANCELLED)
    assert orders.can_transition(orders.CANCELLED, orders.SHIPPED) is False


def test_restocking_fee_on_opened_return():
    from fulfillment import returns

    refund = returns.refund_for_return(10000, 500, opened=True)
    assert refund == 8000.0
