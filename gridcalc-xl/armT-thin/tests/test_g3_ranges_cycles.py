from gridcalc import Workbook


def make_sheet():
    return Workbook().add_sheet("S1")


def test_sum_min_max_and_empty_range_rules():
    sheet = make_sheet()
    sheet.set("A1", 3)
    sheet.set("B1", 5)
    sheet.set("A2", 1)
    sheet.set("C1", "=SUM(A1:B2)")
    sheet.set("C2", "=MIN(A1:B2)")
    sheet.set("C3", "=MAX(A1:B2)")
    sheet.set("C4", "=SUM(D1:E2)")
    sheet.set("C5", "=MIN(D1:E2)")

    assert sheet.get("C1") == 9
    assert sheet.get("C2") == 1
    assert sheet.get("C3") == 5
    assert sheet.get("C4") == 0
    assert sheet.get("C5") == "#TYPE!"


def test_range_errors_and_row_major_order():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "text")
    sheet.set("A2", "=1/0")
    sheet.set("C1", "=SUM(A1:B2)")
    sheet.set("C2", "=SUM(B2:A1)")
    sheet.set("C3", "=SUM(A0:A1)")
    sheet.set("C4", "=SUM(#REF!)")
    sheet.set("C5", "=SUM(A2:A1)")
    sheet.set("C6", "=SUM(B1:A1)")
    sheet.set("C7", "=MIN(A2:A1)")

    assert sheet.get("C1") == "#TYPE!"
    assert sheet.get("C2") == "#REF!"
    assert sheet.get("C3") == "#REF!"
    assert sheet.get("C4") == "#REF!"
    assert sheet.get("C5") == "#REF!"
    assert sheet.get("C6") == "#REF!"
    assert sheet.get("C7") == "#REF!"


def test_count_is_structural_and_does_not_evaluate_members():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("A2", "=1/0")
    sheet.set("B1", "text")
    sheet.set("C1", "=COUNT(A1:B2)")
    before = sheet.eval_count

    assert sheet.get("C1") == 3
    assert sheet.eval_count == before + 1


def test_cycles_direct_mutual_and_through_ranges():
    sheet = make_sheet()
    sheet.set("A1", "=A1")
    sheet.set("B1", "=C1")
    sheet.set("C1", "=B1")
    sheet.set("D1", "=SUM(D1:D2)")

    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"
    assert sheet.get("C1") == "#CYCLE!"
    assert sheet.get("D1") == "#CYCLE!"


def test_range_outside_function_is_parse_error_and_single_ref_arg_is_parse_error():
    sheet = make_sheet()
    sheet.set("A1", "=A1:B2")
    sheet.set("A2", "=SUM(A1)")

    assert sheet.get("A1") == "#PARSE!"
    assert sheet.get("A2") == "#PARSE!"
