import pytest

from gridcalc import Sheet


class StrSub(str):
    pass


def test_valid_addresses_across_grid():
    s = Sheet()
    for addr in ("A1", "Z99", "M50"):
        s.set(addr, 1)
        assert s.get(addr) == 1


@pytest.mark.parametrize(
    "addr",
    ["a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1"],
)
def test_invalid_address_strings_raise(addr):
    s = Sheet()
    with pytest.raises(ValueError):
        s.get(addr)
    with pytest.raises(ValueError):
        s.set(addr, 1)


def test_non_str_address_raises():
    s = Sheet()
    with pytest.raises(ValueError):
        s.get(5)
    with pytest.raises(ValueError):
        s.get(None)
    with pytest.raises(ValueError):
        s.set(None, 1)


def test_str_subclass_address_accepted():
    s = Sheet()
    s.set(StrSub("A1"), 42)
    assert s.get(StrSub("A1")) == 42


def test_failed_get_leaves_state_unchanged():
    s = Sheet()
    s.set("A1", 1)
    before_count = s.eval_count
    with pytest.raises(ValueError):
        s.get("bogus")
    assert s.eval_count == before_count
    assert s.get("A1") == 1


def test_eval_count_zero_on_fresh_sheet():
    s = Sheet()
    assert s.eval_count == 0
