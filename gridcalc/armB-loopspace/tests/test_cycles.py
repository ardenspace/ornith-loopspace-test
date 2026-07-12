import pytest
from gridcalc.sheet import Sheet


class TestSelfReference:
    def test_self_ref_returns_cycle(self):
        """A1 =A1 should return #CYCLE!."""
        sheet = Sheet()
        sheet.set("A1", "=A1")
        assert sheet.get("A1") == "#CYCLE!"


class TestMutualReference:
    def test_mutual_ref_both_cycle(self):
        """A1 =B1, B1 =A1 — both should be #CYCLE!."""
        sheet = Sheet()
        sheet.set("A1", "=B1")
        sheet.set("B1", "=A1")
        assert sheet.get("A1") == "#CYCLE!"
        assert sheet.get("B1") == "#CYCLE!"


class TestRangeCycle:
    def test_sum_through_range_cycle(self):
        """A1 =SUM(A1:B1) with B1=5 should be #CYCLE!."""
        sheet = Sheet()
        sheet.set("B1", 5)
        sheet.set("A1", "=SUM(A1:B1)")
        assert sheet.get("A1") == "#CYCLE!"

    def test_count_does_not_participate(self):
        """A1 =COUNT(A1:A1) should be 1, not #CYCLE!."""
        sheet = Sheet()
        sheet.set("A1", "=COUNT(A1:A1)")
        assert sheet.get("A1") == 1


class TestPropagation:
    def test_off_cycle_cell_gets_cycle_error(self):
        """A1 =B1 (cycle), C1 =A1 — C1 should be #CYCLE!."""
        sheet = Sheet()
        sheet.set("A1", "=B1")
        sheet.set("B1", "=A1")
        sheet.set("C1", "=A1")
        assert sheet.get("C1") == "#CYCLE!"

    def test_propagation_through_arithmetic(self):
        """A1 =B1 (cycle), C1 =A1+1 — C1 should be #CYCLE!."""
        sheet = Sheet()
        sheet.set("A1", "=B1")
        sheet.set("B1", "=A1")
        sheet.set("C1", "=A1+1")
        assert sheet.get("C1") == "#CYCLE!"


class TestRecovery:
    def test_breaking_cycle_recovers(self):
        """After setting A1 to a value, cycle is broken and values recover."""
        sheet = Sheet()
        sheet.set("A1", "=B1")
        sheet.set("B1", "=A1")
        # Both are #CYCLE!
        assert sheet.get("A1") == "#CYCLE!"
        assert sheet.get("B1") == "#CYCLE!"
        # Break the cycle
        sheet.set("A1", 10)
        # Now B1 = A1 = 10, A1 = 10
        assert sheet.get("A1") == 10
        assert sheet.get("B1") == 10

    def test_rebuild_cycle_after_break(self):
        """Re-establishing the cycle again should produce #CYCLE!."""
        sheet = Sheet()
        sheet.set("A1", 10)
        sheet.set("B1", 10)
        # Now set up cycle
        sheet.set("A1", "=B1")
        sheet.set("B1", "=A1")
        assert sheet.get("A1") == "#CYCLE!"
        assert sheet.get("B1") == "#CYCLE!"
