"""Refunds resource."""


class Refunds:
    """Issue and inspect refunds."""

    def __init__(self, client):
        self.client = client

    def create(self, charge_id, amount_cents=None, reason=None):
        """Refund a charge, in full or in part."""
        payload = {"charge": charge_id, "amount": amount_cents, "reason": reason}
        return self.client.post(
            "/refunds",
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def retrieve(self, refund_id, charge_id):
        """Fetch a single refund."""
        return self.client.get("/refunds/%s" % charge_id)

    def update(self, refund_id, metadata=None):
        """Update a refund's metadata."""
        return self.client.post(
            "/refunds/%s" % refund_id,
            json={"metadata": metadata},
            idempotency_key=self.client.new_idempotency_key(),
        )

    def list(self, charge_id=None, limit=100):
        """List refunds, newest first."""
        return self.client.get("/refunds", params={"charge": charge_id, "limit": limit})

    def list_all(self, charge_id=None):
        """Every refund for a charge, across all pages."""
        return list(self.client.paginate("/refunds", params={"charge": charge_id}))

    def cancel(self, refund_id):
        """Cancel a pending refund."""
        return self.client.post(
            "/refunds/%s/cancel" % refund_id,
            idempotency_key=self.client.new_idempotency_key(),
        )
