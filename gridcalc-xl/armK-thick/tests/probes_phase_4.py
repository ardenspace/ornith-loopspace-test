from gridcalc import Workbook


def test_count_range_members_are_static_closure_but_not_evaluated():
    """R8 says COUNT does not evaluate members; R10 still includes them in closure."""
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=COUNT(B1:B2)")
    sheet.set("B1", "=D1+1")
    sheet.set("D1", 10)

    before = sheet.eval_count
    assert sheet.get("A1") == 1
    assert sheet.eval_count - before == 1

    sheet.set("D1", 20)
    before = sheet.eval_count
    assert sheet.get("A1") == 1
    assert sheet.eval_count - before == 1


def test_identical_formula_write_invalidates_but_preserves_left_to_right_short_circuit():
    """R5 short-circuits after first error; R10 identical writes still invalidate."""
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=1/0+B1")
    sheet.set("B1", "=40+2")

    before = sheet.eval_count
    assert sheet.get("A1") == "#DIV!"
    assert sheet.eval_count - before == 1

    sheet.set("A1", "=1/0+B1")
    before = sheet.eval_count
    assert sheet.get("A1") == "#DIV!"
    assert sheet.eval_count - before == 1


def test_out_of_bounds_formula_storage_is_irrelevant_lazy_edit_for_existing_cache():
    """R12 stores out-of-bounds formulas lazily; R10 irrelevant edits keep cache warm."""
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", "=B1+1")
    sheet.set("B1", 4)

    before = sheet.eval_count
    assert sheet.get("A1") == 5
    assert sheet.eval_count - before == 1

    sheet.set("C1", "=" + "1" * 513)
    before = sheet.eval_count
    assert sheet.get("A1") == 5
    assert sheet.eval_count - before == 0
