"""Task 4.1: Dependency closure and invalidation — R10 tests."""
import pytest

from gridcalc import Workbook


def _make_sheet():
    """Create a workbook with a single sheet named 'S'."""
    wb = Workbook()
    return wb.add_sheet("S")


def test_direct_reference_invalidates_dependent():
    """After editing a direct dependency, the dependent formula recomputes."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")

    # First get: evaluates B1.
    assert sheet.get("B1") == 11
    assert sheet.eval_count == 1

    # Edit A1 (in B1's closure).
    sheet.set("A1", 20)

    # B1 should recompute.
    assert sheet.get("B1") == 21
    assert sheet.eval_count == 2  # 1 for initial, 1 for recomputation


def test_range_members_invalidates_dependent():
    """After editing a range member, the SUM formula recomputes."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", 20)
    sheet.set("C1", "=SUM(A1:B1)")

    # First get: evaluates C1.
    assert sheet.get("C1") == 30
    assert sheet.eval_count == 1

    # Edit A1 (in C1's closure via range).
    sheet.set("A1", 100)

    # C1 should recompute.
    assert sheet.get("C1") == 120
    assert sheet.eval_count == 2


def test_count_range_members_invalidates_dependent():
    """After editing a COUNT range member, the COUNT formula recomputes."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", 20)
    sheet.set("C1", "=COUNT(A1:B1)")

    # First get: evaluates C1.
    assert sheet.get("C1") == 2
    assert sheet.eval_count == 1

    # Edit A1 (in C1's closure via COUNT range).
    sheet.set("A1", 30)

    # C1 should recompute (count is still 2, but eval_count increments).
    assert sheet.get("C1") == 2
    assert sheet.eval_count == 2


def test_transitive_dependencies_invalidates():
    """After editing a transitive dependency, the dependent formula recomputes."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")
    sheet.set("C1", "=B1+1")

    # First get: evaluates C1 (which evaluates B1).
    assert sheet.get("C1") == 12
    assert sheet.eval_count == 2  # 1 for B1, 1 for C1

    # Edit A1 (in C1's closure transitively).
    sheet.set("A1", 100)

    # C1 should recompute.
    assert sheet.get("C1") == 102
    assert sheet.eval_count == 4  # 2 for initial, 2 for recompute (B1 + C1)


def test_cycle_detection_prevents_infinite_loop():
    """Cycles are detected and both cells evaluate to #CYCLE!."""
    sheet = _make_sheet()
    sheet.set("A1", "=B1+1")
    sheet.set("B1", "=A1+1")

    # Both should evaluate to #CYCLE!.
    assert sheet.get("A1") == "#CYCLE!"
    assert sheet.get("B1") == "#CYCLE!"
    assert sheet.eval_count == 2  # 1 for A1, 1 for B1


def test_irrelevant_edit_does_not_recompute():
    """After editing a cell outside X's closure, get(X) returns cached value."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")
    sheet.set("C1", 999)  # unrelated cell

    # First get: evaluates B1.
    assert sheet.get("B1") == 11
    assert sheet.eval_count == 1

    # Edit C1 (not in B1's closure).
    before = sheet.eval_count
    sheet.set("C1", 888)
    assert sheet.get("B1") == 11  # should return cached value
    assert sheet.eval_count == before  # no recomputation


def test_identical_write_still_invalidates():
    """Writing content identical to existing content still counts as relevant."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")

    # First get: evaluates B1.
    assert sheet.get("B1") == 11
    assert sheet.eval_count == 1

    # Write the same formula again.
    sheet.set("B1", "=A1+1")

    # B1 should recompute (even though the formula is identical).
    assert sheet.get("B1") == 11
    assert sheet.eval_count == 2  # incremented despite identical formula


def test_large_range_does_not_expand_during_closure():
    """Invalid huge ranges like SUM(A1:A999999999) should not expand."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    # A999999999 is an invalid address (row > 99), so the range is invalid.
    sheet.set("B1", "=SUM(A1:A999999999)")

    # Should return #REF! without expanding the range.
    assert sheet.get("B1") == "#REF!"
    assert sheet.eval_count == 1


def test_eval_count_delta_matches_formula_cells_in_closure():
    """After relevant edit, eval_count delta equals number of formula cells in closure."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")
    sheet.set("C1", "=B1+1")

    # First get: evaluates C1 (which evaluates B1).
    assert sheet.get("C1") == 12
    assert sheet.eval_count == 2

    # Edit A1 (in C1's closure).
    sheet.set("A1", 100)

    # C1 should recompute, and the delta should equal the number of formula
    # cells in C1's closure (B1 and C1 = 2).
    before = sheet.eval_count
    assert sheet.get("C1") == 102
    delta = sheet.eval_count - before
    assert delta == 2  # B1 and C1 both recomputed


def test_formula_cell_in_range_member_closure():
    """Formula cells in range members are included in closure."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")  # formula cell
    sheet.set("C1", "=SUM(A1:B1)")

    # First get: evaluates C1 (which evaluates B1).
    assert sheet.get("C1") == 21  # 10 + 11
    assert sheet.eval_count == 2  # 1 for B1, 1 for C1

    # Edit A1 (in C1's closure via B1).
    sheet.set("A1", 100)

    # C1 should recompute: SUM(A1:B1) = A1 + B1 = 100 + 101 = 201.
    assert sheet.get("C1") == 201
    assert sheet.eval_count == 4  # 2 for initial, 2 for recompute


def test_multiple_dependents_invalidated():
    """After editing a cell, all dependents are invalidated."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+1")
    sheet.set("C1", "=A1+2")

    # First get: evaluates B1 and C1.
    assert sheet.get("B1") == 11
    assert sheet.get("C1") == 12
    assert sheet.eval_count == 2

    # Edit A1.
    sheet.set("A1", 100)

    # Both B1 and C1 should recompute.
    assert sheet.get("B1") == 101
    assert sheet.get("C1") == 102
    assert sheet.eval_count == 4  # 2 for initial, 2 for recompute


def test_literal_string_cell_not_affected_by_formula_edit():
    """Editing a formula cell does not affect literal string cells."""
    sheet = _make_sheet()
    sheet.set("A1", "hello")
    sheet.set("B1", 10)
    sheet.set("C1", "=B1+1")

    # First get: evaluates C1.
    assert sheet.get("C1") == 11
    assert sheet.eval_count == 1

    # Edit A1 (literal string, not in C1's closure).
    before = sheet.eval_count
    sheet.set("A1", "world")
    assert sheet.get("C1") == 11  # should return cached value
    assert sheet.eval_count == before  # no recomputation


def test_unary_minus_operand_in_closure():
    """A formula using unary minus on a reference includes the operand in its closure."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=-A1")

    # First get: evaluates B1.
    assert sheet.get("B1") == -10
    assert sheet.eval_count == 1

    # Edit A1 (operand of unary minus in B1's closure).
    sheet.set("A1", 100)

    # B1 should recompute.
    assert sheet.get("B1") == -100
    assert sheet.eval_count == 2


def test_parse_error_formula_contributes_no_refs():
    """A formula that fails to parse contributes no refs to the closure."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=+++")  # parse error

    # B1 evaluates to #PARSE!.
    assert sheet.get("B1") == "#PARSE!"
    assert sheet.eval_count == 1

    # Edit A1 (should NOT invalidate B1 since parse error contributes no refs).
    before = sheet.eval_count
    sheet.set("A1", 999)
    assert sheet.get("B1") == "#PARSE!"
    assert sheet.eval_count == before  # no recomputation


def test_invalid_range_contributes_no_refs():
    """A formula with an invalid range (e.g. row > 99) contributes no refs."""
    sheet = _make_sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=SUM(A1:A999)")  # A999 has row 999 > 99, invalid

    # B1 evaluates to #REF!.
    assert sheet.get("B1") == "#REF!"
    assert sheet.eval_count == 1

    # Edit A1 (should NOT invalidate B1 since invalid range contributes no refs).
    before = sheet.eval_count
    sheet.set("A1", 999)
    assert sheet.get("B1") == "#REF!"
    assert sheet.eval_count == before  # no recomputation
