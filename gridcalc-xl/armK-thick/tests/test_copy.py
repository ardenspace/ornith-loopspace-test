"""Task 6.2: absolute references and copy rewriting."""

import pytest

from gridcalc import Workbook
from gridcalc.formula import PARSE_ERROR, REF_ERROR, parse_formula
from tests.reference_model import NaiveSheet


def _sheet():
    wb = Workbook()
    return wb, wb.add_sheet("S1")


def test_absolute_marks_evaluate_like_unmarked_refs_and_ranges():
    wb, sh = _sheet()
    sh.set("A1", 2)
    sh.set("B1", 3)

    assert parse_formula("$A$1", resolve_ref=lambda addr: ("int", 2) if addr == "A1" else ("invalid", None)) == 2
    sh.set("C1", "=$A1 + A$1 + $A$1 + SUM($A$1:B$1)")

    assert sh.get("C1") == 11
    assert wb.undo() is True


def test_ref_error_is_grammar_legal_primary_and_range_arg():
    wb, sh = _sheet()
    sh.set("A1", "=#REF!")
    sh.set("A2", "=1+#REF!")
    sh.set("A3", "=SUM(#REF!:A1)")
    sh.set("A4", "=SUM(A1:#REF!)")

    assert sh.get("A1") == REF_ERROR
    assert sh.get("A2") == REF_ERROR
    assert sh.get("A3") == REF_ERROR
    assert sh.get("A4") == REF_ERROR


def test_copy_validates_arguments_rejects_empty_source_and_does_not_journal_failures():
    wb, sh = _sheet()
    sh.set("B1", "old")

    with pytest.raises(ValueError):
        sh.copy("A1", "C1")
    with pytest.raises(ValueError):
        sh.copy("$B$1", "C1")
    sh.copy("B1", "S1!C1")
    assert sh.get("C1") == "old"

    assert sh.get("B1") == "old"
    assert wb.undo() is True
    assert sh.get("C1") is None
    assert sh.get("B1") == "old"
    assert wb.undo() is True
    assert sh.get("B1") is None


def test_copy_literal_values_are_normalized_identically():
    wb, sh = _sheet()
    sh.set("A1", 7)
    sh.set("B1", "previous")
    sh.copy("A1", "B1")

    assert sh.get("B1") == 7
    assert wb.undo() is True
    assert sh.get("B1") == "previous"
    assert wb.redo() is True
    assert sh.get("B1") == 7


def test_copy_literal_over_formula_target_clears_cached_formula_result():
    wb, sh = _sheet()
    sh.set("A1", 7)
    sh.set("B1", "=A1+1")

    assert sh.get("B1") == 8
    sh.copy("A1", "B1")

    assert sh.get("B1") == 7


def test_copy_does_not_evaluate_formulas_or_change_counters():
    wb, sh = _sheet()
    sh.set("A1", 5)
    sh.set("B1", "=A1+1")
    before = sh.eval_count

    sh.copy("B1", "C1")

    assert sh.eval_count == before
    assert sh.get("C1") == 7


def test_copy_preserves_unparseable_and_out_of_bounds_formula_text_byte_for_byte():
    wb, sh = _sheet()
    too_long = "=" + "A1+" * 200
    sh.set("A1", "=A1 +")
    sh.set("A2", too_long)

    sh.copy("A1", "B1")
    sh.copy("A2", "B2")

    assert sh.get("B1") == PARSE_ERROR
    assert sh._cells["B1"] == "=A1 +"
    assert sh._cells["B2"] == too_long


def test_copy_rewrites_parseable_refs_preserving_absolute_components_and_invalid_refs():
    wb, sh = _sheet()
    sh.set("A1", 10)
    sh.set("B1", "=A1 + $A1 + A$1 + $A$1 + A0 + A007 + A100")

    sh.copy("B1", "C2")


    assert sh._cells["C2"] == "=B2 + $A2 + B$1 + $A$1 + A0 + A007 + A100"
    assert sh.get("C2") == REF_ERROR


def test_copy_mixed_absolute_rewrite_matches_reference_model():
    wb, sh = _sheet()
    ref = NaiveSheet()
    for sheet in (sh, ref):
        sheet.set("A1", 2)
        sheet.set("A2", 3)
        sheet.set("B1", 5)
        sheet.set("B2", "=$A1+A$1")

    sh.copy("B2", "C3")
    ref.copy("B2", "C3")

    assert sh._cells["C3"] == ref._cells["C3"] == "=$A2+B$1"
    assert sh.get("C3") == ref.get("C3") == 8


def test_copy_replaces_shifted_refs_and_ranges_that_leave_grid_with_ref_error_text():
    wb, sh = _sheet()
    sh.set("Y98", "=Z99 + SUM(Y98 : Z99) + SUM($Y$98:$Z$99)")

    sh.copy("Y98", "Z99")


    assert sh._cells["Z99"] == "=#REF! + SUM(#REF!) + SUM($Y$98:$Z$99)"
    assert sh.get("Z99") == REF_ERROR


def test_copy_replaces_whole_range_when_first_endpoint_leaves_grid():
    wb, sh = _sheet()
    sh.set("B2", "=SUM(A2:B3)")

    sh.copy("B2", "A1")

    assert sh._cells["A1"] == "=SUM(#REF!)"


def test_copy_with_zero_delta_is_legal_and_text_unchanged():
    wb, sh = _sheet()
    sh.set("A1", "=A1 + $B$2")

    sh.copy("A1", "A1")

    assert sh._cells["A1"] == "=A1 + $B$2"


def test_copy_undo_restores_never_set_target_and_redo_reapplies():
    wb, sh = _sheet()
    sh.set("A1", "=B1+1")
    sh.copy("A1", "B2")

    assert sh._cells["B2"] == "=C2+1"
    assert wb.undo() is True
    assert sh.get("B2") is None
    assert wb.redo() is True
    assert sh._cells["B2"] == "=C2+1"
