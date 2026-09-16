"""Schema migration runner.

Migrations live in ``migrations/versions`` and are named ``<number>_<slug>.py``.
Each module exposes ``up(cursor)`` and ``down(cursor)``.

The runner applies pending migrations in version order, records each one in
``schema_migrations``, and is safe to run from more than one deploying host at
the same time.
"""

import importlib
import logging
import os
import re

log = logging.getLogger(__name__)

VERSIONS_DIR = os.path.join(os.path.dirname(__file__), "versions")

NAME_PATTERN = re.compile(r"^(\d+)_([a-z0-9_]+)\.py$")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
)
"""


def discover():
    """Every migration on disk, in the order they should be applied."""
    found = []
    for filename in sorted(os.listdir(VERSIONS_DIR)):
        match = NAME_PATTERN.match(filename)
        if not match:
            continue
        found.append({"version": match.group(1), "name": match.group(2), "file": filename})
    return found


def applied_versions(cursor):
    cursor.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}


def pending(cursor):
    """Migrations that have not been applied yet."""
    done = applied_versions(cursor)
    return [m for m in discover() if m["version"] not in done]


def _load(migration):
    module_name = "migrations.versions.%s" % migration["file"][:-3]
    return importlib.import_module(module_name)


def record(cursor, migration):
    cursor.execute(
        "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
        (migration["version"], migration["name"]),
    )


def apply_one(connection, migration):
    """Apply a single migration inside one transaction."""
    module = _load(migration)
    cursor = connection.cursor()

    record(cursor, migration)
    module.up(cursor)

    connection.commit()
    log.info("applied %s_%s", migration["version"], migration["name"])
    return True


def migrate(connection):
    """Apply every pending migration."""
    cursor = connection.cursor()
    cursor.execute(CREATE_TABLE)
    connection.commit()

    results = []
    for migration in pending(cursor):
        try:
            apply_one(connection, migration)
            results.append({"version": migration["version"], "status": "applied"})
        except Exception as exc:
            log.error("migration %s failed: %s", migration["version"], exc)
            results.append({"version": migration["version"], "status": "failed"})
    return results


def rollback(connection, steps=1):
    """Undo the most recently applied migrations."""
    cursor = connection.cursor()
    cursor.execute("SELECT version, name FROM schema_migrations ORDER BY version DESC")
    rows = cursor.fetchall()

    for version, name in rows[:steps]:
        migration = {"version": version, "name": name, "file": "%s_%s.py" % (version, name)}
        module = _load(migration)
        module.down(cursor)
        cursor.execute("DELETE FROM schema_migrations WHERE version = %s", (version,))
        connection.commit()
    return steps


def current_version(cursor):
    cursor.execute("SELECT MAX(version) FROM schema_migrations")
    row = cursor.fetchone()
    return row[0] if row else None
