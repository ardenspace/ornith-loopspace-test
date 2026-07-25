"""Task 2.3: Lazy counters, caching, and single-sheet cycles — R9, R10."""
import pytest

from gridcalc import Workbook


# ---------------------------------------------------------------------------
# 1. eval_count starts at 0
# ---------------------------------------------------------------------------

class TestEvalCountInitial:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_eval_count_starts_at_zero(self):
        assert self.h.eval_count == 0


# ---------------------------------------------------------------------------
# 2. eval_count increments on formula evaluation
# ---------------------------------------------------------------------------

class TestEvalCountIncrement:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_literal_cell_does_not_increment(self):
        self.h.set("A1", 42)
        assert self.h.get("A1") == 42
        assert self.h.eval_count == 0

    def test_empty_cell_does_not_increment(self):
        assert self.h.get("Z99") is None
        assert self.h.eval_count == 0

    def test_formula_cell_increments_once(self):
        self.h.set("A1", 10)
        self.h.set("B1", "=A1+5")
        assert self.h.get("B1") == 15
        assert self.h.eval_count == 1

    def test_multiple_formula_cells_each_increment(self):
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        self.h.set("C1", "=B1+1")
        assert self.h.get("C1") == 3
        assert self.h.eval_count == 2  # B1 and C1 evaluated


# ---------------------------------------------------------------------------
# 3. Caching: consecutive get returns cached result with +0 delta
# ---------------------------------------------------------------------------

class TestCaching:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_consecutive_get_no_delta(self):
        self.h.set("A1", 10)
        self.h.set("B1", "=A1+5")
        self.h.get("B1")  # first get, eval_count becomes 1
        count_before = self.h.eval_count
        self.h.get("B1")  # second get, should be cached
        assert self.h.eval_count == count_before

    def test_get_after_edit_increments(self):
        self.h.set("A1", 10)
        self.h.set("B1", "=A1+5")
        self.h.get("B1")  # eval_count = 1
        self.h.set("A1", 20)  # invalidate cache
        self.h.get("B1")  # re-evaluate, eval_count = 2
        assert self.h.eval_count == 2
        assert self.h.get("B1") == 25


# ---------------------------------------------------------------------------
# 4. Cycle detection: direct cycle (A1 references A1)
# ---------------------------------------------------------------------------

class TestDirectCycle:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_direct_cycle_returns_cycle_error(self):
        self.h.set("A1", "=A1+1")
        result = self.h.get("A1")
        assert result == "#CYCLE!"

    def test_direct_cycle_increments_eval_count(self):
        self.h.set("A1", "=A1+1")
        self.h.get("A1")
        assert self.h.eval_count == 1  # started evaluation, detected cycle


# ---------------------------------------------------------------------------
# 5. Cycle detection: mutual cycle (A1 <-> B1)
# ---------------------------------------------------------------------------

class TestMutualCycle:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_mutual_cycle_both_return_cycle_error(self):
        self.h.set("A1", "=B1+1")
        self.h.set("B1", "=A1+1")
        assert self.h.get("A1") == "#CYCLE!"
        assert self.h.get("B1") == "#CYCLE!"

    def test_mutual_cycle_eval_count(self):
        self.h.set("A1", "=B1+1")
        self.h.set("B1", "=A1+1")
        self.h.get("A1")
        # Both A1 and B1 started evaluation, so eval_count = 2
        assert self.h.eval_count == 2


# ---------------------------------------------------------------------------
# 6. Cycle detection: dependent cycle (A1 -> B1 -> C1 -> A1)
# ---------------------------------------------------------------------------

class TestDependentCycle:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_dependent_cycle_all_return_cycle_error(self):
        self.h.set("A1", "=C1+1")
        self.h.set("B1", "=A1+1")
        self.h.set("C1", "=B1+1")
        assert self.h.get("A1") == "#CYCLE!"
        assert self.h.get("B1") == "#CYCLE!"
        assert self.h.get("C1") == "#CYCLE!"

    def test_dependent_cycle_eval_count(self):
        self.h.set("A1", "=C1+1")
        self.h.set("B1", "=A1+1")
        self.h.set("C1", "=B1+1")
        self.h.get("A1")
        # A1, B1, C1 all started evaluation
        assert self.h.eval_count == 3


# ---------------------------------------------------------------------------
# 7. Cells depending on cycle receive #CYCLE! by propagation
# ---------------------------------------------------------------------------

class TestCyclePropagation:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_cell_dependent_on_cycle_gets_cycle_error(self):
        self.h.set("A1", "=A1+1")  # cycle
        self.h.set("B1", "=A1+1")  # depends on cycle
        assert self.h.get("A1") == "#CYCLE!"
        assert self.h.get("B1") == "#CYCLE!"


# ---------------------------------------------------------------------------
# 8. Mutating operations do not evaluate or change eval_count
# ---------------------------------------------------------------------------

class TestMutatingOperations:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_set_does_not_increment(self):
        self.h.set("A1", 10)
        self.h.set("B1", "=A1+5")
        assert self.h.eval_count == 0

    def test_add_sheet_does_not_increment(self):
        self.wb.add_sheet("S2")
        assert self.h.eval_count == 0

    def test_undo_does_not_increment(self):
        self.h.set("A1", 10)
        initial_count = self.h.eval_count
        self.wb.undo()
        assert self.h.eval_count == initial_count

    def test_redo_does_not_increment(self):
        self.h.set("A1", 10)
        self.wb.undo()
        initial_count = self.h.eval_count
        self.wb.redo()
        assert self.h.eval_count == initial_count


# ---------------------------------------------------------------------------
# 9. Cache invalidation: set invalidates dependent formulas
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_set_invalidates_dependent_formula(self):
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        assert self.h.get("B1") == 2
        self.h.set("A1", 2)
        assert self.h.get("B1") == 3  # not stale 2

    def test_set_invalidates_chain(self):
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        self.h.set("C1", "=B1+1")
        assert self.h.get("C1") == 3
        self.h.set("A1", 10)
        assert self.h.get("C1") == 12  # not stale 3


# ---------------------------------------------------------------------------
# 10. eval_count counts formula computation starts, not references
# ---------------------------------------------------------------------------

class TestEvalCountSemantics:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_no_ref_formula_increments_once(self):
        """A formula with no references should increment eval_count by 1."""
        self.h.set("A1", "=1+2")
        assert self.h.get("A1") == 3
        assert self.h.eval_count == 1

    def test_multi_ref_formula_increments_once(self):
        """A formula with multiple literal references should increment by 1."""
        self.h.set("A1", 1)
        self.h.set("B1", 2)
        self.h.set("C1", "=A1+B1")
        assert self.h.get("C1") == 3
        assert self.h.eval_count == 1  # only C1 is a formula cell

    def test_error_result_counts_same(self):
        """Error results (#DIV!) should count the same as values."""
        self.h.set("A1", "=1/0")
        assert self.h.get("A1") == "#DIV!"
        assert self.h.eval_count == 1

    def test_cycle_result_counts_same(self):
        """Cycle results (#CYCLE!) should count the same as values."""
        self.h.set("A1", "=A1+1")
        assert self.h.get("A1") == "#CYCLE!"
        assert self.h.eval_count == 1


# ---------------------------------------------------------------------------
# 11. Cached error results return strings, not _ErrorValue objects
# ---------------------------------------------------------------------------

class TestCachedErrorType:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_cached_div_error_returns_string(self):
        self.h.set("A1", "=1/0")
        result1 = self.h.get("A1")
        result2 = self.h.get("A1")
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert result1 == "#DIV!"
        assert result2 == "#DIV!"

    def test_cached_cycle_error_returns_string(self):
        self.h.set("A1", "=A1+1")
        result1 = self.h.get("A1")
        result2 = self.h.get("A1")
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert result1 == "#CYCLE!"
        assert result2 == "#CYCLE!"
