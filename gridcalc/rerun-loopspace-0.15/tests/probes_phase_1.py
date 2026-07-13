"""Phase 1 probes — cross-cutting scenarios derived from spec."""
from gridcalc import Sheet


def test_probe1_int_roundtrip():
    """Probe 1: R1 × R2 interaction — int round-trip."""
    s = Sheet()
    s.set("A1", 42)
    assert s.get("A1") == 42


def test_probe2_valueerror_isolation():
    """Probe 2: R1 ValueError isolation — state unchanged after invalid get."""
    s = Sheet()
    s.set("A1", 1)
    try:
        s.get("invalid")
    except ValueError:
        pass
    assert s.get("A1") == 1


def test_probe3_eval_count_literal_only():
    """Probe 3: R2 eval_count invariant — stays 0 across literal ops."""
    s = Sheet()
    s.set("A1", 1)
    s.get("A1")
    s.set("B1", "x")
    s.get("B1")
    assert s.eval_count == 0
