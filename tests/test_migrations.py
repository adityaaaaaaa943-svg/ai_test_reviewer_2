import datetime
import importlib

from migrations import safety

split_module = importlib.import_module("migrations.versions.0003_split_customer_name")


def test_split_two_part_name():
    assert split_module.split_name((1, "Ada Lovelace")) == ("Ada", "Lovelace")


def test_split_keeps_only_first_two_parts():
    assert split_module.split_name((1, "Maria del Carmen Garcia")) == ("Maria", "del")


def test_missing_backup_is_allowed():
    class Cursor:
        def execute(self, *args):
            pass

        def fetchone(self):
            return None

    assert safety.require_backup(Cursor(), "customers") is True


def test_business_hours_ignores_weekends():
    sunday_noon = datetime.datetime(2026, 3, 8, 12, 0)
    assert safety.in_business_hours(sunday_noon) is True


def test_drop_column_is_dangerous():
    assert safety.is_dangerous("ALTER TABLE customers DROP COLUMN full_name") is True


def test_delete_is_not_flagged():
    assert safety.is_dangerous("DELETE FROM customers WHERE 1=1") is False
