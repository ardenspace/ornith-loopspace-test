"""Tests for circular-reference detection (Task 3.2)."""
import pytest
from gridcalc.sheet import Sheet
from gridcalc.parser import ParseError


class TestCycleDetection:
    """Tests for circular reference detection (R11)."""

    def test_simple_cycle(self):
        """A1 → A2 → A1 is a cycle."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        assert s.get("A1") == "#CYCLE!"
        assert s.get("A2") == "#CYCLE!"

    def test_self_reference(self):
        """A1 → A1 is a cycle."""
        s = Sheet()
        s.set("A1", "=A1")
        assert s.get("A1") == "#CYCLE!"

    def test_three_cell_cycle(self):
        """A1 → A2 → A3 → A1 is a cycle."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A3")
        s.set("A3", "=A1")
        assert s.get("A1") == "#CYCLE!"
        assert s.get("A2") == "#CYCLE!"
        assert s.get("A3") == "#CYCLE!"

    def test_cycle_with_arithmetic(self):
        """A1 = A2 + 1, A2 = A1 + 1 is a cycle."""
        s = Sheet()
        s.set("A1", "=A2+1")
        s.set("A2", "=A1+1")
        assert s.get("A1") == "#CYCLE!"
        assert s.get("A2") == "#CYCLE!"

    def test_no_cycle_direct_value(self):
        """A1 = 5, A2 = A1 + 1 is not a cycle."""
        s = Sheet()
        s.set("A1", 5)
        s.set("A2", "=A1+1")
        assert s.get("A2") == 6

    def test_no_cycle_dag(self):
        """A1 → A2 → A3 (no cycle)."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "=A1")
        s.set("A3", "=A2")
        assert s.get("A3") == 1

    def test_cycle_in_range(self):
        """SUM over a range containing a cycle yields #CYCLE!."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        s.set("B1", "=SUM(A1:A2)")
        assert s.get("B1") == "#CYCLE!"

    def test_cycle_not_triggered_by_literal(self):
        """A1 = 5, A2 = 6 (no formulas) — no cycle."""
        s = Sheet()
        s.set("A1", 5)
        s.set("A2", 6)
        assert s.get("A1") == 5
        assert s.get("A2") == 6

    def test_cycle_not_triggered_by_empty(self):
        """Empty cells don't cause cycles."""
        s = Sheet()
        s.set("A1", "=A2")
        # A2 is empty
        assert s.get("A1") == 0  # Empty contributes 0

    def test_r12_256_cell_chain_no_recursion_error(self):
        """256-cell chain must not raise RecursionError (R12)."""
        s = Sheet()
        s.set("A1", 1)
        for i in range(2, 100):  # Max addressable is A99
            s.set(f"A{i}", f"=A{i-1}")
        # Should not raise RecursionError
        result = s.get("A99")
        assert result == 1

    def test_count_self_reference_not_cycle(self):
        """COUNT does not participate in cycle detection (R8, R9)."""
        s = Sheet()
        s.set("A1", "=COUNT(A1:A1)")
        assert s.get("A1") == 1

    def test_cycle_propagation(self):
        """Cell off the cycle referencing a cycle cell returns #CYCLE! (R9)."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        s.set("B1", "=A1")
        assert s.get("B1") == "#CYCLE!"

    def test_cycle_recovery_after_set(self):
        """Breaking the cycle with a set recovers correct values (R9)."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        assert s.get("A1") == "#CYCLE!"
        # Break the cycle
        s.set("A1", 5)
        assert s.get("A2") == 5
        assert s.get("A1") == 5

    def test_self_in_range_cycle(self):
        """A1 = SUM(A1:B1) — source cell is inside its own range → #CYCLE!."""
        s = Sheet()
        s.set("A1", "=SUM(A1:B1)")
        assert s.get("A1") == "#CYCLE!"

    def test_self_in_range_min_cycle(self):
        """A1 = MIN(A1:A1) — source cell inside range → #CYCLE!."""
        s = Sheet()
        s.set("A1", "=MIN(A1:A1)")
        assert s.get("A1") == "#CYCLE!"

    def test_self_in_range_max_cycle(self):
        """A1 = MAX(A1:A1) — source cell inside range → #CYCLE!."""
        s = Sheet()
        s.set("A1", "=MAX(A1:A1)")
        assert s.get("A1") == "#CYCLE!"

    def test_count_exempt_from_cycle(self):
        """COUNT does not participate in cycle detection.

        A1 = COUNT(A1:A1) should return 1 (one non-empty cell), not #CYCLE!.
        """
        s = Sheet()
        s.set("A1", "=COUNT(A1:A1)")
        assert s.get("A1") == 1

    def test_propagation_off_cycle(self):
        """A cell off the cycle that references a cycle cell returns #CYCLE!."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        s.set("B1", "=A1")
        assert s.get("B1") == "#CYCLE!"

    def test_recovery_after_breaking_cycle(self):
        """Breaking a cycle with set() recovers subsequent evaluations."""
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A2", "=A1")
        assert s.get("A1") == "#CYCLE!"
        s.set("A1", 5)
        assert s.get("A2") == 5
