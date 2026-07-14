import pytest

from gridcalc import Sheet


class Address(str):
    pass


class Number(int):
    pass


class Text(str):
    pass


def test_str_subclass_address_and_int_subclass_raw_normalize_together():
    sheet = Sheet()

    assert sheet.set(Address("M50"), Number(12)) is None


    value = sheet.get(Address("M50"))
    assert value == 12
    assert type(value) is int
    assert sheet.eval_count == 0


def test_formula_shaped_str_subclass_is_stored_without_literal_phase_evaluation():
    sheet = Sheet()

    assert sheet.set(Address("A1"), Text("=Z99+1")) is None

    assert sheet.eval_count == 0


def test_failed_set_preserves_prior_content_and_eval_count():
    sheet = Sheet()
    sheet.set("Z99", 5)

    for raw in (True, 1.25, None, ["x"]):
        with pytest.raises(ValueError):
            sheet.set("Z99", raw)
        assert sheet.get("Z99") == 5
        assert sheet.eval_count == 0


def test_failed_get_preserves_content_and_eval_count():
    sheet = Sheet()
    sheet.set("A1", Text("kept"))

    for addr in ("a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1", 5, None):
        with pytest.raises(ValueError):
            sheet.get(addr)
        assert sheet.get("A1") == "kept"
        assert type(sheet.get("A1")) is str
        assert sheet.eval_count == 0
