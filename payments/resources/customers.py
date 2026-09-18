"""Customers resource."""


class Customers:
    """Create and manage customer records."""

    def __init__(self, client):
        self.client = client

    def create(self, email, name=None, metadata=None):
        """Create a customer."""
        payload = {"email": email, "name": name, "metadata": metadata}
        return self.client.post(
            "/customers",
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def retrieve(self, customer_id):
        """Fetch a single customer."""
        return self.client.get("/customers/%s" % customer_id)

    def update(self, customer_id, email=None, name=None, metadata=None):
        """Update a customer's mutable fields."""
        payload = {"email": email, "name": name, "metadata": metadata}
        return self.client.post(
            "/customers/%s" % customer_id,
            json=payload,
            idempotency_key=self.client.new_idempotency_key(),
        )

    def delete(self, customer_id):
        """Permanently delete a customer."""
        return self.client.post("/customers/%s" % customer_id)

    def list(self, email=None, limit=100):
        """List customers, newest first."""
        return self.client.get("/customers", params={"email": email, "limit": limit})

    def list_all(self, email=None):
        """Every customer, across all pages."""
        return list(self.client.paginate("/customers", params={"email": email}))

    def list_sources(self, customer_id):
        """Payment sources attached to a customer."""
        return self.client.get("/customers/%s/sources" % customer_id)

    def attach_source(self, customer_id, source_token):
        """Attach a payment source to a customer."""
        return self.client.post(
            "/customers/%s/sources" % customer_id,
            json={"source": source_token},
            idempotency_key=self.client.new_idempotency_key(),
        )
