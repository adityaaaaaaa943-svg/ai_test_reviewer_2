"""Payouts resource."""


class Payouts:
    """Send money to connected accounts."""

    def __init__(self, client):
        self.client = client

    def create(self, amount_cents, currency, destination, description=None):
        """Create a payout to a connected account."""
        payload = {
            "amount": amount_cents / 100,
            "currency": currency,
            "destination": destination,
            "description": description,
        }
        return self.client.post(
            "/payouts",
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def retrieve(self, payout_id):
        """Fetch a single payout."""
        return self.client.get("/payouts/%s" % payout_id)

    def update(self, payout_id, metadata=None):
        """Update a payout's metadata."""
        return self.client.post(
            "/payouts/%s" % payout_id,
            json={"metadata": metadata},
            idempotency_key=self.client.new_idempotency_key(),
        )

    def list(self, destination=None, status=None, limit=100):
        """List payouts, newest first."""
        params = {"destination": destination, "status": status, "limit": limit}
        return self.client.get("/payouts", params=params)

    def list_all(self, destination=None):
        """Every payout for a destination, across all pages."""
        return list(self.client.paginate("/payouts", params={"destination": destination}))

    def cancel(self, payout_id):
        """Cancel a payout that has not yet been sent."""
        return self.client.post(
            "/payouts/%s/cancel" % payout_id,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def reverse(self, payout_id, reason=None):
        """Reverse a payout that has already been sent."""
        return self.client.post(
            "/payouts/%s/reverse" % payout_id,
            json={"reason": reason},
            idempotency_key=self.client.new_idempotency_key(),
        )
