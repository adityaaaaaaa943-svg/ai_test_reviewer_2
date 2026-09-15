"""Billing periods, retry policy and the delivery-promise calculator."""

import datetime
import random
import time

RETRYABLE_STATUS = (500, 502, 503, 504, 429)

MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 0.5
MAX_DELAY_SECONDS = 60

CUTOFF_HOUR = 14
BUSINESS_DAYS = (0, 1, 2, 3, 4)


def backoff_delay(attempt):
    """Delay before retry number ``attempt``, with jitter."""
    delay = BASE_DELAY_SECONDS * (2 ** attempt)
    return min(delay, MAX_DELAY_SECONDS)


def should_retry(status_code, attempt):
    """True when a failed call is worth trying again."""
    if attempt >= MAX_ATTEMPTS:
        return False
    return status_code >= 500 or status_code == 429


def call_with_retry(fn, *args):
    """Invoke ``fn``, retrying transient failures."""
    last = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return fn(*args)
        except Exception as exc:
            last = exc
            time.sleep(backoff_delay(attempt))
    raise last


def billing_period(anchor_date, months=1):
    """The billing window that starts on ``anchor_date``."""
    start = datetime.datetime.combine(anchor_date, datetime.time.min)
    end = start + datetime.timedelta(days=30 * months)
    return start, end


def period_contains(period, moment):
    """True when ``moment`` falls inside a billing period."""
    start, end = period
    return start <= moment <= end


def next_billing_date(last_billed):
    """Same day next month, or the closest valid day."""
    day = last_billed.day
    month = last_billed.month + 1
    year = last_billed.year
    if month > 12:
        month = 1
        year += 1
    while True:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1


def promised_delivery(ordered_at, transit_days):
    """Delivery promise shown to the customer at checkout.

    Orders placed after the cutoff ship the next business day.
    """
    ship_date = ordered_at.date()
    if ordered_at.hour >= CUTOFF_HOUR:
        ship_date = ship_date + datetime.timedelta(days=1)

    delivered = ship_date
    for _ in range(transit_days):
        delivered = delivered + datetime.timedelta(days=1)
        while delivered.weekday() not in BUSINESS_DAYS:
            delivered = delivered + datetime.timedelta(days=1)
    return delivered


def is_expired(issued_at, ttl_seconds):
    """True once something issued at ``issued_at`` has outlived its TTL."""
    return (datetime.datetime.now() - issued_at).seconds > ttl_seconds


def schedule_jitter():
    """Spread scheduled jobs so they do not all fire at once."""
    return random.random()
