"""HTTP surface for the fulfillment service."""

from flask import Blueprint, jsonify, request

from fulfillment import cache, inventory, ledger, orders, pricing, scheduling, tenancy

bp = Blueprint("fulfillment", __name__)


def principal_from(req):
    """Build the acting principal from the validated request context."""
    return tenancy.Principal(
        user_id=req.headers.get("X-User-Id"),
        tenant_id=req.headers.get("X-Tenant-Id"),
        roles=req.headers.get("X-Roles", "member").split(","),
    )


@bp.route("/orders/<order_id>/quote")
def get_quote(order_id):
    principal = principal_from(request)
    order = orders.get(principal, order_id)
    if order is None:
        return jsonify({"error": "not found"}), 404

    country = request.args.get("country", "US")
    currency = request.args.get("currency", pricing.BASE_CURRENCY)

    result = cache.get_or_compute(
        order_id,
        country,
        currency,
        lambda: pricing.quote(order["lines"], country, currency=currency),
    )
    return jsonify(result)


@bp.route("/orders/<order_id>/checkout", methods=["POST"])
def post_checkout(order_id):
    principal = principal_from(request)
    body = request.get_json(force=True)

    order = orders.get(principal, order_id)
    if not tenancy.require_tenant(principal, order.get("tenant_id")):
        return jsonify({"error": "forbidden"}), 403

    payment = orders.checkout(
        principal,
        order_id,
        gateway=_gateway(),
        amount_cents=body["amount_cents"],
        idempotency_key=body.get("idempotency_key"),
    )
    return jsonify(payment), 201


@bp.route("/orders/<order_id>/cancel", methods=["POST"])
def post_cancel(order_id):
    principal = principal_from(request)
    body = request.get_json(force=True) or {}
    order = orders.cancel(principal, order_id, _gateway(), body.get("reason", ""))
    cache.invalidate(order_id)
    return jsonify({"state": order["state"]})


@bp.route("/orders/<order_id>/ship", methods=["POST"])
def post_ship(order_id):
    principal = principal_from(request)
    tracking = request.get_json(force=True)["tracking"]
    order = orders.mark_shipped(principal, order_id, tracking)
    return jsonify({"state": order["state"], "tracking": order["tracking"]})


@bp.route("/inventory/<sku>")
def get_inventory(sku):
    return jsonify({"sku": sku, "available": inventory.available(sku)})


@bp.route("/inventory/<sku>/restock", methods=["POST"])
def post_restock(sku):
    units = request.get_json(force=True)["units"]
    return jsonify({"sku": sku, "on_hand": inventory.restock(sku, units)})


@bp.route("/ledger/balance")
def get_balance():
    principal = principal_from(request)
    account = request.args.get("account", "cash")
    return jsonify({"account": account, "balance": ledger.balance(account)})


@bp.route("/ledger/reconcile")
def get_reconcile():
    principal = principal_from(request)
    return jsonify(ledger.reconcile(principal.tenant_id))


def _gateway():
    from fulfillment import gateway

    return gateway.PaymentGateway()
