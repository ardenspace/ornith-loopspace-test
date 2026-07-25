from gridcalc import Workbook


def test_literal_error_text_reference_is_string_not_formula_error():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "#DIV!")
    sheet.set("B1", "=A1+1")

    assert sheet.get("B1") == "#TYPE!"
    assert sheet.eval_count == 1


def test_scalar_cycle_propagates_to_dependent_formula():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=B1+1")
    sheet.set("B1", "=A1+1")
    sheet.set("C1", "=A1+5")

    assert sheet.get("C1") == "#CYCLE!"
    assert sheet.get("A1") == "#CYCLE!"


def test_left_to_right_error_short_circuits_later_formula_reference():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=1+1")
    sheet.set("C1", "=A1+B1")

    assert sheet.get("C1") == "#DIV!"
    assert sheet.eval_count == 2


def test_name_error_crosses_reference_before_later_type_error():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=FOO")
    sheet.set("B1", "=A1+\"x\"")

    assert sheet.get("B1") == "#NAME!"
    assert sheet.eval_count == 2
