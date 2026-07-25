import pytest

from gridcalc import Workbook


def test_volatile_unselected_if_branch_survives_roundtrip_and_uses_warm_bound():
    """R15 static IF closure + R24/R25 round-trip + R27 volatile cache bound."""
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", '=IF(1,5,NOW())')

    assert sh.get("A1") == 5
    assert sh.eval_count == 1

    loaded = Workbook.from_json(wb.to_json())
    loaded_sh = loaded.sheet("S")

    assert loaded_sh.get("A1") == 5
    assert loaded_sh.eval_count == 1
    assert loaded_sh.get("A1") == 5
    assert loaded_sh.eval_count == 1

    assert loaded.advance_clock() == 1
    assert loaded_sh.get("A1") == 5
    assert loaded_sh.eval_count == 2


def test_out_of_bounds_string_result_does_not_corrupt_cross_sheet_volatile_get():
    """R12/R28 damage confinement + R11/R23 cross-sheet values + R26 NOW()."""
    wb = Workbook()
    data = wb.add_sheet("Data")
    calc = wb.add_sheet("Calc")
    data.set("A1", "ok")
    data.set("B1", "x" * 4096)
    data.set("B2", "y")
    calc.set("A1", '=CONCAT(Data!A1,"-",NOW())')
    calc.set("B1", "=CONCAT(Data!B1,Data!B2)")

    try:
        calc.get("B1")
    except Exception:
        pass

    assert wb.advance_clock() == 1
    assert calc.get("A1") == "ok-1"
    assert calc.get("A1") == "ok-1"


def test_overlong_formula_copy_undo_roundtrip_keeps_later_within_bounds_working():
    """R17 copy journals + R24 persistence + R28 overlong formula mutation tolerance."""
    wb = Workbook()
    sh = wb.add_sheet("S")
    overlong_formula = "=" + "+".join(["1"] * 260)
    assert len(overlong_formula) > 512

    sh.set("A1", overlong_formula)
    sh.copy("A1", "B1")
    sh.set("C1", '=CONCAT("safe",NOW())')

    assert wb.undo() is True
    assert sh.get("C1") is None
    assert wb.redo() is True
    assert sh.get("C1") == "safe0"

    loaded = Workbook.from_json(wb.to_json())
    loaded_sh = loaded.sheet("S")
    assert loaded_sh.get("C1") == "safe0"
    assert loaded.advance_clock() == 1
    assert loaded_sh.get("C1") == "safe1"

    with pytest.raises(ValueError):
        loaded_sh.copy("D1", "E1")
    assert loaded_sh.get("C1") == "safe1"
