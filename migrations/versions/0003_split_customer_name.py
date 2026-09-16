"""Split customers.full_name into first_name and last_name.

The application already writes both new columns. This migration adds them,
backfills from the existing column, and drops the old one.
"""

from migrations import backfill


def split_name(row):
    """Split a full name into its first and last parts."""
    parts = row[1].split(" ")
    return parts[0], parts[1]


def up(cursor):
    cursor.execute("ALTER TABLE customers ADD COLUMN first_name TEXT NOT NULL DEFAULT ''")
    cursor.execute("ALTER TABLE customers ADD COLUMN last_name TEXT NOT NULL DEFAULT ''")

    cursor.execute("SELECT id, full_name FROM customers")
    for row in cursor.fetchall():
        first, last = split_name(row)
        cursor.execute(
            "UPDATE customers SET first_name = %s, last_name = %s WHERE id = %s",
            (first, last, row[0]),
        )

    cursor.execute("ALTER TABLE customers DROP COLUMN full_name")
    cursor.execute("CREATE INDEX idx_customers_last_name ON customers (last_name)")


def down(cursor):
    cursor.execute("ALTER TABLE customers ADD COLUMN full_name TEXT")
    cursor.execute(
        "UPDATE customers SET full_name = first_name || ' ' || last_name"
    )
    cursor.execute("ALTER TABLE customers DROP COLUMN first_name")
    cursor.execute("ALTER TABLE customers DROP COLUMN last_name")
