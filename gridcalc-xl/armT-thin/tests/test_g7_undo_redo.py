import pytest

from gridcalc import Workbook


def test_set_copy_define_name_undo_redo_lifo_and_cache_invalidation():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", 1)
    sheet.set("B1", "=A1+1")
    assert sheet.get("B1") == 2

    sheet.set("A1", 5)
    assert sheet.get("B1") == 6
    before = sheet.eval_count
    assert wb.undo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count > before

    before = sheet.eval_count
    assert wb.redo() is True
    assert sheet.get("B1") == 6
    assert sheet.eval_count > before

    sheet.set("C1", "=AA")
    assert sheet.get("C1") == "#NAME!"
    sheet.define_name("AA", "A1")
    assert sheet.get("C1") == 5
    assert wb.undo() is True
    assert sheet.get("C1") == "#NAME!"
    assert wb.redo() is True
    assert sheet.get("C1") == 5

    sheet.copy("A1", "D1")
    assert sheet.get("D1") == 5
    assert wb.undo() is True
    assert sheet.get("D1") is None
    assert wb.redo() is True
    assert sheet.get("D1") == 5


def test_failed_calls_do_not_journal_and_new_operation_clears_redo():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", 1)

    with pytest.raises(ValueError):
        sheet.set("A0", 2)
    assert wb.undo() is True
    assert sheet.get("A1") is None
    assert wb.redo() is True
    assert sheet.get("A1") == 1

    assert wb.undo() is True
    sheet.set("B1", 2)
    assert wb.redo() is False
    assert sheet.get("A1") is None
    assert sheet.get("B1") == 2


def test_add_sheet_undo_invalidates_and_redo_restores_handle():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", 1)
    assert wb.undo() is True
    assert wb.undo() is True

    with pytest.raises(ValueError):
        sheet.get("A1")
    with pytest.raises(ValueError):
        sheet.eval_count
    assert wb.sheet_names == []

    assert wb.redo() is True
    assert wb.sheet_names == ["S1"]
    assert sheet.get("A1") is None


def test_eval_count_monotonic_across_undo_redo():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", "=1+1")
    assert sheet.get("A1") == 2
    count = sheet.eval_count

    assert wb.undo() is True
    assert sheet.eval_count == count
    assert wb.redo() is True
    assert sheet.get("A1") == 2
    assert sheet.eval_count >= count
