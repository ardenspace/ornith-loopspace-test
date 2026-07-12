"""Phase 3 Task 3.1: Function grammar + SUM/MIN/MAX/COUNT (R3, R7, R8)."""
import pytest
from gridcalc import Sheet


# ── function call syntax ─────────────────────────────────────────────

def test_sum_basic():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", 2)
    s.set("A3", 3)
    s.set("B1", "=SUM(A1:A3)")
    assert s.get("B1") == 6


def test_sum_with_whitespace():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", 2)
    s.set("B1", "=SUM(A1 : A2)")
    assert s.get("B1") == 3


def test_sum_composes():
    """=SUM(A1:B2)+1 is legal."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", 2)
    s.set("A2", 3)
    s.set("B2", 4)
    s.set("C1", "=SUM(A1:B2)+1")
    assert s.get("C1") == 11


def test_max_composes():
    """=-MAX(A1:A2)*2 is legal."""
    s = Sheet()
    s.set("A1", 5)
    s.set("A2", 10)
    s.set("B1", "=-MAX(A1:A2)*2")
    assert s.get("B1") == -20


# ── #PARSE! on invalid function syntax ───────────────────────────────

def test_unknown_function():
    s = Sheet()
    s.set("A1", "=AVG(A1:A2)")
    assert s.get("A1") == "#PARSE!"


def test_lowercase_function():
    s = Sheet()
    s.set("A1", "=sum(A1:A2)")
    assert s.get("A1") == "#PARSE!"


def test_range_outside_function():
    s = Sheet()
    s.set("A1", "=A1:B2")
    assert s.get("A1") == "#PARSE!"


def test_function_with_single_ref():
    """=SUM(A1) — no colon — is #PARSE!"""
    s = Sheet()
    s.set("A1", "=SUM(A1)")
    assert s.get("A1") == "#PARSE!"


def test_function_with_parens_around_range():
    """=SUM((A1:B2)) is #PARSE!"""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=SUM((A1:A1))")
    assert s.get("B1") == "#PARSE!"


# ── #REF! on invalid ranges ─────────────────────────────────────────

def test_misordered_range():
    """=SUM(B2:A1) — TL col > BR col — is #REF!"""
    s = Sheet()
    s.set("A1", "=SUM(B2:A1)")
    assert s.get("A1") == "#REF!"


def test_range_out_of_grid():
    """=SUM(A0:B2) — A0 is invalid — is #REF!"""
    s = Sheet()
    s.set("A1", "=SUM(A0:B2)")
    assert s.get("A1") == "#REF!"


def test_range_row_100():
    """=SUM(A1:A100) — row 100 out of range — is #REF!"""
    s = Sheet()
    s.set("A1", "=SUM(A1:A100)")
    assert s.get("A1") == "#REF!"


# ── SUM semantics ────────────────────────────────────────────────────

def test_sum_skips_empty():
    s = Sheet()
    s.set("A1", 1)
    # A2, A3 empty
    s.set("B1", "=SUM(A1:A3)")
    assert s.get("B1") == 1


def test_sum_all_empty():
    """SUM(A1:A3) where A1 is being evaluated → cycle (R9)."""
    s = Sheet()
    s.set("A1", "=SUM(A1:A3)")
    assert s.get("A1") == "#CYCLE!"


def test_sum_with_string_cell():
    """A string cell in range → #TYPE!"""
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", "hello")
    s.set("A3", 3)
    s.set("B1", "=SUM(A1:A3)")
    assert s.get("B1") == "#TYPE!"


# ── MIN/MAX semantics ────────────────────────────────────────────────

def test_min():
    s = Sheet()
    s.set("A1", 5)
    s.set("A2", 2)
    s.set("A3", 8)
    s.set("B1", "=MIN(A1:A3)")
    assert s.get("B1") == 2


def test_max():
    s = Sheet()
    s.set("A1", 5)
    s.set("A2", 2)
    s.set("A3", 8)
    s.set("B1", "=MAX(A1:A3)")
    assert s.get("B1") == 8


def test_min_all_empty():
    """MIN(A1:A3) where A1 is being evaluated → cycle (R9)."""
    s = Sheet()
    s.set("A1", "=MIN(A1:A3)")
    assert s.get("A1") == "#CYCLE!"


def test_max_all_empty():
    """MAX(A1:A3) where A1 is being evaluated → cycle (R9)."""
    s = Sheet()
    s.set("A1", "=MAX(A1:A3)")
    assert s.get("A1") == "#CYCLE!"


def test_min_with_string():
    s = Sheet()
    s.set("A1", "x")
    s.set("A2", 2)
    s.set("B1", "=MIN(A1:A2)")
    assert s.get("B1") == "#TYPE!"


# ── COUNT semantics ──────────────────────────────────────────────────

def test_count():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", "hello")
    s.set("A3", "=10")
    s.set("B1", "=COUNT(A1:A3)")
    assert s.get("B1") == 3


def test_count_skips_empty():
    s = Sheet()
    s.set("A1", 1)
    # A2 empty
    s.set("A3", 3)
    s.set("B1", "=COUNT(A1:A3)")
    assert s.get("B1") == 2


def test_count_self_reference():
    """A1 holding =COUNT(A1:A1) is 1, not #CYCLE!"""
    s = Sheet()
    s.set("A1", "=COUNT(A1:A1)")
    assert s.get("A1") == 1


def test_count_all_empty():
    """COUNT(A1:A3) where A1 has a formula → A1 is non-empty, count=1."""
    s = Sheet()
    s.set("A1", "=COUNT(A1:A3)")
    assert s.get("A1") == 1


def test_count_invalid_range():
    s = Sheet()
    s.set("A1", "=COUNT(A0:A1)")
    assert s.get("A1") == "#REF!"


# ── row-major visit order ───────────────────────────────────────────

def test_row_major_visit_order():
    """SUM(A1:B2) visits A1, B1, A2, B2."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "error_cell")  # string → #TYPE!
    s.set("A2", 3)
    s.set("B2", 4)
    s.set("C1", "=SUM(A1:B2)")
    # B1 is a string, so #TYPE! at B1, A2 and B2 never evaluated
    assert s.get("C1") == "#TYPE!"
