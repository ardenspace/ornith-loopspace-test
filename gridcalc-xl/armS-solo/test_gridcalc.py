"""Comprehensive test suite for gridcalc.

Covers all acceptance groups G1-G10 from SPEC.md.
"""

import json
import pytest
from gridcalc import Workbook


# ============================================================================
# G1: R1, R2 — cell store
# ============================================================================


class TestG1CellStore:
    """R1: Address validation; R2: set/get semantics."""

    def test_r1_valid_addresses(self):
        """R1: A1-Z99 are valid."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            for row in range(1, 100):
                addr = f"{col}{row}"
                s.set(addr, 1)
                assert s.get(addr) == 1

    def test_r1_invalid_addresses(self):
        """R1: invalid addresses raise ValueError."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        invalid = ["", "a1", "A0", "A01", "A100", "AA1", " A1", "A1 ", "S1!A1", 5, None]
        for addr in invalid:
            with pytest.raises(ValueError):
                s.get(addr)

    def test_r2_set_int(self):
        """R2: set int."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 42)
        assert s.get("A1") == 42

    def test_r2_set_str_literal(self):
        """R2: set string literal."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "hello")
        assert s.get("A1") == "hello"

    def test_r2_set_empty_string(self):
        """R2: empty string is a valid literal."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "")
        assert s.get("A1") == ""

    def test_r2_set_formula(self):
        """R2: str starting with = is a formula."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=1+1")
        assert s.get("A1") == 2

    def test_r2_bool_rejected(self):
        """R2: bool raises ValueError."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        with pytest.raises(ValueError):
            s.set("A1", True)

    def test_r2_get_empty_cell(self):
        """R2: get on never-set cell returns None."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        assert s.get("A1") is None

    def test_r2_set_replaces(self):
        """R2: set on occupied cell replaces content."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert s.get("A1") == 2


# ============================================================================
# G2: R3, R4, R5, R6 — formula grammar and scalar evaluation
# ============================================================================


class TestG2FormulaGrammar:
    """R3: grammar; R4: integer division; R5: error ordering; R6: ref semantics."""

    def test_r3_empty_formula(self):
        """R3: = evaluates to #PARSE!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=")
        assert s.get("A1") == "#PARSE!"

    def test_r3_arithmetic(self):
        """R3: basic arithmetic."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=1+2")
        assert s.get("A1") == 3
        s.set("A2", "=3-1")
        assert s.get("A2") == 2
        s.set("A3", "=2*3")
        assert s.get("A3") == 6
        s.set("A4", "=6/2")
        assert s.get("A4") == 3

    def test_r3_unary_minus(self):
        """R3: unary minus stacks."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=-1")
        assert s.get("A1") == -1
        s.set("A2", "=--1")
        assert s.get("A2") == 1
        s.set("A3", "=2--3")
        assert s.get("A3") == 5

    def test_r3_comparisons(self):
        """R3: comparisons yield 1/0."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=1<2")
        assert s.get("A1") == 1
        s.set("A2", "=2<1")
        assert s.get("A2") == 0
        s.set("A3", "=1<2<3")
        assert s.get("A3") == 1  # (1<2)<3 = 1<3 = 1

    def test_r4_integer_division(self):
        """R4: truncation toward zero."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=-7/2")
        assert s.get("A1") == -3
        s.set("A2", "=7/-2")
        assert s.get("A2") == -3
        s.set("A3", "=7/2")
        assert s.get("A3") == 3

    def test_r4_division_by_zero(self):
        """R4: division by zero is #DIV!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=1/0")
        assert s.get("A1") == "#DIV!"

    def test_r5_error_ordering(self):
        """R5: first error in left-to-right order is the result."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=1/0+1")
        assert s.get("A1") == "#DIV!"

    def test_r6_empty_cell_is_zero(self):
        """R6: empty cell contributes int 0."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=A2+1")
        assert s.get("A1") == 1  # A2 is empty, contributes 0

    def test_r6_invalid_ref(self):
        """R6: ref with leading zero or out-of-range row is #REF!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=A01+1")
        assert s.get("A1") == "#REF!"
        s.set("A2", "=A100+1")
        assert s.get("A2") == "#REF!"


# ============================================================================
# G3: R7, R8, R9 — ranges, functions, cycles
# ============================================================================


class TestG3RangesFunctionsCycles:
    """R7: range semantics; R8: COUNT; R9: cycles."""

    def test_r7_range_sum(self):
        """R7: SUM over a range."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", 2)
        s.set("A3", "=SUM(A1:A2)")
        assert s.get("A3") == 3

    def test_r7_range_type_error(self):
        """R7: string in range for SUM is #TYPE!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "hello")
        s.set("A2", "=SUM(A1:A1)")
        assert s.get("A2") == "#TYPE!"

    def test_r8_count(self):
        """R8: COUNT returns number of non-empty cells."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "hello")
        s.set("A3", "=COUNT(A1:A2)")
        assert s.get("A3") == 2

    def test_r8_count_empty_range(self):
        """R8: COUNT on all-empty range is 0."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=COUNT(A10:A20)")
        assert s.get("A1") == 0

    def test_r8_count_no_evaluation(self):
        """R8: COUNT does not evaluate range members."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=COUNT(A2:A2)")
        s.set("A2", "=1/0")  # Would error if evaluated
        assert s.get("A1") == 1  # A2 is non-empty, so count is 1

    def test_r9_cycle(self):
        """R9: circular reference is #CYCLE!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=A2+1")
        s.set("A2", "=A1+1")
        assert s.get("A1") == "#CYCLE!"
        assert s.get("A2") == "#CYCLE!"


# ============================================================================
# G4: R10, R11, R12 — incremental recomputation
# ============================================================================


class TestG4IncrementalRecomputation:
    """R10: eval_count bounds; R11: naive equivalence; R12: bounds."""

    def test_r10_repeat_read(self):
        """R10: two consecutive gets add 0 on second."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=A1+1")
        s.get("A2")
        assert s.eval_count == 1
        s.get("A2")
        assert s.eval_count == 1  # No change

    def test_r10_irrelevant_edit(self):
        """R10: edit outside closure adds 0."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=A1+1")
        s.get("A2")
        s.set("B1", 100)  # Outside closure of A2
        s.get("A2")
        assert s.eval_count == 1  # No change

    def test_r10_relevant_edit(self):
        """R10: edit inside closure adds at least 1."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=A1+1")
        s.get("A2")
        s.set("A1", 2)  # Inside closure of A2
        s.get("A2")
        assert s.eval_count == 2  # At least 1

    def test_r11_naive_equivalence(self):
        """R11: values match naive full recomputation."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=A1+1")
        s.set("A3", "=A2*2")
        assert s.get("A3") == 4


# ============================================================================
# G5: R13, R14, R15 — string type and functions
# ============================================================================


class TestG5StringType:
    """R13: string literals and typing; R14: CONCAT/LEN; R15: IF."""

    def test_r13_string_literal(self):
        """R13: string literal in formula."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", '="hello"')
        assert s.get("A1") == "hello"

    def test_r13_string_comparison(self):
        """R13: string comparison."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", '="a"="b"')
        assert s.get("A1") == 0
        s.set("A2", '="a"="a"')
        assert s.get("A2") == 1

    def test_r13_mixed_type_comparison(self):
        """R13: mixed int-str comparison is #TYPE!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", '="a"=1')
        assert s.get("A1") == "#TYPE!"

    def test_r14_concat(self):
        """R14: CONCAT concatenates."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", '=CONCAT("a","b","c")')
        assert s.get("A1") == "abc"

    def test_r14_concat_int(self):
        """R14: CONCAT renders int as decimal."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=CONCAT(1,2,3)")
        assert s.get("A1") == "123"

    def test_r14_len(self):
        """R14: LEN returns length."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", '=LEN("hello")')
        assert s.get("A1") == 5
        s.set("A2", "=LEN(123)")
        assert s.get("A2") == 3

    def test_r15_if_true(self):
        """R15: IF selects true branch when condition nonzero."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=IF(1,10,20)")
        assert s.get("A1") == 10

    def test_r15_if_false(self):
        """R15: IF selects false branch when condition zero."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=IF(0,10,20)")
        assert s.get("A1") == 20

    def test_r15_if_skip_unselected(self):
        """R15: unselected branch is never evaluated."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=IF(1,1,1/0)")  # False branch has error, but not selected
        assert s.get("A1") == 1


# ============================================================================
# G6: R16, R17, R18 — absolute references, copy, named ranges
# ============================================================================


class TestG6AbsoluteRefsCopyNames:
    """R16: $ marks; R17: copy; R18: define_name."""

    def test_r16_absolute_ref(self):
        """R16: $ marks don't affect evaluation."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=$A$1")
        assert s.get("A2") == 1

    def test_r17_copy_literal(self):
        """R17: copy literal."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 42)
        s.copy("A1", "B1")
        assert s.get("B1") == 42

    def test_r17_copy_formula_shift(self):
        """R17: copy formula shifts refs."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("B1", "=A1")
        s.copy("B1", "C1")
        assert s.get("C1") == 1  # Formula =B1 evaluates to 1

    def test_r17_copy_absolute_no_shift(self):
        """R17: $ marks prevent shifting."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("B1", "=$A$1")
        s.copy("B1", "C1")
        assert s.get("C1") == 1  # $A$1 still refers to A1

    def test_r17_copy_out_of_grid(self):
        """R17: shifted ref leaves grid → #REF!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("Z1", 1)
        s.set("A1", "=Z1")
        s.copy("A1", "B1")  # Column shift from A to B: Z+1 = outside grid
        assert s.get("B1") == "#REF!"

    def test_r18_define_name(self):
        """R18: define_name binds a name."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 42)
        s.define_name("MyRef", "A1")
        s.set("B1", "=MyRef")
        assert s.get("B1") == 42

    def test_r18_undefined_name(self):
        """R18: undefined name is #NAME!."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=UndefinedName")
        assert s.get("A1") == "#NAME!"


# ============================================================================
# G7: R19, R20 — undo/redo
# ============================================================================


class TestG7UndoRedo:
    """R19: journal; R20: counters."""

    def test_r19_undo_set(self):
        """R19: undo reverts set."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert s.get("A1") == 2
        wb.undo()
        assert s.get("A1") == 1

    def test_r19_redo_set(self):
        """R19: redo re-applies set."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        wb.undo()
        assert s.get("A1") is None
        wb.redo()
        assert s.get("A1") == 1

    def test_r19_undo_add_sheet(self):
        """R19: undo removes sheet."""
        wb = Workbook()
        wb.add_sheet("S1")
        wb.add_sheet("S2")
        wb.undo()
        assert wb.sheet_names == ["S1"]

    def test_r20_counters_monotonic(self):
        """R20: eval_count never decreases."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=A1")
        s.get("A2")
        count_before = s.eval_count
        wb.undo()
        wb.redo()
        assert s.eval_count >= count_before


# ============================================================================
# G8: R21, R22, R23 — workbook and multi-sheet
# ============================================================================


class TestG8WorkbookMultiSheet:
    """R21: Workbook API; R22: qualifiers; R23: cross-sheet."""

    def test_r21_add_sheet(self):
        """R21: add_sheet creates sheet."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        assert wb.sheet_names == ["S1"]

    def test_r21_sheet(self):
        """R21: sheet returns handle."""
        wb = Workbook()
        wb.add_sheet("S1")
        s = wb.sheet("S1")
        assert s is not None

    def test_r21_sheet_invalid(self):
        """R21: sheet raises on unknown name."""
        wb = Workbook()
        with pytest.raises(ValueError):
            wb.sheet("NonExistent")

    def test_r22_qualified_ref(self):
        """R22: qualified reference."""
        wb = Workbook()
        s1 = wb.add_sheet("S1")
        s2 = wb.add_sheet("S2")
        s1.set("A1", 42)
        s2.set("A1", "=S1!A1")
        assert s2.get("A1") == 42

    def test_r23_cross_sheet_copy(self):
        """R23: copy to another sheet."""
        wb = Workbook()
        s1 = wb.add_sheet("S1")
        s2 = wb.add_sheet("S2")
        s1.set("A1", 1)
        s2.copy("S1!A1", "A1")
        assert s2.get("A1") == 1


# ============================================================================
# G9: R24, R25 — persistence round-trip
# ============================================================================


class TestG9Persistence:
    """R24: to_json/from_json; R25: round-trip equivalence."""

    def test_r24_to_json(self):
        """R24: to_json returns valid JSON."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 42)
        j = wb.to_json()
        data = json.loads(j)
        assert data["sheets"]["S1"]["cells"]["A1"] == 42

    def test_r24_from_json(self):
        """R24: from_json loads workbook."""
        j = '{"clock":0,"sheets":{"S1":{"cells":{"A1":42},"names":{}}}}'
        wb = Workbook.from_json(j)
        s = wb.sheet("S1")
        assert s.get("A1") == 42

    def test_r25_round_trip(self):
        """R25: round-trip preserves values."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 42)
        s.set("A2", "=A1+1")
        wb2 = Workbook.from_json(wb.to_json())
        s2 = wb2.sheet("S1")
        assert s2.get("A1") == 42
        assert s2.get("A2") == 43


# ============================================================================
# G10: R26, R27, R28 — volatile recalculation and XL bounds
# ============================================================================


class TestG10VolatileBounds:
    """R26: clock/NOW; R27: volatility; R28: bounds."""

    def test_r26_clock(self):
        """R26: clock starts at 0."""
        wb = Workbook()
        assert wb.clock == 0

    def test_r26_advance_clock(self):
        """R26: advance_clock increments."""
        wb = Workbook()
        assert wb.advance_clock() == 1
        assert wb.advance_clock() == 2

    def test_r26_now(self):
        """R26: NOW() returns clock."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=NOW()")
        assert s.get("A1") == 0
        wb.advance_clock()
        assert s.get("A1") == 1

    def test_r27_volatile_recompute(self):
        """R27: volatile cells recompute on clock change."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=NOW()")
        s.get("A1")
        assert s.eval_count == 1
        wb.advance_clock()
        s.get("A1")
        assert s.eval_count == 2  # Recomputed

    def test_r27_non_volatile_no_recompute(self):
        """R27: non-volatile cells don't recompute on clock change."""
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A2", "=A1+1")
        s.get("A2")
        assert s.eval_count == 1
        wb.advance_clock()
        s.get("A2")
        assert s.eval_count == 1  # Not recomputed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
