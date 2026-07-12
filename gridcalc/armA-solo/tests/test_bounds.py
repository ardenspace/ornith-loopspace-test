"""Phase 4 Task 4.3: Bounds hardening (R12)."""
import pytest
from gridcalc import Sheet


# ── 32-deep nested parentheses ───────────────────────────────────────

def test_32_deep_parens():
    """32-deep nested parentheses parse and evaluate without raising."""
    s = Sheet()
    formula = "=" + "(" * 32 + "1" + ")" * 32
    s.set("A1", formula)
    assert s.get("A1") == 1


# ── ~510-deep unary-minus tower inside 512 chars ─────────────────────

def test_deep_unary_minus_tower():
    """~510-deep unary minus within 512 chars."""
    s = Sheet()
    # "-" * 510 + "1" has 511 chars, which is <= 512
    formula = "=" + "-" * 510 + "1"
    assert len(formula) <= 512
    s.set("A1", formula)
    # 510 minuses: even → 1, odd → -1. 510 is even.
    assert s.get("A1") == 1


# ── 256-formula-cell reference chain ─────────────────────────────────

def test_256_cell_chain():
    """256 formula cells in a chain evaluates without raising."""
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
    # Should not raise
    val = s.get(prev)
    assert isinstance(val, int)


# ── magnitude bound: intermediates at or below |2**63 - 1| ───────────

def test_magnitude_bound():
    """Arithmetic with intermediates at 2**63-1 completes without raising."""
    s = Sheet()
    max_val = 2**63 - 1
    s.set("A1", max_val)
    s.set("B1", "=A1+0")
    assert s.get("B1") == max_val


def test_magnitude_bound_multiplication():
    """Multiplication chain peaking near the bound."""
    s = Sheet()
    # 2^62 * 2 = 2^63 which exceeds bound, but 2^62 * 1 = 2^62 is fine
    s.set("A1", 2**62)
    s.set("B1", "=A1*1")
    assert s.get("B1") == 2**62


# ── confinement: >512-char formula in unrelated cell ─────────────────

def test_confinement_large_formula_unrelated():
    """>512-char formula in unrelated cell: set succeeds, within-bounds gets work."""
    s = Sheet()
    # Put a >512-char formula in Z99 (unrelated to A1)
    big_formula = "=" + "-1+" * 200 + "1"  # way over 512 chars
    s.set("Z99", big_formula)  # set should succeed
    # Within-bounds get on A1 should work
    s.set("A1", "=1+2")
    assert s.get("A1") == 3
