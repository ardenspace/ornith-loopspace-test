import pytest

import gridcalc
from gridcalc import Workbook


def test_public_surface_and_sheet_names_are_exact_and_fresh():
    assert gridcalc.__all__ == ["Workbook"]
    assert sorted(name for name in dir(Workbook) if not name.startswith("_")) == [
        "add_sheet",
        "advance_clock",
        "clock",
        "from_json",
        "redo",
        "sheet",
        "sheet_names",
        "to_json",
        "undo",
    ]
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    assert sorted(name for name in dir(s1) if not name.startswith("_")) == [
        "copy",
        "define_name",
        "eval_count",
        "get",
        "set",
    ]
    names = wb.sheet_names
    names.append("X")
    assert wb.sheet_names == ["S1"]


def test_qualified_refs_ranges_and_cross_sheet_counters():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("A1", 5)
    s2.set("A2", 7)
    s1.set("B1", "=S2!A1+1")
    s1.set("B2", "=SUM(S2!A1:A2)")

    assert s1.get("B1") == 6
    assert s1.get("B2") == 12
    assert s1.eval_count == 2
    assert s2.eval_count == 0


def test_cross_sheet_cycles_and_absent_sheet_ref():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", "=S2!A1")
    s2.set("A1", "=S1!A1")
    s1.set("B1", "=Ghost!A1")

    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A1") == "#CYCLE!"
    assert s1.get("B1") == "#REF!"


def test_qualified_copy_and_destination_host_semantics():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 1)
    s2.set("A1", 10)
    s1.set("B1", "=A1+S2!A1")
    s1.copy("S1!B1", "S2!B1")

    assert s2.get("B1") == 20


def test_copy_never_shifts_sheet_qualifier():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("C2", 55)
    s1.set("D1", "=S2!B1")
    s1.copy("D1", "E2")
    assert s1.get("E2") == 55

    s1.set("D2", "=S2!Z1")
    s1.copy("D2", "E2")
    assert s1.get("E2") == "#REF!"


def test_qualified_name_targets_and_per_sheet_name_resolution():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 3)
    s2.set("A1", 4)
    s1.define_name("VAL", "S2!A1")
    s2.define_name("VAL", "A1")
    s1.set("B1", "=VAL")
    s2.set("B1", "=VAL")

    assert s1.get("B1") == 4
    assert s2.get("B1") == 4
    with pytest.raises(ValueError):
        s1.define_name("BAD", "Ghost!A1")


def test_add_sheet_touch_set_and_eval_count_name_lifetime():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "=NEWS!A1")
    assert s1.get("A1") == "#REF!"
    news = wb.add_sheet("NEWS")
    assert s1.get("A1") == 0

    news.set("B1", "=1+1")
    assert news.get("B1") == 2
    assert news.eval_count == 1
    assert wb.undo() is True
    assert wb.undo() is True
    assert wb.add_sheet("NEWS").eval_count == 1
