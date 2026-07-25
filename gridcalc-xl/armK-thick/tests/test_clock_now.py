"""Task 10.1: NOW() function (R26)."""

from gridcalc.formula import PARSE_ERROR, parse_formula
from gridcalc.workbook import Workbook


def test_parse_formula_accepts_uppercase_now_empty_call_with_clock_callback():
    assert parse_formula("NOW()", resolve_now=lambda: 7) == 7


def test_parse_formula_rejects_lowercase_and_mixed_case_now():
    assert parse_formula("now()") == PARSE_ERROR
    assert parse_formula("Now()") == PARSE_ERROR


def test_parse_formula_rejects_now_with_arguments():
    assert parse_formula("NOW(1)", resolve_now=lambda: 7) == PARSE_ERROR
    assert parse_formula("NOW(A1)", resolve_now=lambda: 7) == PARSE_ERROR


def test_empty_parentheses_on_other_functions_remain_parse_error():
    assert parse_formula("CONCAT()") == PARSE_ERROR
    assert parse_formula("LEN()") == PARSE_ERROR
    assert parse_formula("IF()") == PARSE_ERROR
    assert parse_formula("SUM()") == PARSE_ERROR


def test_workbook_now_evaluates_to_current_clock_int():
    wb = Workbook()
    sh = wb.add_sheet("S1")
    sh.set("A1", "=NOW()")

    assert sh.get("A1") == 0
    assert isinstance(sh.get("A1"), int)
    wb.advance_clock()
    assert sh.get("A1") == 1


def test_now_inside_if_len_concat_uses_current_clock():
    wb = Workbook()
    sh = wb.add_sheet("S1")
    wb.advance_clock()
    wb.advance_clock()

    sh.set("A1", "=IF(1,NOW(),0)")
    sh.set("A2", "=LEN(NOW())")
    sh.set("A3", '=CONCAT("t",NOW())')

    assert sh.get("A1") == 2
    assert sh.get("A2") == 1
    assert sh.get("A3") == "t2"


def test_undo_redo_advance_clock_invalidates_cached_now_results():
    wb = Workbook()
    sh = wb.add_sheet("S1")
    sh.set("A1", "=NOW()")

    assert sh.get("A1") == 0
    wb.advance_clock()
    assert sh.get("A1") == 1
    assert wb.undo() is True
    assert sh.get("A1") == 0
    assert wb.redo() is True
    assert sh.get("A1") == 1
