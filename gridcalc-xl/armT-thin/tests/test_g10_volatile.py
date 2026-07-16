from gridcalc import Workbook


def test_clock_and_now_cache_until_clock_edit():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", "=NOW()")

    assert wb.clock == 0
    assert sheet.get("A1") == 0
    before = sheet.eval_count
    assert sheet.get("A1") == 0
    assert sheet.eval_count == before

    assert wb.advance_clock() == 1
    assert wb.clock == 1
    assert sheet.get("A1") == 1
    assert sheet.eval_count == before + 1


def test_clock_edit_touches_volatile_closure_only_and_undo_redo_restores_clock():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", "=NOW()+1")
    sheet.set("B1", "=A1+1")
    sheet.set("C1", "=1+1")
    assert sheet.get("B1") == 2
    assert sheet.get("C1") == 2

    wb.advance_clock()
    before = sheet.eval_count
    assert sheet.get("B1") == 3
    assert sheet.get("C1") == 2
    assert sheet.eval_count - before == 2

    assert wb.undo() is True
    assert wb.clock == 0
    assert sheet.get("B1") == 2
    assert wb.redo() is True
    assert wb.clock == 1
    assert sheet.get("B1") == 3


def test_now_inside_string_is_not_volatile_and_wrong_arity_parse_error():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", '=CONCAT("NOW()")')
    sheet.set("A2", "=NOW(1)")
    assert sheet.get("A1") == "NOW()"
    assert sheet.get("A2") == "#PARSE!"
    before = sheet.eval_count
    wb.advance_clock()
    assert sheet.get("A1") == "NOW()"
    assert sheet.get("A2") == "#PARSE!"
    assert sheet.eval_count == before


def test_clock_persists_but_journal_and_counters_reset():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", "=NOW()")
    wb.advance_clock()
    assert sheet.get("A1") == 1

    loaded = Workbook.from_json(wb.to_json())
    loaded_sheet = loaded.sheet("S1")
    assert loaded.clock == 1
    assert loaded_sheet.eval_count == 0
    assert loaded_sheet.get("A1") == 1
    assert loaded.undo() is False


def test_now_in_unselected_if_branch_is_still_static_volatile():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("D1", "=IF(1,2,NOW())")
    assert sheet.get("D1") == 2
    before = sheet.eval_count
    wb.advance_clock()
    assert sheet.get("D1") == 2
    assert sheet.eval_count - before == 1


def test_overlong_formula_copy_is_byte_for_byte():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    raw = "=B1+" + "1+" * 260 + "1"
    sheet.set("A1", raw)
    sheet.copy("A1", "A2")
    payload = wb.to_json()
    assert raw in payload
    assert "B2" not in payload
