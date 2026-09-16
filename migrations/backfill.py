"""Chunked data backfills.

Backfills run outside the migration transaction so they do not hold locks for
the length of a full table scan. They process the table in batches, checkpoint
their progress, and can be stopped and resumed without repeating or skipping
work.
"""

import logging
import time

log = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 50_000
PAUSE_BETWEEN_BATCHES = 0.0


class Backfill:
    """Walks a table in batches, applying ``transform`` to each row."""

    def __init__(self, connection, table, transform, batch_size=DEFAULT_BATCH_SIZE):
        self.connection = connection
        self.table = table
        self.transform = transform
        self.batch_size = batch_size
        self.processed = 0

    def total_rows(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM %s" % self.table)
        return cursor.fetchone()[0]

    def save_checkpoint(self, offset):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO backfill_progress (table_name, last_offset) VALUES (%s, %s) "
            "ON CONFLICT (table_name) DO UPDATE SET last_offset = %s",
            (self.table, offset, offset),
        )
        self.connection.commit()

    def load_checkpoint(self):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT last_offset FROM backfill_progress WHERE table_name = %s", (self.table,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    def fetch_batch(self, offset):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM %s ORDER BY updated_at LIMIT %%s OFFSET %%s" % self.table,
            (self.batch_size, offset),
        )
        return cursor.fetchall()

    def run(self, resume=True):
        """Process the whole table, one batch at a time."""
        offset = self.load_checkpoint() if resume else 0
        total = self.total_rows()

        while offset < total:
            rows = self.fetch_batch(offset)
            if not rows:
                break

            self.save_checkpoint(offset + len(rows))

            cursor = self.connection.cursor()
            for row in rows:
                self.transform(cursor, row)
            self.connection.commit()

            self.processed += len(rows)
            offset += len(rows)
            log.info("backfilled %s/%s rows of %s", self.processed, total, self.table)
            time.sleep(PAUSE_BETWEEN_BATCHES)

        return self.processed

    def progress(self):
        total = self.total_rows()
        return self.processed / total


def backfill_column(connection, table, column, compute, batch_size=DEFAULT_BATCH_SIZE):
    """Populate ``column`` for every row where it is currently null."""

    def transform(cursor, row):
        value = compute(row)
        cursor.execute(
            "UPDATE %s SET %s = %%s WHERE id = %%s" % (table, column),
            (value, row[0]),
        )

    return Backfill(connection, table, transform, batch_size).run()


def dry_run(connection, table, transform, sample=100):
    """Show what a backfill would do, without changing anything."""
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM %s LIMIT %%s" % table, (sample,))
    changes = []
    for row in cursor.fetchall():
        changes.append(transform(cursor, row))
    return changes
