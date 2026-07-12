"""Phase 1 Task 1.2: Literal values — types, normalization, replacement (R2)."""
import pytest
from gridcalc import Sheet


def _make_sheet():
    return Sheet()


# ── int and str round-trip ───────────────────────────────────────────

def test_int_roundtrip():
    s = _make_sheet()
    s.set("A1", 42)
    assert s.get("A1") == 42


def test_str_roundtrip():
    s = _make_sheet()
    s.set("A1", "hello")
    assert s.get("A1") == "hello"


def test_never_set_returns_none():
    s = _make_sheet()
    assert s.get("A1") is None


# ── formula string accepted at set (no get on formula in phase 1) ───

def test_formula_string_accepted_at_set():
    s = _make_sheet()
    s.set("A1", "=1+2")
    # phase 1 doesn't evaluate — but we can check it's stored
    # (we won't call get on it here)


# ── bool raises ValueError ──────────────────────────────────────────

def test_bool_raw_raises():
    s = _make_sheet()
    with pytest.raises(ValueError):
        s.set("A1", True)
    with pytest.raises(ValueError):
        s.set("A1", False)


# ── other invalid types ─────────────────────────────────────────────

@pytest.mark.parametrize("bad", [1.5, None, [], {}, set()])
def test_invalid_raw_types(bad):
    s = _make_sheet()
    with pytest.raises(ValueError):
        s.set("A1", bad)


# ── int-subclass and str-subclass normalization ──────────────────────

class MyInt(int):
    pass


class MyStr(str):
    pass


def test_int_subclass_normalized():
    s = _make_sheet()
    s.set("A1", MyInt(42))
    val = s.get("A1")
    assert val == 42
    assert type(val) is int


def test_str_subclass_normalized():
    s = _make_sheet()
    s.set("A1", MyStr("hello"))
    val = s.get("A1")
    assert val == "hello"
    assert type(val) is str


# ── set returns None ─────────────────────────────────────────────────

def test_set_returns_none():
    s = _make_sheet()
    assert s.set("A1", 1) is None


# ── set replaces content ────────────────────────────────────────────

def test_set_replaces_int_with_str():
    s = _make_sheet()
    s.set("A1", 1)
    s.set("A1", "hello")
    assert s.get("A1") == "hello"


def test_set_replaces_str_with_int():
    s = _make_sheet()
    s.set("A1", "hello")
    s.set("A1", 42)
    assert s.get("A1") == 42


def test_set_replaces_with_formula():
    s = _make_sheet()
    s.set("A1", 1)
    s.set("A1", "=2+3")
    # formula evaluation is phase 2


# ── ValueError leaves state unchanged ────────────────────────────────

def test_set_valueerror_no_change():
    s = _make_sheet()
    s.set("A1", 10)
    before = s.eval_count
    with pytest.raises(ValueError):
        s.set("A1", True)
    assert s.eval_count == before
    assert s.get("A1") == 10


# ── eval_count stays 0 for literals ─────────────────────────────────

def test_eval_count_zero_literal_only():
    s = _make_sheet()
    s.set("A1", 1)
    s.set("B1", "x")
    s.set("C1", 2)
    s.get("A1")
    s.get("B1")
    s.get("C1")
    assert s.eval_count == 0
