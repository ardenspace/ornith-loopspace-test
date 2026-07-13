"""Task 4.2: Dependency graph + dirty propagation per R10, R11."""
import pytest
from gridcalc import Sheet


class TestIrrelevantEdit:
    """Irrelevant edit: set(Y) with Y outside X's reference closure, then get(X) adds 0."""

    def test_irrelevant_edit_adds_zero(self):
        """Set outside closure doesn't trigger re-evaluation."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        # Set C1 (outside B1's closure)
        s.set("C1", 100)
        # Get B1 should add 0
        s.get("B1")
        assert s.eval_count == 1
        assert s.get("B1") == 2

    def test_irrelevant_edit_distinct_cells(self):
        """Set on completely unrelated cell doesn't affect evaluation."""
        s = Sheet()
        s.set("A1", 5)
        s.set("Z99", "=A1*2")
        s.get("Z99")
        assert s.eval_count == 1
        # Set A2 (not in Z99's closure)
        s.set("A2", 10)
        s.get("Z99")
        assert s.eval_count == 1
        assert s.get("Z99") == 10


class TestRelevantEdit:
    """Relevant edit: set(Y) with Y inside closure, then get(X) adds ≥1 and at most closure size."""

    def test_relevant_edit_self_reference(self):
        """set(X, ...) then get(X) adds at least 1."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        # Set B1 itself (inside its own closure)
        s.set("B1", "=A1+2")
        s.get("B1")
        assert s.eval_count == 2
        assert s.get("B1") == 3

    def test_relevant_edit_dependency(self):
        """set(Y) where Y is referenced by X triggers re-evaluation of X."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        # Set A1 (inside B1's closure)
        s.set("A1", 10)
        s.get("B1")
        assert s.eval_count == 2
        assert s.get("B1") == 11

    def test_relevant_edit_upper_bound(self):
        """Relevant edit adds at most the number of formula cells in closure."""
        s = Sheet()
        # Chain: A1 (literal) → B1 → C1 → D1
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.set("C1", "=B1+1")
        s.set("D1", "=C1+1")
        s.get("D1")
        # D1, C1, B1 are formulas (count=3); A1 is literal (no increment)
        assert s.eval_count == 3
        # Set A1 (inside D1's closure)
        s.set("A1", 10)
        s.get("D1")
        # D1's closure is {D1, C1, B1, A1}; formula cells are D1, C1, B1 (3 cells)
        # So delta should be at most 3
        delta = s.eval_count - 3
        assert 1 <= delta <= 3
        assert s.get("D1") == 13

    def test_formula_cell_outside_closure_not_recomputed(self):
        """A formula cell outside the closure is never recomputed."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.set("C1", 100)  # Literal
        s.set("D1", "=C1+1")  # D1 depends on C1, not A1 or B1
        s.get("B1")
        s.get("D1")
        assert s.eval_count == 2
        # Set A1 (inside B1's closure, outside D1's closure)
        s.set("A1", 10)
        s.get("B1")
        # B1 re-evaluates (count=3), D1 should NOT re-evaluate
        assert s.eval_count == 3
        assert s.get("D1") == 101  # Unchanged


class TestClosureSemantics:
    """Closure semantics: range members count, invalid range contributes no members, #PARSE! is itself."""

    def test_range_members_in_closure(self):
        """Range members are in the closure (even empty cells)."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", 2)
        s.set("A3", 3)
        s.set("B1", "=SUM(A1:A3)")
        s.get("B1")
        # B1 is formula (count=1); A1, A2, A3 are literals (no increment)
        assert s.eval_count == 1
        # Set A2 (inside B1's closure via range)
        s.set("A2", 20)
        s.get("B1")
        # B1 re-evaluates (count=2)
        assert s.eval_count == 2
        assert s.get("B1") == 24

    def test_empty_cell_in_range_in_closure(self):
        """Empty cells in a range are in the closure."""
        s = Sheet()
        s.set("A1", 1)
        # A2 is empty
        s.set("A3", 3)
        s.set("B1", "=SUM(A1:A3)")
        s.get("B1")
        # B1 is formula (count=1); A1, A3 are literals (no increment); A2 is empty
        assert s.eval_count == 1
        # Set A2 (empty → now has value, inside closure)
        s.set("A2", 20)
        s.get("B1")
        # B1 re-evaluates (count=2)
        assert s.eval_count == 2
        assert s.get("B1") == 24

    def test_invalid_range_contributes_no_members(self):
        """Invalid range (mis-ordered) contributes no members to closure."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=SUM(B2:A1)")  # Mis-ordered range → #REF!
        s.get("B1")
        assert s.eval_count == 1  # Only B1 evaluated
        # B1's closure should be just {B1} (invalid range contributes nothing)
        # Set A1 (outside B1's closure)
        s.set("A1", 10)
        s.get("B1")
        assert s.eval_count == 1  # No re-evaluation
        assert s.get("B1") == "#REF!"

    def test_parse_error_closure_is_self(self):
        """A #PARSE! formula's closure is just itself."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=INVALID(A1)")  # #PARSE!
        s.get("B1")
        assert s.eval_count == 1
        # B1's closure is just {B1}
        # Set A1 (outside B1's closure)
        s.set("A1", 10)
        s.get("B1")
        assert s.eval_count == 1  # No re-evaluation
        assert s.get("B1") == "#PARSE!"

    def test_edit_leaving_literal_adds_zero(self):
        """An edit that leaves X literal/empty makes the final get add 0."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        # Set B1 to a literal (leaves it non-formula)
        s.set("B1", 100)
        s.get("B1")
        assert s.eval_count == 1  # No evaluation (literal)
        assert s.get("B1") == 100


class TestIdenticalContentEdit:
    """A set writing identical content still counts as an edit (≥1 on next dependent get)."""

    def test_identical_content_still_triggers_recompute(self):
        """set(X, same_value) still triggers re-evaluation of dependents."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        # Set A1 to the same value
        s.set("A1", 1)
        s.get("B1")
        assert s.eval_count == 2  # Re-evaluation triggered
        assert s.get("B1") == 2

    def test_identical_formula_still_triggers_recompute(self):
        """Setting a formula to its current value still triggers re-evaluation."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        # Set B1 to the same formula
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 2  # Re-evaluation triggered
        assert s.get("B1") == 2


class TestAllPriorTestsStillGreen:
    """Verify all phase 1-3 and 4.1 tests still pass (sanity check)."""

    def test_phase1_address_validation(self):
        """Basic address validation still works."""
        s = Sheet()
        s.set("A1", 1)
        assert s.get("A1") == 1
        with pytest.raises(ValueError):
            s.get("a1")
        with pytest.raises(ValueError):
            s.get("A0")

    def test_phase2_formula_evaluation(self):
        """Basic formula evaluation still works."""
        s = Sheet()
        s.set("A1", 2)
        s.set("B1", "=A1*3+1")
        assert s.get("B1") == 7

    def test_phase3_function_evaluation(self):
        """Function evaluation still works."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", 2)
        s.set("A3", 3)
        s.set("B1", "=SUM(A1:A3)")
        assert s.get("B1") == 6

    def test_phase3_cycle_detection(self):
        """Cycle detection still works."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        assert s.get("A1") == "#CYCLE!"
        assert s.get("A2") == "#CYCLE!"

    def test_phase4_counter_basics(self):
        """Basic eval_count behavior still works."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.get("B1")
        assert s.eval_count == 1
        s.get("B1")
        assert s.eval_count == 1  # Cached
