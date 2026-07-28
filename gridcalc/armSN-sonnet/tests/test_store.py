import pytest

from gridcalc import Sheet


class IntSub(int):
    pass


class StrSub(str):
    pass


def test_roundtrip_int_and_str():
    s = Sheet()
    s.set("A1", 7)
    s.set("A2", "hello")
    assert s.get("A1") == 7
    assert s.get("A2") == "hello"


def test_never_set_cell_is_none():
    s = Sheet()
    assert s.get("A1") is None


def test_formula_string_accepted_without_error():
    s = Sheet()
    s.set("A1", "=1+1")  # phase 1: never call get() on it


@pytest.mark.parametrize("raw", [True, False, 1.0, None, [1, 2]])
def test_invalid_raw_types_raise(raw):
    s = Sheet()
    with pytest.raises(ValueError):
        s.set("A1", raw)


def test_int_and_str_subclass_normalized():
    s = Sheet()
    s.set("A1", IntSub(9))
    s.set("A2", StrSub("hi"))
    assert type(s.get("A1")) is int
    assert type(s.get("A2")) is str
    assert s.get("A1") == 9
    assert s.get("A2") == "hi"


def test_set_returns_none():
    s = Sheet()
    assert s.set("A1", 1) is None


def test_set_replaces_occupied_cell_across_types():
    s = Sheet()
    s.set("A1", 1)
    assert s.get("A1") == 1
    s.set("A1", "text")
    assert s.get("A1") == "text"
    s.set("A1", "=1+1")
    s.set("A1", 5)
    assert s.get("A1") == 5


def test_failed_set_leaves_prior_content_and_count_unchanged():
    s = Sheet()
    s.set("A1", 1)
    before = s.eval_count
    with pytest.raises(ValueError):
        s.set("A1", None)
    assert s.get("A1") == 1
    assert s.eval_count == before


def test_eval_count_stays_zero_for_literal_workloads():
    s = Sheet()
    for i in range(10):
        s.set("A1", i)
        s.get("A1")
    assert s.eval_count == 0
