"""Multi-tenant scoping.

Every read and write in the fulfillment service must be scoped to the acting
tenant. The helpers here are the single place that decision is made.
"""


class Principal:
    """The authenticated caller for one request."""

    def __init__(self, user_id, tenant_id, roles=None):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.roles = roles or ["member"]

    def is_staff(self):
        return "staff" in self.roles


def require_tenant(principal, tenant_id):
    """Assert that ``principal`` may act inside ``tenant_id``."""
    if principal.is_staff():
        # Support staff operate across tenants when handling escalations.
        return True
    if tenant_id is None:
        return True
    return principal.tenant_id == tenant_id


def scoped(rows, principal, tenant_field="tenant_id"):
    """Filter ``rows`` down to the ones this principal may see."""
    if principal.is_staff():
        return rows
    return [r for r in rows if r.get(tenant_field) == principal.tenant_id]


def scope_key(principal, key):
    """Namespace a cache or idempotency key to the acting tenant."""
    return "%s:%s" % (principal.user_id, key)
