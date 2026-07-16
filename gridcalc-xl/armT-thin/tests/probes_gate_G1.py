"""Gate G1 probes — derived from FULL SPEC alone (R1, R2 — cell store).

Scenario 1: R1 address validation (ValueError on bad args, None on valid never-set).
Scenario 2: R2 store/read-back and replacement.
Scenario 3: R2 type rules (bool rejected, other types rejected).
Scenario 4: R2 subclass normalization.
Scenario 5 (cross-cut): failed calls leave observable state incl. eval_count unchanged.
"""
import pytest

from gridcalc import Workbook


def fresh_sheet():
    wb = Workbook()
    return wb.add_sheet("S1")


# --- Scenario 1: R1 address validation ---

@pytest.mark.parametrize("bad", [5, None, 1.0, b"A1", ["A1"]])
def test_r1_non_str_address_raises(bad):
    s = fresh_sheet()
    with pytest.raises(ValueError):
        s.get(bad)
    with pytest.raises(ValueError):
        s.set(bad, 1)


@pytest.mark.parametrize("bad", [
    "a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1",
    "S1!A1", "A١", "1A", "A", "1",
])
def test_r1_invalid_str_address_raises(bad):
    s = fresh_sheet()
    with pytest.raises(ValueError):
        s.get(bad)
    with pytest.raises(ValueError):
        s.set(bad, 1)


def test_r1_valid_boundary_addresses_never_set_return_none():
    s = fresh_sheet()
    assert s.get("A1") is None  # R2: never-set cell
    assert s.get("Z99") is None
    assert s.get("A99") is None
    assert s.get("Z1") is None


# --- Scenario 2: R2 store and read back ---

def test_r2_set_returns_none_and_roundtrips():
    s = fresh_sheet()
    assert s.set("A1", 42) is None
    assert s.get("A1") == 42
    s.set("A2", "hello")
    assert s.get("A2") == "hello"
    # R2: "=..." raw is stored as a formula; get returns the formula's
    # evaluated result — an int, a str value, or an error string, never
    # None. The exact value of "=1+1" is R3/R4 (G2) — not gated here.
    s.set("A3", "=1+1")
    v = s.get("A3")
    assert v is not None
    assert type(v) in (int, str)


def test_r2_set_replaces_occupied_cell():
    s = fresh_sheet()
    s.set("A1", 42)
    s.set("A1", "x")
    assert s.get("A1") == "x"
    s.set("A1", -7)
    assert s.get("A1") == -7


# --- Scenario 3: R2 type rules ---

def test_r2_bool_raw_raises():
    s = fresh_sheet()
    with pytest.raises(ValueError):
        s.set("A1", True)
    with pytest.raises(ValueError):
        s.set("A1", False)


@pytest.mark.parametrize("bad", [1.5, None, [1], (1,), b"x", {"a": 1}])
def test_r2_other_raw_types_raise(bad):
    s = fresh_sheet()
    with pytest.raises(ValueError):
        s.set("A1", bad)


# --- Scenario 4: R2 subclass normalization ---

class IntSub(int):
    pass


class StrSub(str):
    pass


def test_r2_int_subclass_normalized_on_storage():
    s = fresh_sheet()
    s.set("A1", IntSub(7))
    v = s.get("A1")
    assert v == 7
    assert type(v) is int


def test_r2_str_subclass_normalized_on_storage_and_accepted_as_addr():
    s = fresh_sheet()
    s.set(StrSub("A2"), StrSub("hi"))
    v = s.get(StrSub("A2"))
    assert v == "hi"
    assert type(v) is str


# --- Scenario 5 (cross-cut): failed calls leave observable state unchanged ---

def test_failed_set_and_get_leave_state_and_counters_unchanged():
    # R1: a get that raises ValueError leaves all observable state —
    # contents, caches, counters — unchanged. R2: a set that raises
    # ValueError leaves the workbook unchanged. Repeat-read caching
    # (R10) is G4's business; only failed-call neutrality is gated here.
    s = fresh_sheet()
    s.set("B1", "=1+1")
    before_value = s.get("B1")

    count = s.eval_count
    with pytest.raises(ValueError):
        s.set("B1", True)            # failed set: bool raw
    assert s.eval_count == count     # counter untouched by the failed set

    count = s.eval_count
    with pytest.raises(ValueError):
        s.get("A100")                # failed get: invalid address
    assert s.eval_count == count

    count = s.eval_count
    with pytest.raises(ValueError):
        s.set(5, 1)                  # failed set: non-str addr
    assert s.eval_count == count

    # contents survived every failed call
    assert s.get("B1") == before_value

    # a literal cell set to plain str stays a literal (no formula routing)
    s.set("C1", "hello")
    count = s.eval_count
    assert s.get("C1") == "hello"
    assert s.eval_count == count     # literal reads never increment (R10 rule cited by R1's state clause)
