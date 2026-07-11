from kvtx.database import Database


def _db():
    return Database()


def test_reads_see_uncommitted_writes():
    db = _db()
    db.begin()
    db.set("a", "1")
    assert db.get("a") == "1"
    assert db.count("1") == 1


def test_rollback_undoes_writes_in_innermost_tx():
    db = _db()
    db.begin()
    db.set("a", "1")
    assert db.rollback() is True
    assert db.get("a") is None


def test_rollback_restores_prior_value_on_overwrite():
    db = _db()
    db.set("a", "1")
    db.begin()
    db.set("a", "2")
    db.rollback()
    assert db.get("a") == "1"


def test_rollback_restores_deleted_key():
    db = _db()
    db.set("a", "1")
    db.begin()
    db.delete("a")
    db.rollback()
    assert db.get("a") == "1"


def test_nested_rollback_only_undoes_innermost():
    db = _db()
    db.set("a", "1")
    db.begin()
    db.set("a", "2")
    db.begin()
    db.set("a", "3")
    db.rollback()
    assert db.get("a") == "2"
    db.rollback()
    assert db.get("a") == "1"


def test_commit_applies_all_and_clears_stack():
    db = _db()
    db.begin()
    db.set("a", "1")
    db.begin()
    db.set("a", "2")
    assert db.commit() is True
    assert db.get("a") == "2"
    assert db.rollback() is False


def test_rollback_with_no_open_tx_returns_false():
    db = _db()
    assert db.rollback() is False
    assert db.get("any") is None


def test_commit_with_no_open_tx_returns_false():
    db = _db()
    assert db.commit() is False


def test_count_reflects_overlays_and_restored_by_rollback():
    db = _db()
    db.set("a", "x")
    db.begin()
    db.set("b", "x")
    assert db.count("x") == 2
    db.rollback()
    assert db.count("x") == 1


def test_count_reflects_overlays_and_preserved_by_commit():
    db = _db()
    db.set("a", "x")
    db.begin()
    db.set("b", "x")
    db.commit()
    assert db.count("x") == 2
    assert db.rollback() is False


def test_overwrite_inside_tx_count_consistency():
    db = _db()
    db.set("a", "x")
    db.begin()
    db.set("a", "y")
    assert db.count("x") == 0
    assert db.count("y") == 1
    db.rollback()
    assert db.count("x") == 1
    assert db.count("y") == 0


def test_delete_inside_tx_count_consistency():
    db = _db()
    db.set("a", "x")
    db.set("b", "x")
    db.begin()
    db.delete("a")
    assert db.count("x") == 1
    db.rollback()
    assert db.count("x") == 2


def test_deep_nesting_with_mixed_commit_point():
    db = _db()
    db.set("a", "1")
    db.begin()
    db.set("a", "2")
    db.begin()
    db.delete("a")
    db.begin()
    db.set("a", "3")
    db.rollback()
    assert db.get("a") is None
    db.rollback()
    assert db.get("a") == "2"
    db.commit()
    assert db.get("a") == "2"
    assert db.rollback() is False
