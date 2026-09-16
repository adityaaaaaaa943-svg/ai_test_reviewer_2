"""Add a currency column to orders.

Historic orders predate multi-currency and were all settled in GBP, so the
backfill sets them accordingly.
"""

TABLE = "orders"


def up(cursor):
    cursor.execute(
        "ALTER TABLE orders ADD COLUMN currency CHAR(3) NOT NULL DEFAULT 'GBP'"
    )
    cursor.execute(
        "ALTER TABLE orders ADD CONSTRAINT orders_currency_check "
        "CHECK (currency IN ('GBP', 'EUR', 'USD', 'INR'))"
    )
    cursor.execute("UPDATE orders SET currency = 'GBP' WHERE currency IS NULL")
    cursor.execute(
        "ALTER TABLE order_lines ADD COLUMN currency CHAR(3) "
        "REFERENCES currencies (code)"
    )
    cursor.execute("CREATE UNIQUE INDEX idx_orders_currency ON orders (currency)")


def down(cursor):
    cursor.execute("ALTER TABLE orders DROP COLUMN currency")
    cursor.execute("ALTER TABLE order_lines DROP COLUMN currency")
