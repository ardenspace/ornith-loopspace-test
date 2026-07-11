import pytest
from kvtx import Database


class TestBaseStore:
    def test_set_and_get(self):
        db = Database()
        db.set("a", "1")
        assert db.get("a") == "1"

    def test_get_unset_key(self):
        db = Database()
        assert db.get("missing") is None

    def test_delete_makes_key_unset(self):
        db = Database()
        db.set("a", "1")
        db.delete("a")
        assert db.get("a") is None

    def test_delete_unset_key_is_noop(self):
        db = Database()
        db.delete("missing")
        assert db.get("missing") is None

    def test_overwrite(self):
        db = Database()
        db.set("a", "1")
        db.set("a", "2")
        assert db.get("a") == "2"

    def test_count_basic(self):
        db = Database()
        db.set("a", "x")
        db.set("b", "x")
        assert db.count("x") == 2

    def test_count_no_match(self):
        db = Database()
        db.set("a", "x")
        assert db.count("y") == 0

    def test_count_returns_int(self):
        db = Database()
        assert isinstance(db.count("x"), int)

    def test_get_returns_str_or_none(self):
        db = Database()
        db.set("a", "hello")
        assert isinstance(db.get("a"), str)
        assert db.get("missing") is None

    def test_overwrite_updates_both_counts(self):
        db = Database()
        db.set("a", "x")
        db.set("b", "x")
        db.set("a", "y")
        assert db.count("x") == 1
        assert db.count("y") == 1

    def test_delete_decrements_count(self):
        db = Database()
        db.set("a", "x")
        db.set("b", "x")
        db.delete("a")
        assert db.count("x") == 1

    def test_deleting_last_holder(self):
        db = Database()
        db.set("a", "x")
        db.delete("a")
        assert db.count("x") == 0
