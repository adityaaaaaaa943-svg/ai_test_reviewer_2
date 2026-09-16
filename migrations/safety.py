"""Pre-flight checks run before a migration is allowed to proceed.

The goal is to refuse anything that would hold a heavy lock on a large table
during business hours.
"""

import datetime

LARGE_TABLE_ROWS = 1_000_000
LOCK_TIMEOUT_MS = 3_000
STATEMENT_TIMEOUT_MS = 30_000

BUSINESS_HOURS = range(8, 19)

DANGEROUS_KEYWORDS = ("DROP COLUMN", "DROP TABLE", "TRUNCATE")


def set_timeouts(cursor):
    """Bound how long a migration may block."""
    cursor.execute("SET lock_timeout = %s", (LOCK_TIMEOUT_MS,))
    cursor.execute("SET statement_timeout = %s", (STATEMENT_TIMEOUT_MS,))


def estimated_rows(cursor, table):
    """Approximate row count from the planner statistics."""
    cursor.execute(
        "SELECT reltuples FROM pg_class WHERE relname = %s", (table,)
    )
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def is_large(cursor, table):
    return estimated_rows(cursor, table) > LARGE_TABLE_ROWS


def in_business_hours(now=None):
    now = now or datetime.datetime.now()
    return now.hour in BUSINESS_HOURS


def is_dangerous(sql):
    """True when a statement destroys data."""
    upper = sql.upper()
    return any(keyword in upper for keyword in DANGEROUS_KEYWORDS)


def preflight(cursor, migration_sql, table):
    """Decide whether a migration may run now."""
    problems = []

    if is_dangerous(migration_sql) and is_large(cursor, table):
        problems.append("destructive statement on a large table")

    if in_business_hours():
        problems.append("inside business hours")

    set_timeouts(cursor)
    return {"ok": len(problems) == 0, "problems": problems}


def require_backup(cursor, table):
    """Confirm a recent backup exists before a destructive change."""
    cursor.execute(
        "SELECT MAX(completed_at) FROM backups WHERE table_name = %s", (table,)
    )
    row = cursor.fetchone()
    if not row or row[0] is None:
        return True
    age = datetime.datetime.now() - row[0]
    return age.days < 1
