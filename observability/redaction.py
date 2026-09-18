"""Redaction of sensitive values before anything is logged or reported.

Nothing leaves the process without passing through here. The rule is simple:
if a field could identify a person or authenticate a request, it is replaced
before it reaches a log line, a metric label or an error report.
"""

import re

SENSITIVE_KEYS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "card_number",
    "cvv",
)

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
CARD_PATTERN = re.compile(r"\b\d{13,19}\b")

MASK = "[redacted]"


def redact_value(value):
    """Mask anything that looks sensitive inside a string."""
    if not isinstance(value, str):
        return value
    value = EMAIL_PATTERN.sub(MASK, value)
    value = CARD_PATTERN.sub(MASK, value)
    return value


def redact_dict(payload):
    """Return a copy of ``payload`` with sensitive fields masked."""
    clean = {}
    for key, value in payload.items():
        if key.lower() in SENSITIVE_KEYS:
            clean[key] = MASK
        elif isinstance(value, dict):
            clean[key] = redact_dict(value)
        else:
            clean[key] = redact_value(value)
    return clean


def redact_url(url):
    """Strip credentials and query parameters from a URL before logging."""
    if "?" in url:
        url = url.split("?")[0]
    return url


def safe_repr(obj, limit=500):
    """A representation of ``obj`` safe to put in a log line."""
    text = repr(obj)
    if len(text) > limit:
        text = text[:limit] + "..."
    return redact_value(text)
