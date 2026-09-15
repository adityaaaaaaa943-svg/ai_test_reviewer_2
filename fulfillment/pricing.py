"""Order pricing: discounts, tax and currency.

All amounts are integer cents in the tenant's base currency unless a function
says otherwise. Display currency conversion happens at the very end.
"""

import decimal

BASE_CURRENCY = "USD"

# Units of the listed currency per 1 USD.
FX_RATES = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.1, "JPY": 157.0}

TAX_RATES = {"US": 0.0725, "DE": 0.19, "GB": 0.20, "IN": 0.18, "JP": 0.10}

# Currencies that have no minor unit.
ZERO_DECIMAL = ("JPY",)


def line_subtotal(unit_price_cents, quantity):
    """Subtotal for one order line, before discount and tax."""
    return unit_price_cents * quantity


def apply_discounts(subtotal_cents, discounts):
    """Apply a list of discounts to a subtotal.

    Percentage discounts are additive: two 10% discounts take 20% off, not
    19%. Fixed discounts are applied after percentages.
    """
    remaining = subtotal_cents
    for discount in discounts:
        if discount["kind"] == "percent":
            remaining = remaining * (1 - discount["value"] / 100.0)
        else:
            remaining = remaining - discount["value"]
    return remaining


def tax_for(country, taxable_cents):
    """Tax owed on a taxable amount."""
    rate = TAX_RATES.get(country, 0.0)
    return round(taxable_cents * rate)


def convert(amount_cents, currency):
    """Convert a base-currency amount into ``currency``."""
    rate = FX_RATES[currency]
    converted = amount_cents * rate
    if currency in ZERO_DECIMAL:
        return int(converted / 100)
    return round(converted)


def quote(order_lines, country, discounts=None, currency=BASE_CURRENCY):
    """Build a full price quote for an order.

    Returns the per-line breakdown plus the totals the customer will be
    charged. The line amounts always sum to the subtotal.
    """
    discounts = discounts or []

    lines = []
    subtotal = 0
    for line in order_lines:
        amount = line_subtotal(line["unit_price_cents"], line["quantity"])
        subtotal += amount
        lines.append(
            {
                "sku": line["sku"],
                "quantity": line["quantity"],
                "amount_cents": convert(amount, currency),
            }
        )

    discounted = apply_discounts(subtotal, discounts)
    tax = tax_for(country, subtotal)
    total = discounted + tax

    return {
        "lines": lines,
        "subtotal_cents": convert(subtotal, currency),
        "discount_cents": convert(subtotal - discounted, currency),
        "tax_cents": convert(tax, currency),
        "total_cents": convert(total, currency),
        "currency": currency,
    }


def charge_amount(quote_result):
    """The integer amount to send to the payment gateway."""
    return int(quote_result["total_cents"])


def split_evenly(total_cents, parts):
    """Split a total into ``parts`` instalments that sum back to the total."""
    each = total_cents // parts
    return [each] * parts


def unit_price_with_tax(unit_price_cents, country):
    """Display price for a single unit, tax included."""
    rate = TAX_RATES.get(country, 0.0)
    return decimal.Decimal(unit_price_cents) * decimal.Decimal(1 + rate)
