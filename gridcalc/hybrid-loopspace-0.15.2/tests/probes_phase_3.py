from gridcalc import Sheet


def test_function_primary_composes_with_comparison_and_short_circuits_errors():
    # R3 function calls are primaries; R4/R5 require left-to-right error precedence.
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("A2", 2)
    sheet.set("B1", "=SUM(A1:A2) * 2 >= MAX(A1:A2) + 4")
    sheet.set("C1", "=SUM(A1:A2) / 0 + MAX(A1:A2)")

    assert sheet.get("B1") == 1
    assert sheet.get("C1") == "#DIV!"


def test_count_is_structural_and_does_not_evaluate_or_cycle():
    # R8 COUNT counts non-empty cells, including formulas and strings, without evaluating them.
    sheet = Sheet()
    sheet.set("A1", "=COUNT(A1:C1)")
    sheet.set("B1", "#DIV!")
    sheet.set("C1", "=1/0")

    assert sheet.get("A1") == 3


def test_range_row_major_first_error_beats_later_cycle():
    # R7 visits row-major and the first error wins; R9 cycle only matters if reached.
    sheet = Sheet()
    sheet.set("A1", "text")
    sheet.set("B1", "=SUM(A1:B1)")

    assert sheet.get("B1") == "#TYPE!"


def test_range_row_major_cycle_propagates_when_first_error():
    # R7/R9 together: a cycle reached through SUM is the range result and propagates.
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=SUM(A1:B1)")

    assert sheet.get("B1") == "#CYCLE!"
    assert sheet.get("A1") == "#CYCLE!"
