import pytest

from gridcalc import Workbook


def test_unset_and_literal_cells():
    sheet = Workbook().add_sheet("S1")

    assert sheet.get("A1") is None
    assert sheet.set("A1", 12) is None
    assert sheet.get("A1") == 12
    assert sheet.set("A1", "text") is None
    assert sheet.get("A1") == "text"


def test_invalid_get_address_does_not_change_counter_or_state():
    sheet = Workbook().add_sheet("S1")
    sheet.set("A1", 1)
    before = sheet.eval_count

    for bad in [5, None, "", "a1", "A0", "A01", "A100", "AA1", " A1", "A1 ", "S1!A1"]:
        with pytest.raises(ValueError):
            sheet.get(bad)

    assert sheet.get("A1") == 1
    assert sheet.eval_count == before


def test_invalid_set_raw_or_address_is_atomic():
    sheet = Workbook().add_sheet("S1")
    sheet.set("A1", 1)

    for args in [("A1", True), ("A1", 1.2), ("A0", 2), ("S1!A1", 2)]:
        with pytest.raises(ValueError):
            sheet.set(*args)

    assert sheet.get("A1") == 1


def test_subclasses_are_normalized():
    class MyInt(int):
        pass

    class MyStr(str):
        pass

    sheet = Workbook().add_sheet(MyStr("S1"))
    sheet.set(MyStr("A1"), MyInt(3))
    sheet.set("A2", MyStr("hello"))

    assert sheet.get("A1") == 3
    assert type(sheet.get("A1")) is int
    assert sheet.get("A2") == "hello"
    assert type(sheet.get("A2")) is str
