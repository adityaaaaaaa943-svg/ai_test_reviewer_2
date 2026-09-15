# Fulfillment service

Order lifecycle, payments ledger and inventory reservation for the codzee.io
storefront.

## Modules

| Module | Responsibility |
| --- | --- |
| `tenancy.py` | Decides who may read or write what. Every other module depends on it. |
| `ledger.py` | Append-only double-entry record of all money movement. |
| `inventory.py` | Physical stock and short-lived checkout reservations. |
| `orders.py` | The order lifecycle state machine. |
| `pricing.py` | Discounts, tax and display-currency conversion. |
| `scheduling.py` | Billing periods, retry policy, delivery promises. |
| `cache.py` | Read-through cache in front of the pricing engine. |
| `gateway.py` | Client for the upstream payments API. |
| `api.py` | HTTP surface. |

## Invariants

These are the properties the service is supposed to guarantee. A change that
breaks one of them is a bug regardless of whether a test catches it.

1. **Tenant isolation.** No request may read or write data belonging to a
   tenant other than the caller's own.
2. **The ledger balances.** Total debits equal total credits at all times.
3. **Charges are idempotent.** Retrying a checkout with the same idempotency
   key charges the customer exactly once, and two different orders never
   share an idempotency record.
4. **Stock is conserved.** Units are neither created nor destroyed by
   reserving, releasing, committing or expiring a reservation. Only
   `restock` and `commit` change the physical count.
5. **No overselling.** Concurrent reservations may never take the available
   count below zero.
6. **The state machine is authoritative.** An order only moves along a
   transition listed in `ALLOWED`, and no side effect is applied for a
   transition that is rejected.
7. **The customer is charged what the quote said.** The amount sent to the
   gateway is derived from the pricing engine, never from client input.
8. **Refunds never exceed the charge.** The sum of refunds for an order is
   always less than or equal to the amount charged.
9. **Money is exact.** Amounts are integer cents. Rounding happens once, at
   the presentation boundary, and displayed line amounts reconcile with the
   displayed total.
10. **Billing periods tile the timeline.** Consecutive periods neither
    overlap nor leave gaps, so no instant is billed twice or missed.

## Known gaps

State is held in module-level dicts pending the Postgres migration, so the
service is currently single-process only.
