"""Phase 2 Task 2.2: Evaluator — arithmetic, references, division (R4, R6)."""
import pytest
from gridcalc import Sheet


# ── basic arithmetic ─────────────────────────────────────────────────

def test_addition():
    s = Sheet()
    s.set("A1", "=1+2")
    assert s.get("A1") == 3


def test_multiplication_precedence():
    s = Sheet()
    s.set("A1", "=1+2*3")
    assert s.get("A1") == 7


def test_parens():
    s = Sheet()
    s.set("A1", "=(1+2)*3")
    assert s.get("A1") == 9


def test_unary_minus():
    s = Sheet()
    s.set("A1", "=-1")
    assert s.get("A1") == -1


def test_double_unary_minus_formula():
    """=--1 is 1 per spec."""
    s = Sheet()
    s.set("A1", "=" + "--1")
    assert s.get("A1") == 1


def test_2_minus_double_unary():
    """=2--3 is 5 per spec."""
    s = Sheet()
    s.set("A1", "=" + "2--3")
    assert s.get("A1") == 5


def test_leading_zeros():
    s = Sheet()
    s.set("A1", "=007")
    assert s.get("A1") == 7


def test_subtraction():
    s = Sheet()
    s.set("A1", "=5-3")
    assert s.get("A1") == 2


# ── division ─────────────────────────────────────────────────────────

def test_division_truncates_toward_zero():
    s = Sheet()
    s.set("A1", "=7/2")
    assert s.get("A1") == 3


def test_negative_division():
    s = Sheet()
    s.set("A1", "=-7/2")
    assert s.get("A1") == -3


def test_division_by_negative():
    s = Sheet()
    s.set("A1", "=7/-2")
    assert s.get("A1") == -3


def test_division_by_zero():
    s = Sheet()
    s.set("A1", "=7/0")
    assert s.get("A1") == "#DIV!"


# ── references ───────────────────────────────────────────────────────

def test_ref_number_cell():
    s = Sheet()
    s.set("B1", 10)
    s.set("A1", "=B1+1")
    assert s.get("A1") == 11


def test_ref_empty_cell_is_zero():
    s = Sheet()
    s.set("A1", "=Z9+1")
    assert s.get("A1") == 1


def test_ref_string_cell_is_type_error():
    s = Sheet()
    s.set("A1", "hello")
    s.set("B1", "=A1")
    assert s.get("B1") == "#TYPE!"


def test_ref_invalid_addr_ref_error():
    """A01, A0, A100 parse fine but denote no cell → #REF!"""
    s = Sheet()
    s.set("A1", "=A01")
    assert s.get("A1") == "#REF!"

    s2 = Sheet()
    s2.set("A1", "=A0")
    assert s2.get("A1") == "#REF!"

    s3 = Sheet()
    s3.set("A1", "=A100")
    assert s3.get("A1") == "#REF!"


def test_ref_formula_cell_chains():
    s = Sheet()
    s.set("A1", "=10")
    s.set("B1", "=A1+5")
    s.set("C1", "=B1*2")
    assert s.get("C1") == 30


# ── PARSE! formula ───────────────────────────────────────────────────

def test_parse_error_formula():
    s = Sheet()
    s.set("A1", "=1 +")
    assert s.get("A1") == "#PARSE!"


def test_empty_formula():
    s = Sheet()
    s.set("A1", "=")
    assert s.get("A1") == "#PARSE!"


# ── R12: 256-cell chain ─────────────────────────────────────────────

def test_256_cell_chain_no_raise():
    """256 formula cells in a chain should evaluate without raising."""
    s = Sheet()
    s.set("A1", "=1")
    prev = "A1"
    for i in range(2, 257):
        col_idx = (i - 1) % 26
        row_idx = (i - 1) // 26 + 1
        if row_idx > 99:
            row_idx = (row_idx - 1) % 99 + 1
        addr = f"{chr(ord('A') + col_idx)}{row_idx}"
        s.set(addr, f"={prev}+1")
        prev = addr
    val = s.get(prev)
    assert isinstance(val, int)
