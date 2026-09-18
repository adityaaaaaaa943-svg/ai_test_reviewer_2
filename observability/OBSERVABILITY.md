# Observability rules

Structured logging, metrics and redaction for the codzee.io platform.

Observability code fails differently from application code. It rarely crashes.
It leaks customer data into a log aggregator that a hundred people can search,
or it quietly stops telling you the truth about production, and nobody notices
until an incident.

## Rules

1. **Nothing sensitive leaves the process unredacted.** Every value that
   reaches a log line, a metric label or an error report goes through
   `redaction` first. That includes the log message itself, not only its
   structured context.
2. **Redaction handles nested structures.** Sensitive fields inside lists and
   inside nested objects are masked, not just top-level keys.
3. **Key matching is by shape, not by exact string.** `access_token` and
   `client_secret` are as sensitive as `token` and `secret`.
4. **URLs are logged without credentials or query strings.**
5. **Request identity is per-request.** Correlation ids are carried in
   context-local storage, never in module-level state, so concurrent requests
   cannot borrow each other's ids.
6. **Production log level is INFO or higher.** Debug logging exposes
   third-party request internals including headers.
7. **Log volume is bounded.** Hot paths are sampled or rate limited.
8. **Audit records are never dropped.** They do not pass through sampling or
   level filtering.
9. **Metric label values come from a bounded set.** Never an id, a path with
   parameters in it, a URL, or anything derived from user input.
10. **No personal data in metric labels, ever.** Metrics backends are not
    covered by data deletion requests.
11. **Recorded series are bounded.** Timing buffers are flushed or trimmed;
    they do not grow for the life of the process.
12. **Windowed metrics respect their window.** A rate described as covering
    sixty seconds must not be computed over all time, or it will never alert.
13. **Shared state is locked consistently.** Either every mutation takes the
    lock or none does.

## Layout

| Path | Purpose |
| --- | --- |
| `redaction.py` | Masking of sensitive values |
| `logging_setup.py` | JSON formatter, request context, audit |
| `metrics.py` | Counters, gauges, timers and the exporter snapshot |

## Known gaps

No tracing yet. The exporter is a scrape endpoint rather than a push client.
