"""Phase 1 Task 1.1: Address validation + Sheet skeleton (R1)."""
import pytest
from gridcalc import Sheet


def _make_sheet():
    return Sheet()


# ── valid addresses ──────────────────────────────────────────────────

def test_valid_addresses_roundtrip():
    s = _make_sheet()
    for addr in ("A1", "Z99", "M50", "B1", "AA" if False else "A1"):
        s.set(addr, 42)
        assert s.get(addr) == 42


def test_valid_address_A1():
    s = _make_sheet()
    s.set("A1", 1)
    assert s.get("A1") == 1


def test_valid_address_Z99():
    s = _make_sheet()
    s.set("Z99", 99)
    assert s.get("Z99") == 99


def test_valid_address_M50():
    s = _make_sheet()
    s.set("M50", 50)
    assert s.get("M50") == 50


# ── invalid addresses ────────────────────────────────────────────────

_INVALID_ADDRS = [
    "a1",       # lowercase
    "A0",       # row 0
    "A01",      # leading zero
    "A100",     # row > 99
    "AA1",      # two letters
    "",         # empty
    " A1",      # leading space
    "A1 ",      # trailing space
    "A 1",      # internal space
]


@pytest.mark.parametrize("bad_addr", _INVALID_ADDRS)
def test_invalid_address_raises(bad_addr):
    s = _make_sheet()
    with pytest.raises(ValueError):
        s.get(bad_addr)


@pytest.mark.parametrize("bad_addr", _INVALID_ADDRS)
def test_invalid_address_set_raises(bad_addr):
    s = _make_sheet()
    with pytest.raises(ValueError):
        s.set(bad_addr, 1)


def test_get_non_str_raises():
    s = _make_sheet()
    with pytest.raises(ValueError):
        s.get(5)
    with pytest.raises(ValueError):
        s.get(None)


def test_set_non_str_addr_raises():
    s = _make_sheet()
    with pytest.raises(ValueError):
        s.set(None, 1)
    with pytest.raises(ValueError):
        s.set(5, 1)


# ── str-subclass addr ────────────────────────────────────────────────

class MyStr(str):
    pass


def test_str_subclass_addr_accepted():
    s = _make_sheet()
    s.set(MyStr("A1"), 42)
    assert s.get("A1") == 42


# ── ValueError leaves state unchanged ────────────────────────────────

def test_get_valueerror_no_state_change():
    s = _make_sheet()
    s.set("A1", 10)
    s.get("A1")  # eval_count still 0 (literal)
    before = s.eval_count
    with pytest.raises(ValueError):
        s.get("bad")
    assert s.eval_count == before
    assert s.get("A1") == 10


def test_set_valueerror_no_state_change():
    s = _make_sheet()
    s.set("A1", 10)
    before = s.eval_count
    with pytest.raises(ValueError):
        s.set("bad", 5)
    assert s.eval_count == before
    assert s.get("A1") == 10


# ── eval_count ───────────────────────────────────────────────────────

def test_eval_count_starts_at_zero():
    s = _make_sheet()
    assert s.eval_count == 0


def test_eval_count_stays_zero_literal_only():
    s = _make_sheet()
    s.set("A1", 1)
    s.set("B1", "hello")
    s.get("A1")
    s.get("B1")
    assert s.eval_count == 0
