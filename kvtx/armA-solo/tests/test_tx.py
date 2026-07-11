from kvtx import Database


class TestTransactions:
    def test_reads_see_uncommitted_writes(self):
        db = Database()
        db.begin()
        db.set("a", "1")
        assert db.get("a") == "1"
        assert db.count("1") == 1

    def test_rollback_undoes_writes(self):
        db = Database()
        db.begin()
        db.set("a", "1")
        assert db.rollback() is True
        assert db.get("a") is None

    def test_rollback_restores_prior_value(self):
        db = Database()
        db.set("a", "1")
        db.begin()
        db.set("a", "2")
        db.rollback()
        assert db.get("a") == "1"

    def test_rollback_restores_deleted_key(self):
        db = Database()
        db.set("a", "1")
        db.begin()
        db.delete("a")
        db.rollback()
        assert db.get("a") == "1"

    def test_nested_rollback_innermost_only(self):
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

    def test_commit_applies_all_and_clears_stack(self):
        db = Database()
        db.begin()
        db.set("a", "1")
        db.begin()
        db.set("a", "2")
        assert db.commit() is True
        assert db.get("a") == "2"
        assert db.rollback() is False

    def test_rollback_no_open_returns_false(self):
        db = Database()
        assert db.rollback() is False
        assert db.get("any") is None

    def test_commit_no_open_returns_false(self):
        db = Database()
        assert db.commit() is False

    def test_count_reflects_overlays_and_restored_by_rollback(self):
        db = Database()
        db.set("a", "x")
        db.begin()
        db.set("b", "x")
        assert db.count("x") == 2
        db.rollback()
        assert db.count("x") == 1

    def test_count_reflects_overlays_and_preserved_by_commit(self):
        db = Database()
        db.set("a", "x")
        db.begin()
        db.set("b", "x")
        db.commit()
        assert db.count("x") == 2
        assert db.rollback() is False

    def test_overwrite_inside_tx_count_consistency(self):
        db = Database()
        db.set("a", "x")
        db.begin()
        db.set("a", "y")
        assert db.count("x") == 0
        assert db.count("y") == 1
        db.rollback()
        assert db.count("x") == 1
        assert db.count("y") == 0

    def test_delete_inside_tx_count_consistency(self):
        db = Database()
        db.set("a", "x")
        db.set("b", "x")
        db.begin()
        db.delete("a")
        assert db.count("x") == 1
        db.rollback()
        assert db.count("x") == 2

    def test_deep_nesting_mixed_commit(self):
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
        db.commit()
        assert db.get("a") == "2"
        assert db.rollback() is False

    def test_import_and_exposes_methods(self):
        from kvtx import Database as D
        db = D()
        for method in ("set", "get", "delete", "count", "begin", "rollback", "commit"):
            assert hasattr(db, method)
