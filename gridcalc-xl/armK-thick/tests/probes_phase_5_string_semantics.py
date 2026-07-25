from gridcalc import Workbook


def test_if_static_closure_recomputes_but_unselected_branch_stays_lazy():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=IF(1,B1,C1)")
    sheet.set("B1", "chosen")
    sheet.set("C1", "=1/0")

    assert sheet.get("A1") == "chosen"
    assert sheet.eval_count == 1

    sheet.set("C1", "=1+1")

    assert sheet.get("A1") == "chosen"
    assert sheet.eval_count == 2


def test_concat_empty_reference_and_formula_error_short_circuit_later_formula():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", '=CONCAT("x",B1,C1,D1)')
    sheet.set("C1", "=1/0")
    sheet.set("D1", "=1+1")

    assert sheet.get("A1") == "#DIV!"
    assert sheet.eval_count == 2

    assert sheet.get("D1") == 2
    assert sheet.eval_count == 3


def test_count_self_range_feeds_if_and_len_without_evaluating_cycle_members():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=COUNT(A1:B1)")
    sheet.set("B1", "abc")
    sheet.set("C1", "=IF(A1,LEN(B1),0)")

    assert sheet.get("C1") == 3
    assert sheet.eval_count == 2

    assert sheet.get("A1") == 2
    assert sheet.eval_count == 2
