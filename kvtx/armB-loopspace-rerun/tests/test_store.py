from kvtx.database import Store


def test_set_and_get():
    s = Store()
    s.set("k", "v")
    assert s.get("k") == "v"


def test_get_unset_key_returns_none():
    s = Store()
    assert s.get("missing") is None


def test_delete_makes_get_return_none():
    s = Store()
    s.set("k", "v")
    s.delete("k")
    assert s.get("k") is None


def test_delete_unset_key_is_noop():
    s = Store()
    s.delete("missing")  # should not raise


def test_overwrite_updates_get():
    s = Store()
    s.set("k", "a")
    s.set("k", "b")
    assert s.get("k") == "b"


def test_count_of_unheld_value_returns_zero():
    s = Store()
    assert s.count("nope") == 0


def test_count_returns_int():
    s = Store()
    assert isinstance(s.count("x"), int)


def test_get_returns_str_or_none():
    s = Store()
    s.set("k", "v")
    assert isinstance(s.get("k"), str)
    assert s.get("missing") is None


def test_multiple_keys_same_value():
    s = Store()
    s.set("a", "x")
    s.set("b", "x")
    assert s.count("x") == 2


def test_overwrite_updates_both_counts():
    s = Store()
    s.set("a", "x")
    s.set("b", "x")
    s.set("a", "y")
    assert s.count("x") == 1
    assert s.count("y") == 1


def test_delete_decrements_count():
    s = Store()
    s.set("a", "x")
    s.set("b", "x")
    s.delete("a")
    assert s.count("x") == 1


def test_deleting_last_holder_zero_count():
    s = Store()
    s.set("a", "x")
    s.delete("a")
    assert s.count("x") == 0
