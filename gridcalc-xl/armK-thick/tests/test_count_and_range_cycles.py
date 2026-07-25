"""Task 3.2: COUNT and range cycle behavior — R3, R8, R9 tests."""

from gridcalc import Workbook
from gridcalc.formula import PARSE_ERROR, REF_ERROR, parse_formula


def _sheet():
    wb = Workbook()
    return wb.add_sheet("S")


class TestCountParser:
    def test_count_accepts_one_range_argument(self):
        assert parse_formula("COUNT(A1:A1)") == 0

    def test_count_rejects_no_arguments(self):
        assert parse_formula("COUNT()") == PARSE_ERROR

    def test_count_rejects_two_arguments(self):
        assert parse_formula("COUNT(A1:A1, B1:B1)") == PARSE_ERROR

    def test_count_rejects_single_ref_argument(self):
        assert parse_formula("COUNT(A1)") == PARSE_ERROR

    def test_count_rejects_parenthesized_range_argument(self):
        assert parse_formula("COUNT((A1:A1))") == PARSE_ERROR

    def test_range_remains_illegal_outside_range_argument(self):
        assert parse_formula("COUNT(A1:A1)+A1:A1") == PARSE_ERROR


class TestCountStructuralEvaluation:
    def test_count_counts_number_string_and_formula_cells(self):
        sh = _sheet()
        sh.set("A1", 1)
        sh.set("B1", "x")
        sh.set("C1", "=1/0")
        sh.set("D1", "=COUNT(A1:C1)")
        assert sh.get("D1") == 3

    def test_count_ignores_empty_cells(self):
        sh = _sheet()
        sh.set("A1", 1)
        sh.set("C1", "text")
        sh.set("D1", "=COUNT(A1:C1)")
        assert sh.get("D1") == 2

    def test_count_does_not_evaluate_formula_members(self):
        sh = _sheet()
        sh.set("A1", "=1/0")
        sh.set("B1", "=COUNT(A1:A1)")
        assert sh.get("B1") == 1
        assert sh.eval_count == 1

    def test_count_self_range_returns_one_without_reentry(self):
        sh = _sheet()
        sh.set("A1", "=COUNT(A1:A1)")
        assert sh.get("A1") == 1
        assert sh.eval_count == 1

    def test_count_returns_ref_error_for_invalid_range(self):
        sh = _sheet()
        sh.set("A1", "=COUNT(A0:A1)")
        assert sh.get("A1") == REF_ERROR


class TestRangeCycles:
    def test_sum_self_range_cycle(self):
        sh = _sheet()
        sh.set("A1", "=SUM(A1:A1)")
        assert sh.get("A1") == "#CYCLE!"

    def test_min_self_range_cycle(self):
        sh = _sheet()
        sh.set("A1", "=MIN(A1:A1)")
        assert sh.get("A1") == "#CYCLE!"

    def test_max_self_range_cycle(self):
        sh = _sheet()
        sh.set("A1", "=MAX(A1:A1)")
        assert sh.get("A1") == "#CYCLE!"

    def test_range_cycle_members_and_dependents_propagate_cycle(self):
        sh = _sheet()
        sh.set("A1", "=SUM(B1:B1)")
        sh.set("B1", "=MAX(A1:A1)")
        sh.set("C1", "=A1+1")
        assert sh.get("A1") == "#CYCLE!"
        assert sh.get("B1") == "#CYCLE!"
        assert sh.get("C1") == "#CYCLE!"

    def test_count_range_self_reference_is_not_a_cycle_member(self):
        sh = _sheet()
        sh.set("A1", "=COUNT(A1:B1)")
        sh.set("B1", "=A1+1")
        assert sh.get("A1") == 2
        assert sh.get("B1") == 3
