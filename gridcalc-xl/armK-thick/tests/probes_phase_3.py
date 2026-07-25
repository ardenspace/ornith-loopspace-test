from gridcalc import Workbook


def test_count_self_range_is_structural_not_a_cycle():
    # R8: COUNT counts non-empty formula cells without evaluating members.
    # R9/R10: range members for COUNT do not participate in cycle detection.
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=COUNT(A1:A1)")

    assert sheet.get("A1") == 1
    assert sheet.eval_count == 1

    before = sheet.eval_count
    assert sheet.get("A1") == 1
    assert sheet.eval_count == before


def test_sum_short_circuits_on_first_string_member_before_later_formula_error():
    # R7/R8: range aggregates visit row-major and a string member yields #TYPE!.
    # R10: members after the first offender are not evaluated.
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "text")
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=SUM(A1:B1)")

    assert sheet.get("C1") == "#TYPE!"
    assert sheet.eval_count == 1


def test_invalid_range_returns_ref_without_evaluating_range_members():
    # R7/R10: a misordered range is #REF! and contributes no range members.
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=1/0")
    sheet.set("C1", "=SUM(B1:A1)")

    assert sheet.get("C1") == "#REF!"
    assert sheet.eval_count == 1


def test_cycle_through_sum_ranges_marks_both_formula_members():
    # R7/R9: SUM ranges read typed member values, and cycles through ranges
    # make every cell on the cycle evaluate to #CYCLE!.
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=SUM(B1:B1)")
    sheet.set("B1", "=SUM(A1:A1)")

    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"
