"""Disputes resource."""


class Disputes:
    """Respond to chargebacks and inquiries."""

    def __init__(self, client):
        self.client = client

    def retrieve(self, dispute_id):
        """Fetch a single dispute."""
        return self.client.get("/disputes/%s" % dispute_id)

    def update(self, dispute_id, evidence=None, metadata=None):
        """Attach or replace evidence on a dispute."""
        payload = {"evidence": evidence, "metadata": metadata}
        return self.client.post(
            "/disputes/%s" % dispute_id,
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def close(self, dispute_id):
        """Accept the dispute and stop contesting it."""
        return self.client.post(
            "/disputes/%s/close" % dispute_id,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def list(self, charge_id=None, status=None, limit=100):
        """List disputes, newest first."""
        params = {"charge": charge_id, "status": status, "limit": limit}
        return self.client.get("/disputes", params=params)

    def list_all(self, status=None):
        """Every dispute, across all pages."""
        results = []
        params = {"status": status, "limit": 100}
        while True:
            page = self.client.get("/disputes", params=params)
            results.extend(page.get("data", []))
            if not page.get("has_more"):
                break
        return results

    def list_evidence(self, dispute_id):
        """Evidence already attached to a dispute."""
        return self.client.get("/disputes/%s/evidence" % dispute_id)
