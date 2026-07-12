"""Phase 2 Task 2.3: Comparisons + error values and propagation (R3, R5)."""
import pytest
from gridcalc import Sheet


# ── comparisons yield 1/0 ints ───────────────────────────────────────

def test_less_than():
    s = Sheet()
    s.set("A1", "=1<2")
    assert s.get("A1") == 1


def test_greater_than():
    s = Sheet()
    s.set("A1", "=2>1")
    assert s.get("A1") == 1


def test_equal():
    s = Sheet()
    s.set("A1", "=1+1=2")
    assert s.get("A1") == 1


def test_not_equal():
    s = Sheet()
    s.set("A1", "=2<>2")
    assert s.get("A1") == 0


def test_less_equal():
    s = Sheet()
    s.set("A1", "=1<=1")
    assert s.get("A1") == 1


def test_greater_equal():
    s = Sheet()
    s.set("A1", "=2>=3")
    assert s.get("A1") == 0


def test_left_associative_comparison():
    """=1<2<3 is (1<2)<3 = 1<3 = 1."""
    s = Sheet()
    s.set("A1", "=1<2<3")
    assert s.get("A1") == 1


def test_comparison_with_string_operand():
    s = Sheet()
    s.set("A1", "hello")
    s.set("B1", "=A1<2")
    assert s.get("B1") == "#TYPE!"


# ── error strings are exactly the five defined ───────────────────────

def test_error_strings_exact():
    assert Sheet()._cells is not None  # just to ensure we have the right module
    # We verify the strings exist in the evaluator module
    from gridcalc.evaluator import ERR_PARSE, ERR_REF, ERR_TYPE, ERR_DIV, ERR_CYCLE
    assert ERR_PARSE == "#PARSE!"
    assert ERR_REF == "#REF!"
    assert ERR_TYPE == "#TYPE!"
    assert ERR_DIV == "#DIV!"
    assert ERR_CYCLE == "#CYCLE!"


# ── error propagation — first textual error wins ────────────────────

def test_first_error_wins():
    """=A1+B1*C1 with B1 and C1 both errors returns B1's error."""
    s = Sheet()
    s.set("A1", "=1/0")   # #DIV!
    s.set("B1", "=1/0")   # #DIV!
    s.set("C1", "=1/0")   # #DIV!
    s.set("D1", "=A1+B1*C1")
    # A1 is evaluated first → #DIV!
    assert s.get("D1") == "#DIV!"


def test_short_circuit_div_zero():
    """=1/0+A1 is #DIV! whatever A1 holds."""
    s = Sheet()
    s.set("A1", "=1/0+A1")  # self-referencing to make it interesting
    # Actually let's use a different cell
    s2 = Sheet()
    s2.set("B1", 42)
    s2.set("A1", "=1/0+B1")
    assert s2.get("A1") == "#DIV!"


def test_short_circuit_type_error():
    """=A1/1+B1 with A1 a string → #TYPE!, B1 never evaluated."""
    s = Sheet()
    s.set("A1", "hello")
    s.set("B1", "=1/0")
    s.set("C1", "=A1/1+B1")
    assert s.get("C1") == "#TYPE!"


# ── error in reference ──────────────────────────────────────────────

def test_ref_to_error_cell():
    s = Sheet()
    s.set("A1", "=1/0")
    s.set("B1", "=A1+1")
    assert s.get("B1") == "#DIV!"


def test_error_propagates_through_arithmetic():
    s = Sheet()
    s.set("A1", "=1/0")
    s.set("B1", "=A1*2")
    s.set("C1", "=B1+1")
    assert s.get("C1") == "#DIV!"
