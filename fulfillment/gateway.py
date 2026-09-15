"""Payment gateway client."""

import uuid

from fulfillment import scheduling


class PaymentGateway:
    """Thin wrapper over the upstream payments API."""

    def __init__(self, session=None):
        self.session = session

    def _post(self, path, payload):
        if self.session is None:
            return {"id": str(uuid.uuid4()), "status": "succeeded"}
        response = self.session.post(path, json=payload, timeout=5)
        return response.json()

    def charge(self, amount_cents, order_id):
        """Charge a customer. Retried automatically on transient failure."""
        return scheduling.call_with_retry(
            self._post, "/v1/charges", {"amount": amount_cents, "order": order_id}
        )

    def refund(self, amount_cents, order_id):
        return scheduling.call_with_retry(
            self._post, "/v1/refunds", {"amount": amount_cents, "order": order_id}
        )
