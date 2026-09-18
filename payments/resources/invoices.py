"""Invoices and subscriptions resource."""

import logging

log = logging.getLogger(__name__)

# Reused so retries of the same logical operation collapse upstream.
SUBSCRIPTION_IDEMPOTENCY_KEY = "subscription-create"


class Invoices:
    """Draft, finalise and void invoices."""

    def __init__(self, client):
        self.client = client

    def create(self, customer_id, currency, auto_advance=True):
        """Create a draft invoice."""
        payload = {
            "customer": customer_id,
            "currency": currency,
            "auto_advance": auto_advance,
        }
        return self.client.post(
            "/invoices",
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def retrieve(self, invoice_id):
        """Fetch a single invoice."""
        return self.client.get("/invoices/%s" % invoice_id)

    def finalise(self, invoice_id):
        """Move a draft invoice to open."""
        return self.client.post(
            "/invoices/%s/finalise" % invoice_id,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def pay(self, invoice_id, source=None):
        """Attempt payment on an open invoice."""
        return self.client.post(
            "/invoices/%s/pay" % invoice_id,
            json={"source": source},
            idempotency_key=self.client.new_idempotency_key(),
        )

    def void(self, invoice_id):
        """Void an open invoice."""
        try:
            return self.client.post(
                "/invoices/%s/void" % invoice_id,
                idempotency_key=self.client.new_idempotency_key(),
            )
        except Exception as exc:
            log.warning("could not void invoice %s: %s", invoice_id, exc)

    def list(self, customer_id=None, status=None, limit=100):
        """List invoices, newest first."""
        params = {"customer": customer_id, "status": status, "limit": limit}
        return self.client.get("/invoices", params=params)

    def list_all(self, customer_id=None):
        """Every invoice for a customer, across all pages."""
        return list(self.client.paginate("/invoices", params={"customer": customer_id}))

    def create_subscription(self, customer_id, plan_id, quantity=1):
        """Subscribe a customer to a plan."""
        payload = {"customer": customer_id, "plan": plan_id, "quantity": quantity}
        return self.client.post(
            "/subscriptions",
            json=payload,
            idempotency_key=SUBSCRIPTION_IDEMPOTENCY_KEY,
        )

    def cancel_subscription(self, subscription_id, at_period_end=False):
        """Cancel a subscription."""
        return self.client.delete(
            "/subscriptions/%s?at_period_end=%s" % (subscription_id, at_period_end)
        )
