"""Phase 3 Task 3.2: Circular-reference detection (R9)."""
import pytest
from gridcalc import Sheet


# ── self-reference ───────────────────────────────────────────────────

def test_self_reference():
    s = Sheet()
    s.set("A1", "=A1")
    assert s.get("A1") == "#CYCLE!"


# ── mutual reference ─────────────────────────────────────────────────

def test_mutual_reference():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    assert s.get("B1") == "#CYCLE!"


# ── through a range ──────────────────────────────────────────────────

def test_cycle_through_range():
    """A1 =SUM(A1:B1) is #CYCLE!"""
    s = Sheet()
    s.set("B1", 5)
    s.set("A1", "=SUM(A1:B1)")
    assert s.get("A1") == "#CYCLE!"


def test_count_does_not_cycle():
    """A1 =COUNT(A1:A1) stays 1."""
    s = Sheet()
    s.set("A1", "=COUNT(A1:A1)")
    assert s.get("A1") == 1


# ── propagation ──────────────────────────────────────────────────────

def test_off_cycle_receives_cycle():
    """A cell off the cycle that references one returns #CYCLE!"""
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")  # mutual cycle between A1 and B1
    s.set("C1", "=A1+1")
    assert s.get("C1") == "#CYCLE!"


# ── breaking the cycle ───────────────────────────────────────────────

def test_breaking_cycle_recovers():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    # Break the cycle
    s.set("B1", "=10")
    assert s.get("A1") == 10


def test_breaking_range_cycle():
    s = Sheet()
    s.set("A1", "=SUM(A1:B1)")
    s.set("B1", 5)
    assert s.get("A1") == "#CYCLE!"
    # Break by changing A1 to not reference itself
    s.set("A1", "=B1+1")
    assert s.get("A1") == 6
