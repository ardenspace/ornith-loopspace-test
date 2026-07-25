"""Task 6.3: Named ranges and name invalidation — R18, R19 tests."""

import pytest

from gridcalc import Workbook
from gridcalc.formula import NAME_ERROR, REF_ERROR
from tests.reference_model import NaiveSheet, _ref_tokenize, _ref_parse_expr, _ref_evaluate, _ref_is_error


def _sheet():
    wb = Workbook()
    return wb, wb.add_sheet("S1")


# ---------------------------------------------------------------------------
# 1. Name validation
# ---------------------------------------------------------------------------

class TestNameValidation:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_valid_name_definition(self):
        """A valid name should be defined successfully."""
        result = self.h.define_name("MYRANGE", "A1")
        assert result is None
        assert self.h._names == {"MYRANGE": "A1"}

    def test_name_too_short(self):
        """Names must be at least 2 characters."""
        with pytest.raises(ValueError):
            self.h.define_name("A", "A1")

    def test_name_too_long(self):
        """Names must be at most 32 characters."""
        with pytest.raises(ValueError):
            self.h.define_name("A" * 33, "A1")

    def test_name_starts_with_digit(self):
        """Names must start with a letter or underscore."""
        with pytest.raises(ValueError):
            self.h.define_name("1abc", "A1")

    def test_name_contains_invalid_chars(self):
        """Names can only contain A-Z, 0-9, and underscore."""
        with pytest.raises(ValueError):
            self.h.define_name("my-range", "A1")

    def test_name_rejects_lowercase_letters(self):
        """Name syntax is uppercase letters, digits, and underscore only."""
        for name in ("AAa", "aA", "A_a"):
            with pytest.raises(ValueError):
                self.h.define_name(name, "A1")

    def test_name_is_ref_shaped(self):
        """Names that look like cell addresses are invalid."""
        with pytest.raises(ValueError):
            self.h.define_name("A1", "A1")
        with pytest.raises(ValueError):
            self.h.define_name("Z99", "A1")

    def test_ref_shaped_name_outside_grid_is_invalid_without_state_change(self):
        self.h.define_name("OLDNAME", "A1")
        before_names = dict(self.h._names)
        before_journal = list(self.wb._journal)

        with pytest.raises(ValueError):
            self.h.define_name("A100", "A1")

        assert self.h._names == before_names
        assert self.wb._journal == before_journal

    def test_name_is_function_name(self):
        """Names cannot be function names."""
        for func_name in ["SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW"]:
            with pytest.raises(ValueError):
                self.h.define_name(func_name, "A1")

    def test_name_case_insensitive_function_check(self):
        """Function name check should be case-insensitive."""
        with pytest.raises(ValueError):
            self.h.define_name("sum", "A1")
        with pytest.raises(ValueError):
            self.h.define_name("Sum", "A1")

    def test_name_with_underscore(self):
        """Names can start with underscore."""
        result = self.h.define_name("_PRIVATE", "A1")
        assert result is None

    def test_underscore_digit_name_is_valid(self):
        result = self.h.define_name("_1", "A1")
        assert result is None

    def test_name_with_digits(self):
        """Names can contain digits after first character."""
        result = self.h.define_name("RANGE1", "A1")
        assert result is None


# ---------------------------------------------------------------------------
# 2. Target validation
# ---------------------------------------------------------------------------

class TestTargetValidation:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_valid_address_target(self):
        """A valid address should be accepted as target."""
        result = self.h.define_name("MYCELL", "A1")
        assert result is None

    def test_valid_range_target(self):
        """A valid range should be accepted as target."""
        result = self.h.define_name("MYRANGE", "A1:B2")
        assert result is None

    def test_invalid_address_target(self):
        """Invalid address should raise ValueError."""
        with pytest.raises(ValueError):
            self.h.define_name("BAD", "Z100")

    def test_misordered_range_target(self):
        """Range with start > end should raise ValueError."""
        with pytest.raises(ValueError):
            self.h.define_name("BAD", "B2:A1")

    def test_non_string_name(self):
        """Non-string name should raise ValueError."""
        with pytest.raises(ValueError):
            self.h.define_name(123, "A1")

    def test_non_string_target(self):
        """Non-string target should raise ValueError."""
        with pytest.raises(ValueError):
            self.h.define_name("MYRANGE", 123)

    def test_failed_define_leaves_binding_and_journal_unchanged(self):
        self.h.define_name("MYCELL", "A1")
        before_names = dict(self.h._names)
        before_journal = list(self.wb._journal)

        with pytest.raises(ValueError):
            self.h.define_name("MYCELL", "B2:A1")

        assert self.h._names == before_names
        assert self.wb._journal == before_journal

    def test_absolute_target_is_invalid(self):
        with pytest.raises(ValueError):
            self.h.define_name("MYCELL", "$A$1")

    def test_failed_define_does_not_journal(self):
        """Failed define_name should not be journaled."""
        with pytest.raises(ValueError):
            self.h.define_name("A", "A1")  # too short
        # Only add_sheet is journaled
        assert len(self.wb._journal) == 1

    @pytest.mark.parametrize(
        "name,target",
        [
            ("A", "A1"),
            ("SUM", "A1"),
            ("A1", "A1"),
            (123, "A1"),
            ("MYCELL", 123),
            ("MYCELL", "Z100"),
            ("MYCELL", "B2:A1"),
        ],
    )
    def test_each_invalid_define_class_leaves_names_and_journal_unchanged(self, name, target):
        self.h.define_name("OLDNAME", "A1")
        before_names = dict(self.h._names)
        before_journal = list(self.wb._journal)

        with pytest.raises(ValueError):
            self.h.define_name(name, target)

        assert self.h._names == before_names
        assert self.wb._journal == before_journal


# ---------------------------------------------------------------------------
# 3. NAME as primary in formulas
# ---------------------------------------------------------------------------

class TestNameAsPrimary:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_single_cell_target_returns_typed_value(self):
        """A single-cell name should return the cell's typed value."""
        self.h.set("A1", 42)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 42

    def test_undefined_name_returns_name_error(self):
        """An undefined name should return #NAME!."""
        self.h.set("A1", "=UNDEFINEDNAME")
        assert self.h.get("A1") == NAME_ERROR

    def test_range_target_as_primary_returns_ref_error(self):
        """A range name used as primary should return #REF!."""
        self.h.set("A1", 1)
        self.h.set("B1", 2)
        self.h.define_name("MYRANGE", "A1:B1")
        self.h.set("C1", "=MYRANGE")
        assert self.h.get("C1") == REF_ERROR

    def test_one_by_one_range_primary_returns_typed_value(self):
        self.h.set("A1", "text")
        self.h.define_name("MYRANGE", "A1:A1")
        self.h.set("B1", "=MYRANGE")
        assert self.h.get("B1") == "text"

    def test_name_in_arithmetic(self):
        """A name should work in arithmetic expressions."""
        self.h.set("A1", 10)
        self.h.define_name("XX", "A1")
        self.h.set("B1", "=XX + 5")
        assert self.h.get("B1") == 15

    def test_underscore_digit_name_returns_typed_value(self):
        self.h.set("A1", 9)
        self.h.define_name("_1", "A1")
        self.h.set("B1", "=_1")

        assert self.h.get("B1") == 9


# ---------------------------------------------------------------------------
# 4. NAME as RANGE-ARG in formulas
# ---------------------------------------------------------------------------

class TestNameAsRangeArg:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_range_name_in_sum(self):
        """A range name should work as argument to SUM."""
        self.h.set("A1", 1)
        self.h.set("A2", 2)
        self.h.set("A3", 3)
        self.h.define_name("MYRANGE", "A1:A3")
        self.h.set("B1", "=SUM(MYRANGE)")
        assert self.h.get("B1") == 6

    def test_range_name_in_min_max(self):
        """A range name should work as argument to MIN/MAX."""
        self.h.set("A1", 5)
        self.h.set("A2", 2)
        self.h.set("A3", 8)
        self.h.define_name("MYRANGE", "A1:A3")
        self.h.set("B1", "=MIN(MYRANGE)")
        self.h.set("B2", "=MAX(MYRANGE)")
        assert self.h.get("B1") == 2
        assert self.h.get("B2") == 8

    def test_single_cell_name_in_count_is_one_by_one_range(self):
        self.h.set("A1", "x")
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=COUNT(MYCELL)")
        assert self.h.get("B1") == 1

    def test_undefined_name_range_argument_returns_name_error(self):
        self.h.set("A1", "=SUM(MISSINGNAME)")
        assert self.h.get("A1") == NAME_ERROR

    def test_underscore_digit_name_as_range_argument(self):
        self.h.set("A1", 4)
        self.h.define_name("_1", "A1")
        self.h.set("B1", "=SUM(_1)")

        assert self.h.get("B1") == 4


# ---------------------------------------------------------------------------
# 5. Redefinition
# ---------------------------------------------------------------------------

class TestRedefinition:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_redefine_changes_binding(self):
        """Redefining a name should change its binding."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 10

        self.h.define_name("MYCELL", "B1")
        assert self.h.get("C1") == 20

    def test_redefine_invalidates_formula_cells(self):
        """Redefining a name should invalidate formula cells that use it."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 10

        # Redefine even to the same target should invalidate
        self.h.define_name("MYCELL", "A1")
        assert self.h.get("C1") == 10

    def test_redefine_journals(self):
        """Redefining a name should be journaled."""
        self.h.define_name("MYCELL", "A1")
        self.h.define_name("MYCELL", "B1")
        # Should have 2 define_name entries (plus add_sheet)
        assert len(self.wb._journal) == 3

    def test_redefine_never_evaluates_formulas(self):
        """define_name should never evaluate formulas."""
        self.h.set("A1", 10)
        self.h.set("B1", "=A1+1")
        before = self.h.eval_count
        self.h.define_name("MYCELL", "A1")
        assert self.h.eval_count == before

    def test_identical_redefine_invalidates_transitive_dependents(self):
        self.h.set("A1", 1)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        self.h.set("C1", "=B1+1")
        assert self.h.get("C1") == 2
        self.h.set("A1", 2)
        assert self.h.get("C1") == 3
        self.h._cells["A1"] = 3

        self.h.define_name("MYCELL", "A1")

        assert self.h.get("C1") == 4


# ---------------------------------------------------------------------------
# 6. Undo/redo
# ---------------------------------------------------------------------------

class TestUndoRedo:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_undo_undoes_define(self):
        """Undo should revert a define_name."""
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 0  # A1 is empty

        self.wb.undo()  # Undo the set
        self.wb.undo()  # Undo the define_name
        # Name should be undefined again; B1 cell also removed
        assert self.h.get("B1") is None
        assert "MYCELL" not in self.h._names

    def test_redo_reapplies_define(self):
        """Redo should reapply a define_name."""
        self.h.set("A1", 42)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 42

        self.wb.undo()
        self.wb.redo()
        assert self.h.get("B1") == 42

    def test_undo_restores_previous_binding(self):
        """Undo should restore the previous binding."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.define_name("MYCELL", "B1")

        self.wb.undo()
        # Should be back to A1
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 10

    def test_undo_redo_redefinition_restores_and_reapplies_previous_binding(self):
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 10

        self.h.define_name("MYCELL", "B1")
        assert self.h.get("C1") == 20

        assert self.wb.undo() is True
        assert self.h.get("C1") == 10

        assert self.wb.redo() is True
        assert self.h.get("C1") == 20

    def test_undo_undefined_name(self):
        """Undo should handle undoing a name that was previously undefined."""
        self.h.set("A1", 42)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 42

        self.wb.undo()  # Undo the set
        self.wb.undo()  # Undo the define_name
        # Now MYCELL is undefined
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == NAME_ERROR

    def test_failed_define_does_not_journal(self):
        """Failed define_name should not be journaled."""
        with pytest.raises(ValueError):
            self.h.define_name("A", "A1")  # too short

        # Only add_sheet is journaled
        assert len(self.wb._journal) == 1

    def test_new_operation_clears_redo(self):
        """A new journaled operation should clear the redo stack."""
        self.h.define_name("MYCELL", "A1")
        self.wb.undo()  # Undo the define_name
        # Redo should work
        assert self.wb.redo() is True
        # Now define again (this should clear the redo stack)
        self.h.define_name("MYCELL", "B1")
        # Redo should be cleared
        assert self.wb.redo() is False

    def test_undo_immediately_after_define_restores_undefined_and_redo_reapplies(self):
        self.h.set("A1", 7)
        self.h.define_name("MYCELL", "A1")

        assert self.wb.undo() is True
        assert "MYCELL" not in self.h._names

        assert self.wb.redo() is True
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 7


# ---------------------------------------------------------------------------
# 7. Cache invalidation
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_redefine_invalidates_dependent_formulas(self):
        """Redefining a name should invalidate dependent formula cells."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 10

        # Redefine to B1
        self.h.define_name("MYCELL", "B1")
        assert self.h.get("C1") == 20

    def test_redefine_invalidates_every_cached_formula_that_mentions_name(self):
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.set("C1", "=MYCELL")
        self.h.set("D1", "=MYCELL+1")
        assert self.h.get("C1") == 10
        assert self.h.get("D1") == 11

        self.h.define_name("MYCELL", "B1")

        assert self.h.get("C1") == 20
        assert self.h.get("D1") == 21

    def test_set_dependent_cell_invalidates_formula(self):
        """Setting a cell that a name points to should invalidate the formula."""
        self.h.set("A1", 10)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 10

        # Change A1
        self.h.set("A1", 20)
        assert self.h.get("B1") == 20


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_multiple_names(self):
        """Multiple names can be defined."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("XX", "A1")
        self.h.define_name("YY", "B1")
        self.h.set("C1", "=XX + YY")
        assert self.h.get("C1") == 30

    def test_name_on_different_sheet(self):
        """Names are per-sheet."""
        wb = Workbook()
        s1 = wb.add_sheet("S1")
        s2 = wb.add_sheet("S2")
        s1.set("A1", 10)
        s1.define_name("MYCELL", "A1")
        # s2 should not have access to s1's names
        s2.set("B1", "=MYCELL")
        assert s2.get("B1") == NAME_ERROR

    def test_public_cell_apis_reject_absolute_addresses(self):
        self.h.set("A1", 1)
        self.h.set("B1", "old")
        before = dict(self.h._cells)
        before_journal = list(self.wb._journal)

        for call in (
            lambda: self.h.set("$A$1", 2),
            lambda: self.h.get("$A$1"),
            lambda: self.h.copy("$A$1", "C1"),
            lambda: self.h.copy("A1", "$C$1"),
        ):
            with pytest.raises(ValueError):
                call()

        assert self.h._cells == before
        assert self.wb._journal == before_journal


# ---------------------------------------------------------------------------
# 9. Directed equivalence tests with naive reference model
# ---------------------------------------------------------------------------

class TestDirectedEquivalence:
    """Compare actual implementation against naive reference model."""

    def test_single_cell_name_equivalence(self):
        """Single-cell name should resolve identically in both models."""
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 42)
        sh.define_name("MYCELL", "A1")
        sh.set("B1", "=MYCELL")
        actual_result = sh.get("B1")

        ref = NaiveSheet()
        ref.set("A1", 42)
        ref.define_name("MYCELL", "A1")
        ref.set("B1", "=MYCELL")
        ref_result = ref.get("B1")

        assert actual_result == ref_result

    def test_undefined_name_equivalence(self):
        """Undefined name should return #NAME! in both models."""
        # Actual implementation
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=UNDEFINEDNAME")
        actual_result = sh.get("A1")

        # Reference model
        ref = NaiveSheet()
        ref.set("A1", "=UNDEFINEDNAME")
        ref_result = ref.get("A1")

        assert actual_result == ref_result

    def test_range_name_as_primary_equivalence(self):
        """Range name used as primary should return #REF! in both models."""
        # Actual implementation
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.define_name("MYRANGE", "A1:B1")
        sh.set("C1", "=MYRANGE")
        actual_result = sh.get("C1")

        # Reference model
        ref = NaiveSheet()
        ref.set("A1", 1)
        ref.set("B1", 2)
        ref.define_name("MYRANGE", "A1:B1")
        ref.set("C1", "=MYRANGE")
        ref_result = ref.get("C1")

        # Both should return #REF!
        assert actual_result == REF_ERROR
        assert ref_result == REF_ERROR

    def test_name_in_arithmetic_equivalence(self):
        """Name in arithmetic should resolve identically in both models."""
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.define_name("XX", "A1")
        sh.set("B1", "=XX + 5")
        actual_result = sh.get("B1")

        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.define_name("XX", "A1")
        ref.set("B1", "=XX + 5")
        ref_result = ref.get("B1")

        assert actual_result == ref_result

    def test_range_name_in_sum_equivalence(self):
        """Range name in SUM should resolve identically in both models."""
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 1)
        sh.set("A2", 2)
        sh.set("A3", 3)
        sh.define_name("MYRANGE", "A1:A3")
        sh.set("B1", "=SUM(MYRANGE)")
        actual_result = sh.get("B1")

        ref = NaiveSheet()
        ref.set("A1", 1)
        ref.set("A2", 2)
        ref.set("A3", 3)
        ref.define_name("MYRANGE", "A1:A3")
        ref.set("B1", "=SUM(MYRANGE)")
        ref_result = ref.get("B1")

        assert actual_result == ref_result

    def test_redefine_changes_binding_equivalence(self):
        """Redefining a name should change its binding in both models."""
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.set("B1", 20)
        sh.define_name("MYCELL", "A1")
        sh.set("C1", "=MYCELL")
        actual_result_before = sh.get("C1")
        sh.define_name("MYCELL", "B1")
        actual_result_after = sh.get("C1")

        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.set("B1", 20)
        ref.define_name("MYCELL", "A1")
        ref.set("C1", "=MYCELL")
        ref_result_before = ref.get("C1")
        ref.define_name("MYCELL", "B1")
        ref_result_after = ref.get("C1")

        assert actual_result_before == ref_result_before
        assert actual_result_after == ref_result_after

    def test_multiple_names_equivalence(self):
        """Multiple names should resolve identically in both models."""
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.set("B1", 20)
        sh.define_name("XX", "A1")
        sh.define_name("YY", "B1")
        sh.set("C1", "=XX + YY")
        actual_result = sh.get("C1")

        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.set("B1", 20)
        ref.define_name("XX", "A1")
        ref.define_name("YY", "B1")
        ref.set("C1", "=XX + YY")
        ref_result = ref.get("C1")

        assert actual_result == ref_result

    def test_name_on_different_sheet_equivalence(self):
        """Names are per-sheet and should not leak between sheets."""
        # Actual implementation
        wb = Workbook()
        s1 = wb.add_sheet("S1")
        s2 = wb.add_sheet("S2")
        s1.set("A1", 10)
        s1.define_name("MYCELL", "A1")
        s2.set("B1", "=MYCELL")
        actual_result = s2.get("B1")

        # Reference model
        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.set("B1", "=MYCELL")
        ref_result = ref.get("B1")

        assert actual_result == ref_result

    def test_copy_with_name_stays_same_within_sheet(self):
        """Copy within same sheet should not rewrite name tokens."""
        # Actual implementation
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.define_name("MYCELL", "A1")
        sh.set("B1", "=MYCELL")
        sh.copy("B1", "C1")

        # Name should not be rewritten during copy within same sheet
        assert sh._cells["C1"] == "=MYCELL"
        assert sh.get("C1") == 10

    def test_copy_with_absolute_refs_and_name(self):
        """Copy should rewrite absolute refs but leave names unchanged."""
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.define_name("MYCELL", "A1")
        sh.set("B1", "=A1 + $A$1 + MYCELL")
        sh.copy("B1", "C2")

        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.define_name("MYCELL", "A1")
        ref.set("B1", "=A1 + $A$1 + MYCELL")
        ref.copy("B1", "C2")

        assert sh._cells["C2"] == ref._cells["C2"]
        assert sh.get("C2") == ref.get("C2")

    def test_named_range_copy_with_mixed_absolute_refs_equivalence(self):
        wb = Workbook()
        sh = wb.add_sheet("S1")
        ref = NaiveSheet()
        for sheet in (sh, ref):
            sheet.set("A1", 2)
            sheet.set("A2", 3)
            sheet.set("B1", 5)
            sheet.define_name("MYCELL", "A1")
            sheet.define_name("MYRANGE", "A1:B1")
            sheet.set("B2", "=$A1+A$1+MYCELL+SUM(MYRANGE)")

        sh.copy("B2", "C3")
        ref.copy("B2", "C3")

        assert sh._cells["C3"] == ref._cells["C3"] == "=$A2+B$1+MYCELL+SUM(MYRANGE)"
        assert sh.get("C3") == ref.get("C3") == 17

    def test_absolute_target_invalid_in_actual_and_reference_models(self):
        wb = Workbook()
        sh = wb.add_sheet("S1")
        ref = NaiveSheet()

        with pytest.raises(ValueError):
            sh.define_name("MYCELL", "$A$1")
        with pytest.raises(ValueError):
            ref.define_name("MYCELL", "$A$1")

    def test_copy_rewrites_refs_and_keeps_names_equivalence(self):
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.define_name("MYCELL", "A1")
        sh.set("B1", "=A1+$A$1+MYCELL")
        sh.copy("B1", "C2")

        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.define_name("MYCELL", "A1")
        ref.set("B1", "=A1+$A$1+MYCELL")

        ref.copy("B1", "C2")

        assert sh._cells["C2"] == ref._cells["C2"]
        assert sh.get("C2") == ref.get("C2")

    def test_copy_out_of_bounds_ref_token_equivalence(self):
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=A99")
        sh.copy("A1", "A2")

        ref = NaiveSheet()
        ref.set("A1", "=A99")
        ref.copy("A1", "A2")

        assert sh._cells["A2"] == ref._cells["A2"]
        assert sh.get("A2") == ref.get("A2") == REF_ERROR

    def test_copy_existing_ref_error_token_equivalence(self):
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 10)
        sh.set("B1", "=#REF!+A1")
        sh.copy("B1", "C2")

        ref = NaiveSheet()
        ref.set("A1", 10)
        ref.set("B1", "=#REF!+A1")
        ref.copy("B1", "C2")

        assert sh._cells["C2"] == ref._cells["C2"]
        assert sh.get("C2") == ref.get("C2") == REF_ERROR

    def test_reference_model_named_range_argument(self):
        ref = NaiveSheet()
        ref.set("A1", 1)
        ref.set("A2", 2)
        ref.define_name("MYRANGE", "A1:A2")
        ref.set("B1", "=SUM(MYRANGE)")

        assert ref.get("B1") == 3

    def test_underscore_digit_name_equivalence(self):
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 6)
        sh.define_name("_1", "A1")
        sh.set("B1", "=_1")

        ref = NaiveSheet()
        ref.set("A1", 6)
        ref.define_name("_1", "A1")
        ref.set("B1", "=_1")

        assert sh.get("B1") == ref.get("B1") == 6
