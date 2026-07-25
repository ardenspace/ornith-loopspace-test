"""Task 10.2: Volatile invalidation and warm bound (R27)."""

from gridcalc.formula import PARSE_ERROR
from gridcalc.workbook import Workbook


def _total_eval_count(wb):
    return sum(wb.sheet(name).eval_count for name in wb.sheet_names)


def test_unselected_if_now_marks_formula_volatile_but_string_and_parse_error_do_not():
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=IF(0,NOW(),10)")
    sh.set("A2", '=CONCAT("NOW()")')
    sh.set("A3", "=NOW(")

    assert sh.get("A1") == 10
    assert sh.get("A2") == "NOW()"
    assert sh.get("A3") == PARSE_ERROR
    before = sh.eval_count

    wb.advance_clock()

    assert sh.get("A1") == 10
    assert sh.eval_count - before == 1
    before = sh.eval_count
    assert sh.get("A2") == "NOW()"
    assert sh.get("A3") == PARSE_ERROR
    assert sh.eval_count == before


def test_transitive_now_closure_matches_current_clock_after_clock_edits():
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=NOW()")
    sh.set("B1", "=A1+5")

    assert sh.get("B1") == 5
    wb.advance_clock()
    wb.advance_clock()

    assert sh.get("B1") == 7


def test_repeat_reads_without_edit_have_zero_eval_delta_for_volatile_formula():
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=NOW()")
    sh.set("B1", "=A1+1")

    assert sh.get("B1") == 1
    before = sh.eval_count
    assert sh.get("B1") == 1
    assert sh.eval_count == before


def test_clock_only_edit_does_not_invalidate_nonvolatile_closure():
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=1+1")
    sh.set("B1", "=A1+1")

    assert sh.get("B1") == 3
    before = sh.eval_count
    wb.advance_clock()

    assert sh.get("B1") == 3
    assert sh.eval_count == before


def test_clock_undo_redo_invalidate_only_volatile_formula_cells():
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=NOW()")
    sh.set("B1", "=1+1")

    assert sh.get("A1") == 0
    assert sh.get("B1") == 2
    before = sh.eval_count
    wb.advance_clock()
    assert sh.get("A1") == 1
    assert sh.get("B1") == 2
    assert sh.eval_count - before == 1

    before = sh.eval_count
    assert wb.undo() is True
    assert sh.get("A1") == 0
    assert sh.get("B1") == 2
    assert sh.eval_count - before == 1

    before = sh.eval_count
    assert wb.redo() is True
    assert sh.get("A1") == 1
    assert sh.get("B1") == 2
    assert sh.eval_count - before == 1


def test_warm_clock_only_edits_recompute_at_most_volatile_formula_cells_in_closure():
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", "=1+1")
    sh.set("A2", "=A1+1")
    sh.set("B1", "=A2+NOW()")

    assert sh.get("B1") == 3
    assert sh.get("A1") == 2
    assert sh.get("A2") == 3
    assert sh.get("B1") == 3
    before = _total_eval_count(wb)

    wb.advance_clock()
    wb.advance_clock()

    assert sh.get("B1") == 5
    assert _total_eval_count(wb) - before <= 1
