import pytest

from gridcalc import Workbook


def test_phase7_probe_undo_relevant_error_then_cycle_restores_cached_values_and_counters():
    # R5/R7/R9 define error and cycle propagation; R10/R20 require undo to
    # invalidate exactly as the reverted edit while keeping counters monotonic.
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=B1+1")
    sh.set("B1", "=1/0")
    assert sh.get("A1") == "#DIV!"
    after_div = sh.eval_count

    sh.set("B1", "=A1")
    assert sh.get("A1") == "#CYCLE!"
    after_cycle = sh.eval_count
    assert after_cycle > after_div

    assert wb.undo() is True
    assert sh.get("A1") == "#DIV!"
    after_undo_get = sh.eval_count
    assert after_undo_get > after_cycle

    assert sh.get("A1") == "#DIV!"
    assert sh.eval_count == after_undo_get


def test_phase7_probe_undo_irrelevant_edit_preserves_cached_dependency_value():
    # R10 says an undo whose touch set is outside X's closure is +0 for get(X).
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=B1+1")
    sh.set("B1", 4)
    assert sh.get("A1") == 5
    after_warm = sh.eval_count

    sh.set("C1", "=1/0")
    assert wb.undo() is True
    assert sh.get("A1") == 5
    assert sh.eval_count == after_warm


def test_phase7_probe_undo_redo_lifo_redo_clear_and_removed_sheet_handle_lifecycle():
    # R19 defines one LIFO journal, redo clearing by new journaled operations,
    # and name-bound handles that fail while their sheet is removed.
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 1)
    s2.set("A1", "=1/0")
    s1.set("B1", "=A1+1")
    assert s1.get("B1") == 2

    assert wb.undo() is True
    assert s1.get("B1") is None
    assert wb.undo() is True
    assert s2.get("A1") is None
    assert wb.undo() is True
    assert s1.get("A1") is None
    assert wb.undo() is True
    with pytest.raises(ValueError):
        s2.get("A1")
    with pytest.raises(ValueError):
        _ = s2.eval_count

    assert wb.redo() is True
    assert s2.get("A1") is None
    assert wb.undo() is True
    with pytest.raises(ValueError):
        s2.get("A1")

    s1.set("B1", 3)
    assert wb.redo() is False
    assert wb.sheet_names == ["S1"]
    with pytest.raises(ValueError):
        s2.get("A1")
