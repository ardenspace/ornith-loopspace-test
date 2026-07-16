from gridcalc import Workbook


def make_sheet():
    return Workbook().add_sheet("S1")


def test_repeat_read_uses_cache_and_relevant_edit_recomputes_closure_only():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=A1+1")
    sheet.set("C1", "=B1+1")

    before = sheet.eval_count
    assert sheet.get("C1") == 3
    assert sheet.eval_count - before == 2

    before = sheet.eval_count
    assert sheet.get("C1") == 3
    assert sheet.eval_count - before == 0

    sheet.set("A1", 5)
    before = sheet.eval_count
    assert sheet.get("C1") == 7
    assert 1 <= sheet.eval_count - before <= 2


def test_irrelevant_edit_keeps_cached_result_and_counter_unchanged():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=A1+1")
    assert sheet.get("B1") == 2

    sheet.set("Z99", 100)
    before = sheet.eval_count

    assert sheet.get("B1") == 2
    assert sheet.eval_count == before


def test_formula_replacement_cleans_old_dependency_edges():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 10)
    sheet.set("C1", "=A1+1")
    assert sheet.get("C1") == 2

    sheet.set("C1", "=B1+1")
    assert sheet.get("C1") == 11

    sheet.set("A1", 5)
    before = sheet.eval_count

    assert sheet.get("C1") == 11
    assert sheet.eval_count == before


def test_count_members_are_static_closure_but_not_evaluated():
    sheet = make_sheet()
    sheet.set("A1", "=1+1")
    sheet.set("B1", "=COUNT(A1:A1)")

    before = sheet.eval_count
    assert sheet.get("B1") == 1
    assert sheet.eval_count - before == 1

    before = sheet.eval_count
    assert sheet.get("B1") == 1
    assert sheet.eval_count - before == 0

    sheet.set("A1", "=2+2")
    before = sheet.eval_count
    assert sheet.get("B1") == 1
    assert sheet.eval_count - before == 1


def test_cycle_results_cache_and_clear_after_edit():
    sheet = make_sheet()
    sheet.set("A1", "=A1")

    before = sheet.eval_count
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.eval_count - before == 1

    before = sheet.eval_count
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.eval_count - before == 0

    sheet.set("A1", 3)
    assert sheet.get("A1") == 3



def test_r12_directed_chain_and_unary_tower_within_bounds():
    sheet = make_sheet()
    sheet.set("A1", 1)
    for row in range(2, 99):
        sheet.set(f"A{row}", f"=A{row - 1}+1")
    assert sheet.get("A98") == 98

    sheet.set("B1", "=" + "-" * 500 + "1")
    assert sheet.get("B1") == 1
