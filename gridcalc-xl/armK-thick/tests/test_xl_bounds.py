import pytest

from gridcalc import Workbook


MAX_INT = 2**63 - 1


def _wb3():
    wb = Workbook()
    return wb, wb.add_sheet("S1"), wb.add_sheet("S2"), wb.add_sheet("S3")


def _assert_error(value):
    assert isinstance(value, str) and value.startswith("#")


def test_256_formula_reach_is_counted_across_sheets():
    wb = Workbook()
    sheets = [wb.add_sheet(f"S{i}") for i in range(1, 5)]
    identities = []
    for sheet in sheets:
        for row in range(1, 65):
            identities.append((sheet, sheet._name, f"A{row}"))
    assert len(identities) == 256

    prev_sheet = None
    prev_addr = None
    for index, (handle, sheet_name, addr) in enumerate(identities):
        if index == 0:
            handle.set(addr, "=1")
        else:
            handle.set(addr, f"={prev_sheet}!{prev_addr}+1")
        prev_sheet = sheet_name
        prev_addr = addr

    assert identities[-1][0].get(identities[-1][2]) == 256

    overflow_sheet = wb.add_sheet("S5")
    overflow_sheet.set("A1", f"={prev_sheet}!{prev_addr}+1")
    _assert_error(overflow_sheet.get("A1"))
    assert wb.sheet("S1").get("A1") == 1


def test_string_literals_concat_results_and_decimal_renderings_are_bounded():
    wb, s1, _s2, _s3 = _wb3()
    s1.set("A1", "x" * 4096)
    assert s1.get("A1") == "x" * 4096

    formula_literal = "y" * 500
    s1.set("A2", '="' + formula_literal + '"')
    assert s1.get("A2") == formula_literal

    s1.set("A2", "x" * 4095)
    s1.set("B1", '=CONCAT(A2,"y")')
    assert s1.get("B1") == "x" * 4095 + "y"

    s1.set("B2", f"=CONCAT({MAX_INT})")
    assert s1.get("B2") == str(MAX_INT)

    s1.set("C1", "x" * 4096)
    s1.set("C2", '=CONCAT(C1,"z")')
    _assert_error(s1.get("C2"))
    assert s1.get("B1") == "x" * 4095 + "y"


def test_out_of_bounds_string_intermediate_does_not_corrupt_later_gets():
    _wb, s1, _s2, _s3 = _wb3()
    s1.set("A1", "x" * 4096)
    s1.set("A2", '=LEN(CONCAT(A1,"z"))')
    _assert_error(s1.get("A2"))
    s1.set("B1", '=CONCAT("ok",1)')
    assert s1.get("B1") == "ok1"


def test_oversized_formula_text_copies_journals_and_undo_redo_verbatim():
    _wb, s1, _s2, _s3 = _wb3()
    formula = "=" + ("A1+" * 180) + "A1"
    assert len(formula) > 513
    s1.set("A1", 7)
    s1.set("B1", formula)

    s1.copy("B1", "C1")
    assert s1._cells["C1"] == formula

    assert _wb.undo() is True
    assert "C1" not in s1._cells
    assert _wb.redo() is True
    assert s1._cells["C1"] == formula

    loaded = Workbook.from_json(_wb.to_json())
    assert loaded.sheet("S1")._cells["C1"] == formula
    loaded.sheet("S1").copy("C1", "D1")
    assert loaded.sheet("S1")._cells["D1"] == formula
    assert loaded.sheet("S1").get("A1") == 7


def test_directed_boundary_formula_depth_string_int_and_range_ordering_cases():
    _wb, s1, s2, _s3 = _wb3()
    formula_512 = "1+" * 255 + "10"
    assert len(formula_512) == 512
    s1.set("A1", "=" + formula_512)
    assert s1.get("A1") == 265

    depth_32 = "(" * 32 + "1" + ")" * 32
    s1.set("A2", "=" + depth_32)
    assert s1.get("A2") == 1

    s1.set("B1", "q" * 4096)
    assert s1.get("B1") == "q" * 4096

    s1.set("B2", f"={MAX_INT}")
    assert s1.get("B2") == MAX_INT

    s2.set("A1", 1)
    s2.set("A2", 2)
    s1.set("C1", "=SUM(S2!A1:A2)")
    s1.set("C2", "=SUM(S2!A2:A1)")
    assert s1.get("C1") == 3
    assert s1.get("C2") == "#REF!"


def test_sum_overflow_is_confined_and_later_formula_is_usable():
    _wb, s1, _s2, _s3 = _wb3()
    s1.set("A1", MAX_INT)
    s1.set("A2", 1)
    s1.set("B1", "=SUM(A1:A2)")
    _assert_error(s1.get("B1"))
    s1.set("B2", "=A2+1")
    assert s1.get("B2") == 2
