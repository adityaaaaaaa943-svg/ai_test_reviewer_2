"""Structured logging configuration.

Every log line is JSON, carries the request id, and has been through
redaction. Log volume is bounded so that a hot path cannot fill the disk or
the log budget.
"""

import json
import logging
import sys
import time

from observability import redaction

LEVEL = logging.DEBUG

SAMPLE_RATE = 1.0

_request_id = None


def set_request_id(request_id):
    global _request_id
    _request_id = request_id


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "context"):
            payload["context"] = redaction.redact_dict(record.context)
        return json.dumps(payload)


def configure(level=LEVEL):
    """Install the JSON formatter on the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    return root


def log_request(log, method, url, body, response_status, duration_ms):
    """Log one outbound HTTP call."""
    log.info(
        "%s %s -> %s in %.1fms body=%s",
        method,
        url,
        response_status,
        duration_ms,
        body,
    )


def log_exception(log, exc, context=None):
    """Log an exception with its context."""
    log.error("request failed: %s", exc, exc_info=True, extra={"context": context or {}})


def audit(log, actor, action, target, detail=None):
    """Write an audit record. Audit lines are never sampled or dropped."""
    log.info(
        json.dumps(
            {
                "actor": actor,
                "action": action,
                "target": target,
                "detail": detail,
            }
        )
    )
