import pytest

from gridcalc import Workbook


class StrSubclass(str):
    pass


def test_str_subclasses_normalize_across_sheet_address_and_raw_boundaries():
    wb = Workbook()
    sheet = wb.add_sheet(StrSubclass("S1"))

    names = wb.sheet_names
    assert names == ["S1"]
    assert type(names[0]) is str

    names.append("fake")
    assert wb.sheet_names == ["S1"]

    assert sheet.set(StrSubclass("A1"), StrSubclass("hello")) is None
    value = sheet.get(StrSubclass("A1"))
    assert value == "hello"
    assert type(value) is str


def test_failed_set_is_atomic_across_workbook_observables():
    wb = Workbook()
    left = wb.add_sheet("S1")
    right = wb.add_sheet("S2")
    left.set("A1", 1)
    right.set("A1", "two")

    before = (wb.sheet_names, left.get("A1"), right.get("A1"), left.eval_count, right.eval_count)

    with pytest.raises(ValueError):
        left.set("A1", True)
    assert (wb.sheet_names, left.get("A1"), right.get("A1"), left.eval_count, right.eval_count) == before

    with pytest.raises(ValueError):
        left.set("S2!A1", 3)
    assert (wb.sheet_names, left.get("A1"), right.get("A1"), left.eval_count, right.eval_count) == before


def test_failed_workbook_queries_and_duplicate_sheet_do_not_mutate_existing_state():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("Z99", 42)

    returned_names = wb.sheet_names
    returned_names.clear()

    with pytest.raises(ValueError):
        wb.sheet("missing")
    with pytest.raises(ValueError):
        wb.add_sheet("S1")

    assert wb.sheet_names == ["S1"]
    assert wb.sheet("S1").get("Z99") == 42
    assert sheet.get("Z99") == 42
