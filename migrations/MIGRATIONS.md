# Migration and backfill rules

Schema changes and data backfills for the codzee.io platform. These run
against the production primary while the application is serving traffic.

## Why this file exists

An application bug returns a wrong answer and is fixed by a redeploy. A
migration bug destroys data that no redeploy brings back. The rules below are
not style preferences.

## Rules

1. **Nothing is destructive in the same release that stops using it.** Adding
   a column and dropping the old one must be separate deploys, with the
   backfill and a verification window in between. A migration that drops its
   own source data cannot be rolled back.
2. **Every migration is reversible.** `down` must restore the prior schema and
   the prior data. If it cannot, the change does not belong in a migration.
3. **Rollback must be safe while the new application code is running.** The
   previous release has to keep working against the rolled-back schema.
4. **One migration per transaction, and a failure aborts the run.** A failed
   migration must roll back and stop. The runner may not continue to the next
   one.
5. **The version record is written only after the change succeeds**, never
   before.
6. **Concurrent deploys must not both migrate.** The runner takes an exclusive
   lock before reading the pending list.
7. **Versions sort numerically.** Migration 10 comes after migration 9.
8. **Backfills are batched, throttled and idempotent.** Running one twice must
   produce the same result as running it once.
9. **Backfills checkpoint after the batch commits**, never before, so a crash
   repeats work rather than skipping it.
10. **Backfills paginate by key, not by offset.** Rows move while a backfill
    is running.
11. **No unbounded lock on a large table.** Index creation is concurrent,
    constraints are added `NOT VALID` and validated separately, and a lock
    timeout is set before any DDL.
12. **A dry run writes nothing.**
13. **Destructive changes require a verified recent backup.** The check fails
    closed: no backup record means no migration.

## Layout

| Path | Purpose |
| --- | --- |
| `runner.py` | Discovers, orders and applies migrations |
| `backfill.py` | Chunked, resumable data backfills |
| `safety.py` | Pre-flight checks and timeouts |
| `versions/` | The migrations themselves |

## Known gaps

There is no staging replay harness yet, so migrations are reviewed rather than
rehearsed. That makes review the only gate.
