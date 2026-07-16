import pytest

from gridcalc import Workbook


def make_sheet():
    return Workbook().add_sheet("S1")


def test_absolute_refs_evaluate_like_plain_refs_and_affect_copy_only():
    sheet = make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=$A$1+$A1+A$1+A1")
    sheet.copy("B1", "C2")

    assert sheet.get("B1") == 40
    assert sheet.get("C2") == 50


def test_copy_literals_parse_errors_and_invalid_calls_are_atomic():
    sheet = make_sheet()
    sheet.set("A1", 7)
    sheet.copy("A1", "B1")
    assert sheet.get("B1") == 7

    sheet.set("A2", "=SUM(A1)")
    sheet.copy("A2", "B2")
    assert sheet.get("B2") == "#PARSE!"

    with pytest.raises(ValueError):
        sheet.copy("C1", "D1")
    assert sheet.get("B1") == 7


def test_copy_rewrites_ranges_and_out_of_grid_refs():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("A2", 3)
    sheet.set("B2", 4)
    sheet.set("C3", "=SUM(A1:B2)")
    sheet.copy("C3", "D4")
    assert sheet.get("D4") == 14

    sheet.set("A1", "=A2+Z99")
    sheet.copy("A1", "Z99")
    assert sheet.get("Z99") == "#REF!"


def test_names_as_primary_and_range_args():
    sheet = make_sheet()
    sheet.set("A1", 5)
    sheet.set("A2", 7)
    sheet.define_name("ONE", "A1")
    sheet.define_name("PAIR", "A1:A2")
    sheet.set("B1", "=ONE+1")
    sheet.set("B2", "=SUM(PAIR)")
    sheet.set("B3", "=PAIR")
    sheet.set("B4", "=MISSING")

    assert sheet.get("B1") == 6
    assert sheet.get("B2") == 12
    assert sheet.get("B3") == "#REF!"
    assert sheet.get("B4") == "#NAME!"


def test_copy_preserves_name_tokens_that_contain_ref_suffixes():
    sheet = make_sheet()
    sheet.set("B1", 5)
    sheet.set("C1", 6)
    sheet.define_name("AA1", "B1")
    sheet.define_name("DATA1", "B1:C1")
    sheet.set("A1", "=AA1")
    sheet.set("A2", "=SUM(DATA1)")

    sheet.copy("A1", "A3")
    sheet.copy("A2", "B3")

    assert sheet.get("A3") == 5
    assert sheet.get("B3") == 11


def test_define_name_validates_and_invalidates_mentions_only():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("A2", 2)
    sheet.define_name("NN", "A1")
    sheet.set("B1", "=NN+1")
    sheet.set("B2", "=A2+1")
    assert sheet.get("B1") == 2
    assert sheet.get("B2") == 3

    sheet.define_name("NN", "A2")
    before = sheet.eval_count
    assert sheet.get("B1") == 3
    assert sheet.get("B2") == 3
    assert sheet.eval_count - before == 1

    for args in [("A1", "A1"), ("SUM", "A1"), ("OK", "A0"), ("OK", "B2:A1")]:
        with pytest.raises(ValueError):
            sheet.define_name(*args)
