from gridcalc import Sheet


def test_short_circuit_error_does_not_start_later_formula_and_caches_error():
    # R5 evaluates operands left-to-right and short-circuits on the first error.
    # R10 increments only when a formula computation starts, and caches errors.
    sheet = Sheet()
    sheet.set("A1", "=1/0+Y1")
    sheet.set("Y1", "=1+1")

    before = sheet.eval_count
    assert sheet.get("A1") == "#DIV!"
    assert sheet.eval_count - before == 1

    before = sheet.eval_count
    assert sheet.get("A1") == "#DIV!"
    assert sheet.eval_count - before == 0


def test_count_range_member_is_closure_dependency_but_not_evaluated():
    # R8 COUNT counts non-empty cells without evaluating range members.
    # R10 still includes COUNT range members in reference closure for invalidation.
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=COUNT(A1:A1)")

    before = sheet.eval_count
    assert sheet.get("B1") == 1
    assert sheet.eval_count - before == 1

    sheet.set("A1", "=1/0")
    before = sheet.eval_count
    assert sheet.get("B1") == 1
    assert sheet.eval_count - before == 1


def test_parse_error_dependency_caches_and_only_relevant_edit_invalidates():
    # R3 makes non-derived formulas #PARSE!; R10 parse-error closure is itself,
    # irrelevant edits outside a dependent closure add 0, relevant edits recompute.
    sheet = Sheet()
    sheet.set("A1", "=1+")
    sheet.set("B1", "=A1+1")

    before = sheet.eval_count
    assert sheet.get("B1") == "#PARSE!"
    assert sheet.eval_count - before == 2

    sheet.set("C1", 123)
    before = sheet.eval_count
    assert sheet.get("B1") == "#PARSE!"
    assert sheet.eval_count - before == 0

    sheet.set("A1", "=1+")
    before = sheet.eval_count
    assert sheet.get("B1") == "#PARSE!"
    assert 1 <= sheet.eval_count - before <= 2


def test_range_cycle_propagates_to_dependent_and_repeat_read_is_cached():
    # R7 SUM visits ranges row-major, R9 range cycles produce #CYCLE!, and
    # dependents receive #CYCLE!; R10 caches error results.
    sheet = Sheet()
    sheet.set("A1", "=SUM(A1:A2)")
    sheet.set("A2", 5)
    sheet.set("B1", "=A1+1")

    before = sheet.eval_count
    assert sheet.get("B1") == "#CYCLE!"
    assert 1 <= sheet.eval_count - before <= 2

    before = sheet.eval_count
    assert sheet.get("B1") == "#CYCLE!"
    assert sheet.eval_count - before == 0
