"""Task 4.1: Lazy evaluation, result caching, eval_count."""
import pytest
from gridcalc import Sheet


class TestEvalCountBasics:
    """Tests for eval_count property per R10."""

    def test_eval_count_starts_at_zero(self):
        """eval_count is 0 on a fresh sheet."""
        s = Sheet()
        assert s.eval_count == 0

    def test_eval_count_increments_for_formula(self):
        """eval_count increments by 1 when a formula is evaluated."""
        s = Sheet()
        s.set("A1", "=1+2")
        s.get("A1")
        assert s.eval_count == 1

    def test_eval_count_does_not_change_on_set(self):
        """set() never changes eval_count."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1")
        assert s.eval_count == 0
        s.get("B1")
        assert s.eval_count == 1
        # set after eval should not change count
        s.set("A1", 10)
        assert s.eval_count == 1

    def test_eval_count_does_not_increment_for_literals(self):
        """Reading a literal cell doesn't increment eval_count."""
        s = Sheet()
        s.set("A1", 42)
        s.get("A1")
        assert s.eval_count == 0

    def test_eval_count_does_not_increment_for_empty(self):
        """Reading an empty cell doesn't increment eval_count."""
        s = Sheet()
        s.get("A1")
        assert s.eval_count == 0


class TestCaching:
    """Tests for result caching."""

    def test_repeat_get_returns_cached(self):
        """Repeat get() returns cached result without re-evaluation."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        first_count = s.eval_count
        s.get("B1")
        assert s.eval_count == first_count

    def test_set_invalidates_cache(self):
        """After set(), subsequent get() re-evaluates."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        s.set("A1", 10)
        s.get("B1")
        assert s.eval_count == 2
        assert s.get("B1") == 11

    def test_error_results_are_cached(self):
        """Error results are cached like values."""
        s = Sheet()
        s.set("A1", "=1/0")
        s.get("A1")
        first_count = s.eval_count
        s.get("A1")
        assert s.eval_count == first_count
        assert s.get("A1") == "#DIV!"

    def test_cycle_result_is_cached(self):
        """#CYCLE! results are cached."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        s.get("A1")
        first_count = s.eval_count
        s.get("A1")
        assert s.eval_count == first_count
        assert s.get("A1") == "#CYCLE!"


class TestShortCircuit:
    """Tests for counter-visible short-circuit per R5."""

    def test_short_circuit_division_by_zero(self):
        """'=1/0+Y1' never starts Y1's computation."""
        s = Sheet()
        s.set("A1", 1)
        s.set("Y1", "=A1*2")
        s.set("B1", "=1/0+Y1")
        s.get("B1")
        # B1's evaluation starts (count=1), Y1 is never evaluated
        assert s.eval_count == 1
        assert s.get("B1") == "#DIV!"

    def test_short_circuit_left_error(self):
        """If left operand is error, right operand is not evaluated."""
        s = Sheet()
        s.set("A1", "=1/0")  # #DIV!
        s.set("B1", 10)
        s.set("C1", "=A1+B1")
        s.get("C1")
        # C1 evaluates (count=1), A1 evaluates (count=2), B1 is never evaluated
        assert s.eval_count == 2
        assert s.get("C1") == "#DIV!"


class TestRangeSemantics:
    """Tests for counter-visible range semantics per R7, R8."""

    def test_sum_short_circuits_on_first_error(self):
        """SUM stops evaluating after first error in range."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "=1/0")  # #DIV!
        s.set("A3", 3)  # Never evaluated
        s.set("B1", "=SUM(A1:A3)")
        s.get("B1")
        # B1 evaluates (count=1), A2 evaluates (count=2), A3 never evaluated
        assert s.eval_count == 2
        assert s.get("B1") == "#DIV!"

    def test_count_does_not_evaluate_range_members(self):
        """COUNT doesn't evaluate range members, doesn't increment eval_count for them."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "=1/0")  # Would be #DIV! if evaluated
        s.set("A3", "=2+2")  # Would be 4 if evaluated
        s.set("B1", "=COUNT(A1:A3)")
        s.get("B1")
        # B1 evaluates (count=1), but A1, A2, A3 are NOT evaluated (COUNT is structural)
        assert s.eval_count == 1
        assert s.get("B1") == 3

    def test_count_with_formula_cells(self):
        """COUNT counts formula cells without evaluating them."""
        s = Sheet()
        s.set("A1", "=1+2")
        s.set("B1", "=3+4")
        s.set("C1", "=COUNT(A1:B1)")
        s.get("C1")
        # C1 evaluates (count=1), A1 and B1 are NOT evaluated
        assert s.eval_count == 1
        assert s.get("C1") == 2

    def test_min_short_circuits_on_first_error(self):
        """MIN stops evaluating after first error in range."""
        s = Sheet()
        s.set("A1", 5)
        s.set("A2", "hello")  # #TYPE!
        s.set("A3", 3)  # Never evaluated
        s.set("B1", "=MIN(A1:A3)")
        s.get("B1")
        # B1 evaluates (count=1), A2 is literal "hello" (no increment), A3 never evaluated
        # A2 is a literal string, not a formula, so it doesn't increment eval_count
        # But it IS an error in the range, so MIN returns #TYPE!
        assert s.eval_count == 1
        assert s.get("B1") == "#TYPE!"

    def test_max_short_circuits_on_first_error(self):
        """MAX stops evaluating after first error in range."""
        s = Sheet()
        s.set("A1", 5)
        s.set("A2", "=1/0")  # #DIV!
        s.set("A3", 3)  # Never evaluated
        s.set("B1", "=MAX(A1:A3)")
        s.get("B1")
        # B1 evaluates (count=1), A2 evaluates (count=2), A3 never evaluated
        assert s.eval_count == 2
        assert s.get("B1") == "#DIV!"
