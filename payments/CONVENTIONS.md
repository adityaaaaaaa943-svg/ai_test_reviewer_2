# Payments client conventions

A thin wrapper over the Northwind payments API. `client.py` owns
authentication, retries, idempotency and pagination. The modules under
`resources/` are deliberately repetitive: each one is a near-identical set of
create, retrieve, update, list and action methods.

That repetition is the point. Every resource behaves the same way, so a
reader can learn one module and know them all. It also means **a method that
differs from its siblings is either a deliberate exception or a bug**, and
there are no deliberate exceptions in this pull request.

## Rules

1. **Reads use GET, writes use POST, deletions use DELETE.** No state-changing
   operation is ever issued as a GET.
2. **Every write carries a fresh idempotency key** from
   `client.new_idempotency_key()`. Keys are never shared between calls or
   between operations.
3. **Money is integer minor units.** Amounts are passed through untouched; the
   client never divides or converts them.
4. **A path parameter interpolates the identifier named in the path.** A
   refund path takes a refund id.
5. **Errors propagate.** Resource methods never catch an exception to return
   `None`. The caller decides what a failure means.
6. **List-all methods delegate to `client.paginate`.** Hand-rolled pagination
   loops are not permitted, because they are where cursor bugs live.
7. **Query parameters go in `params`, bodies go in `json`.** Neither is built
   by string concatenation onto the path.
8. **Every method inherits the client timeout.** No method sets its own.

## Layout

| Path | Resource |
| --- | --- |
| `client.py` | Transport, auth, retries, pagination |
| `resources/charges.py` | Charges |
| `resources/refunds.py` | Refunds |
| `resources/customers.py` | Customers and sources |
| `resources/payouts.py` | Payouts to connected accounts |
| `resources/disputes.py` | Chargebacks and evidence |
| `resources/invoices.py` | Invoices and subscriptions |

## Known gaps

Webhook signature verification lands in a follow-up. There is no sandbox
fixture set yet, so these wrappers are reviewed rather than exercised.
