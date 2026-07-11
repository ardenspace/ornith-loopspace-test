"""Tests for base store operations: set, get, delete, count."""

from kvtx.database import Store


def test_set_and_get():
    store = Store()
    store.set("a", "x")
    assert store.get("a") == "x"


def test_get_unset_key_returns_none():
    store = Store()
    assert store.get("missing") is None


def test_delete_makes_get_return_none():
    store = Store()
    store.set("a", "x")
    store.delete("a")
    assert store.get("a") is None


def test_delete_unset_key_is_no_op():
    store = Store()
    store.delete("missing")  # should not raise


def test_overwrite_updates_value():
    store = Store()
    store.set("a", "x")
    store.set("a", "y")
    assert store.get("a") == "y"


def test_count_of_unheld_value_is_zero():
    store = Store()
    assert store.count("nope") == 0


def test_count_returns_int():
    store = Store()
    store.set("a", "x")
    assert isinstance(store.count("x"), int)


def test_get_returns_str_or_none():
    store = Store()
    store.set("a", "x")
    assert isinstance(store.get("a"), str)
    assert store.get("missing") is None


def test_multiple_keys_same_value():
    store = Store()
    store.set("a", "x")
    store.set("b", "x")
    assert store.count("x") == 2


def test_overwrite_updates_both_counts():
    store = Store()
    store.set("a", "x")
    store.set("b", "x")
    store.set("a", "y")
    assert store.count("x") == 1
    assert store.count("y") == 1


def test_delete_decrements_count():
    store = Store()
    store.set("a", "x")
    store.set("b", "x")
    store.delete("a")
    assert store.count("x") == 1


def test_delete_last_holder_zero_count():
    store = Store()
    store.set("a", "x")
    store.delete("a")
    assert store.count("x") == 0
