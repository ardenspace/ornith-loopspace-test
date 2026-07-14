

from gridcalc import Sheet


# --- Self-reference ---

def test_self_reference_returns_cycle():
    """A1 = A1 should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=A1")
    assert sheet.get("A1") == "#CYCLE!"


def test_self_reference_through_arithmetic():
    """A1 = A1+1 should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=A1+1")
    assert sheet.get("A1") == "#CYCLE!"


# --- Mutual reference ---

def test_mutual_reference_both_cycle():
    """A1 = B1, B1 = A1 — both should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"


def test_mutual_reference_three_cells():
    """A1 = B1, B1 = C1, C1 = A1 — all should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=C1")
    sheet.set("C1", "=A1")
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"
    assert sheet.get("C1") == "#CYCLE!"


# --- Through range functions ---

def test_sum_range_self_reference_cycle():
    """A1 = SUM(A1:B1) should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=SUM(A1:B1)")
    assert sheet.get("A1") == "#CYCLE!"


def test_min_range_self_reference_cycle():
    """A1 = MIN(A1:B1) should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=MIN(A1:B1)")
    assert sheet.get("A1") == "#CYCLE!"


def test_max_range_self_reference_cycle():
    """A1 = MAX(A1:B1) should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=MAX(A1:B1)")
    assert sheet.get("A1") == "#CYCLE!"


def test_count_range_self_reference_not_cycle():
    """A1 = COUNT(A1:A1) should be 1 (COUNT doesn't participate in cycle detection)."""
    sheet = Sheet()
    sheet.set("A1", "=COUNT(A1:A1)")
    assert sheet.get("A1") == 1


def test_count_range_with_other_cells():
    """COUNT should count cells without evaluating them."""
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=COUNT(A1:B1)")
    assert sheet.get("C1") == 2


# --- Propagation ---

def test_off_cycle_cell_references_cycle_cell():
    """A1 = B1, B1 = A1, C1 = A1 — C1 should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    sheet.set("C1", "=A1")
    assert sheet.get("C1") == "#CYCLE!"


def test_off_cycle_cell_references_cycle_cell_indirectly():
    """A1 = B1, B1 = C1, C1 = A1, D1 = B1 — D1 should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=C1")
    sheet.set("C1", "=A1")
    sheet.set("D1", "=B1")
    assert sheet.get("D1") == "#CYCLE!"


def test_cycle_propagation_through_arithmetic():
    """A1 = B1, B1 = A1, C1 = A1+1 — C1 should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    sheet.set("C1", "=A1+1")
    assert sheet.get("C1") == "#CYCLE!"


# --- Breaking the cycle ---

def test_breaking_cycle_recovers_values():
    """A1 = B1, B1 = A1, then set A1=5 — A1 should be 5."""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    assert sheet.get("A1") == "#CYCLE!"
    sheet.set("A1", 5)
    assert sheet.get("A1") == 5


def test_breaking_cycle_recovers_mutual():
    """A1 = B1, B1 = A1, set B1=10 — A1 should be 10."""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    sheet.set("B1", 10)
    assert sheet.get("A1") == 10
    assert sheet.get("B1") == 10


def test_recreating_cycle_after_break():
    """A1 = B1, B1 = A1, set A1=5, then set A1 = B1 again — both should cycle."""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    sheet.set("A1", 5)
    assert sheet.get("A1") == 5
    sheet.set("A1", "=B1")
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"


# --- Edge cases ---

def test_no_cycle_with_independent_cells():
    """A1 = 5, B1 = A1+1 — no cycle, B1 should be 6."""
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "=A1+1")
    assert sheet.get("B1") == 6


def test_cycle_with_empty_cell_in_range():
    """A1 = SUM(A1:C1) where B1 is empty — should still be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=SUM(A1:C1)")
    assert sheet.get("A1") == "#CYCLE!"


def test_cycle_detection_does_not_affect_normal_gets():
    """Getting a cell with no formula should not trigger cycle detection."""
    sheet = Sheet()
    sheet.set("A1", 42)
    assert sheet.get("A1") == 42


def test_cycle_propagation_through_sum():
    """A1 = B1, B1 = A1, C1 = SUM(A1:B1) — C1 should be #CYCLE!"""
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=A1")
    sheet.set("C1", "=SUM(A1:B1)")
    assert sheet.get("C1") == "#CYCLE!"
