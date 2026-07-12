"""Phase 4 Task 4.1: Lazy evaluation, result caching, eval_count (R10, R5, R7, R8)."""
import pytest
from gridcalc import Sheet


# ── set never changes eval_count ─────────────────────────────────────

def test_set_does_not_change_eval_count():
    s = Sheet()
    before = s.eval_count
    s.set("A1", 1)
    s.set("B1", "=1+2")
    s.set("C1", "hello")
    assert s.eval_count == before


# ── eval_count rises by 1 per formula cell whose computation starts ──

def test_eval_count_rises_for_formula():
    s = Sheet()
    s.set("A1", "=1+2")
    s.get("A1")
    assert s.eval_count == 1


def test_eval_count_rises_for_each_formula_in_chain():
    s = Sheet()
    s.set("A1", "=1")
    s.set("B1", "=A1+1")
    s.set("C1", "=B1+1")
    s.get("C1")
    # C1, B1, A1 all evaluated
    assert s.eval_count == 3


def test_literal_read_does_not_increment():
    s = Sheet()
    s.set("A1", 42)
    s.get("A1")
    assert s.eval_count == 0


def test_empty_read_does_not_increment():
    s = Sheet()
    s.get("A1")  # never set
    assert s.eval_count == 0


# ── repeat read adds 0 ───────────────────────────────────────────────

def test_repeat_read_adds_zero_number():
    s = Sheet()
    s.set("A1", "=1+2")
    s.get("A1")
    before = s.eval_count
    s.get("A1")
    assert s.eval_count == before


def test_repeat_read_adds_zero_error():
    """Cached error results also prevent re-computation."""
    s = Sheet()
    s.set("A1", "=1/0")
    s.get("A1")
    before = s.eval_count
    s.get("A1")
    assert s.eval_count == before


def test_repeat_read_adds_zero_parse_error():
    s = Sheet()
    s.set("A1", "=1 +")
    s.get("A1")
    before = s.eval_count
    s.get("A1")
    assert s.eval_count == before


def test_repeat_read_adds_zero_cycle_error():
    s = Sheet()
    s.set("A1", "=A1")
    s.get("A1")
    before = s.eval_count
    s.get("A1")
    assert s.eval_count == before


# ── after set, get reflects current sheet ────────────────────────────

def test_after_set_get_reflects_current():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+10")
    s.get("B1")
    assert s.get("B1") == 11
    s.set("A1", 100)
    assert s.get("B1") == 110


# ── counter-visible short-circuit ────────────────────────────────────

def test_short_circuit_counter_visible():
    """=1/0+Y1: Y1's computation never starts (delta is 0)."""
    s = Sheet()
    s.set("Y1", "=1+2")  # would add 1 if evaluated
    s.set("A1", "=1/0+Y1")
    before = s.eval_count
    s.get("A1")
    delta = s.eval_count - before
    assert delta == 1  # only A1's computation started
    assert s.get("A1") == "#DIV!"


def test_short_circuit_type_error_counter():
    """=A1/1+B1 with A1 string: B1 never evaluated."""
    s = Sheet()
    s.set("A1", "hello")
    s.set("B1", "=1/0")
    s.set("C1", "=A1/1+B1")
    before = s.eval_count
    s.get("C1")
    delta = s.eval_count - before
    assert delta == 1  # only C1 started
    assert s.get("C1") == "#TYPE!"


# ── counter-visible range semantics ──────────────────────────────────

def test_range_short_circuit_counter():
    """SUM with string in range: cells after the string not computed."""
    s = Sheet()
    s.set("A1", "=1")
    s.set("A2", "hello")  # string → #TYPE! at position 2
    s.set("A3", "=1/0")   # would be evaluated if we got this far
    s.set("B1", "=SUM(A1:A3)")
    before = s.eval_count
    s.get("B1")
    delta = s.eval_count - before
    # B1 starts (1), A1 evaluated (1), A2 is string → #TYPE! stop
    # A3 never evaluated
    assert delta == 2
    assert s.get("B1") == "#TYPE!"


def test_count_adds_zero_for_range_members():
    """COUNT doesn't increment eval_count for range members."""
    s = Sheet()
    s.set("A1", "=1+2")
    s.set("A2", "=3+4")
    s.set("A3", "=5+6")
    s.set("B1", "=COUNT(A1:A3)")
    before = s.eval_count
    s.get("B1")
    delta = s.eval_count - before
    assert delta == 1  # only B1's own computation (the COUNT itself)
    # Actually COUNT doesn't evaluate range members, so only B1 counts
    # But B1 is a formula cell, so its computation starts → +1
    assert s.get("B1") == 3


def test_count_no_eval_count_for_members():
    """COUNT's range members don't increment eval_count at all."""
    s = Sheet()
    s.set("A1", "=1+2")
    s.set("B1", "=COUNT(A1:A1)")
    before = s.eval_count
    s.get("B1")
    delta = s.eval_count - before
    # B1 is a formula cell, its computation starts → +1
    # COUNT doesn't evaluate A1, so A1 doesn't count
    assert delta == 1
    assert s.get("B1") == 1
