"""Tests for Database nested transactions: begin, rollback, commit."""

from kvtx.database import Database


def test_reads_see_uncommitted_writes():
    db = Database()
    db.begin()
    db.set("a", "1")
    assert db.get("a") == "1"
    assert db.count("1") == 1


def test_rollback_undoes_innermost_writes():
    db = Database()
    db.begin()
    db.set("a", "1")
    result = db.rollback()
    assert result is True
    assert db.get("a") is None


def test_rollback_restores_prior_value_on_overwrite():
    db = Database()
    db.set("a", "1")
    db.begin()
    db.set("a", "2")
    db.rollback()
    assert db.get("a") == "1"


def test_rollback_restores_deleted_key():
    db = Database()
    db.set("a", "1")
    db.begin()
    db.delete("a")
    db.rollback()
    assert db.get("a") == "1"


def test_nested_rollback_only_undoes_innermost():
    db = Database()
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
    db = Database()
    db.begin()
    db.set("a", "1")
    db.begin()
    db.set("a", "2")
    result = db.commit()
    assert result is True
    assert db.get("a") == "2"
    result2 = db.rollback()
    assert result2 is False


def test_rollback_with_no_open_transaction():
    db = Database()
    result = db.rollback()
    assert result is False
    assert db.get("any_key") is None


def test_commit_with_no_open_transaction():
    db = Database()
    result = db.commit()
    assert result is False


def test_count_reflects_overlays_and_restored_by_rollback():
    db = Database()
    db.set("a", "x")
    db.begin()
    db.set("b", "x")
    assert db.count("x") == 2
    db.rollback()
    assert db.count("x") == 1


def test_count_reflects_overlays_and_preserved_by_commit():
    db = Database()
    db.set("a", "x")
    db.begin()
    db.set("b", "x")
    db.commit()
    assert db.count("x") == 2
    assert db.rollback() is False


def test_overwrite_inside_transaction_count_consistency():
    db = Database()
    db.set("a", "x")
    db.begin()
    db.set("a", "y")
    assert db.count("x") == 0
    assert db.count("y") == 1
    db.rollback()
    assert db.count("x") == 1
    assert db.count("y") == 0


def test_delete_inside_transaction_count_consistency():
    db = Database()
    db.set("a", "x")
    db.set("b", "x")
    db.begin()
    db.delete("a")
    assert db.count("x") == 1
    db.rollback()
    assert db.count("x") == 2


def test_deep_nesting_with_mixed_commit():
    db = Database()
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
    result = db.commit()
    assert result is True
    assert db.get("a") == "2"
    assert db.rollback() is False


def test_import_from_package_root():
    from kvtx import Database as DBFromRoot
    db = DBFromRoot()
    db.set("a", "1")
    assert db.get("a") == "1"


def test_database_exposes_required_methods():
    from kvtx import Database
    db = Database()
    assert hasattr(db, "set")
    assert hasattr(db, "get")
    assert hasattr(db, "delete")
    assert hasattr(db, "count")
    assert hasattr(db, "begin")
    assert hasattr(db, "rollback")
    assert hasattr(db, "commit")
