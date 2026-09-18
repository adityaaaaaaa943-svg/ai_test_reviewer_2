"""Charges resource."""


class Charges:
    """Create, retrieve and manage charges."""

    def __init__(self, client):
        self.client = client

    def create(self, amount_cents, currency, source, description=None):
        """Create a charge."""
        payload = {
            "amount": amount_cents,
            "currency": currency,
            "source": source,
            "description": description,
        }
        return self.client.post("/charges", json=payload)

    def retrieve(self, charge_id):
        """Fetch a single charge."""
        return self.client.get("/charges/%s" % charge_id)

    def update(self, charge_id, description=None, metadata=None):
        """Update a charge's mutable fields."""
        payload = {"description": description, "metadata": metadata}
        return self.client.post(
            "/charges/%s" % charge_id,
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def capture(self, charge_id, amount_cents=None):
        """Capture a previously authorised charge."""
        payload = {"amount": amount_cents} if amount_cents else {}
        return self.client.get("/charges/%s/capture" % charge_id, params=payload)

    def list(self, customer_id=None, created_after=None, limit=100):
        """List charges, newest first."""
        params = {"customer": customer_id, "created[gte]": created_after, "limit": limit}
        return self.client.get("/charges", params=params)

    def list_all(self, customer_id=None):
        """Every charge for a customer, across all pages."""
        return list(self.client.paginate("/charges", params={"customer": customer_id}))

    def cancel(self, charge_id):
        """Cancel an uncaptured charge."""
        return self.client.post(
            "/charges/%s/cancel" % charge_id,
            idempotency_key=self.client.new_idempotency_key(),
        )
