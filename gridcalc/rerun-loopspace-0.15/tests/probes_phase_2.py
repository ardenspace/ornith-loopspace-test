"""Phase 2 probes — cross-cutting scenarios derived from spec."""
from gridcalc import Sheet


def test_probe1_division_truncation():
    """Probe 1: R3 × R4 — division truncates toward zero."""
    s = Sheet()
    s.set("A1", "=-7/2")
    assert s.get("A1") == -3


def test_probe2_error_propagation_through_ref():
    """Probe 2: R5 × R6 — error propagates through references."""
    s = Sheet()
    s.set("A1", "=1/0")
    s.set("B1", "=A1")
    assert s.get("B1") == "#DIV!"


def test_probe3_left_most_error_wins():
    """Probe 3: R3 × R5 — left-most error wins in arithmetic."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=1/0")
    s.set("C1", "=1/0")
    s.set("D1", "=A1+B1*C1")
    assert s.get("D1") == "#DIV!"
