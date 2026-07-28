from gridcalc import Sheet


def test_set_never_changes_eval_count():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    before = s.eval_count
    s.set("C1", "=B1+1")  # formula set, still shouldn't evaluate anything
    assert s.eval_count == before


def test_eval_count_rises_by_one_per_formula_cell_started():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.set("C1", "=B1+1")
    assert s.eval_count == 0
    s.get("C1")
    assert s.eval_count == 2  # B1 and C1 each started once; A1 is a literal


def test_literal_and_empty_reads_add_zero():
    s = Sheet()
    s.set("A1", 1)
    s.get("A1")
    s.get("Z9")
    assert s.eval_count == 0


def test_repeat_read_adds_zero_for_values_and_errors():
    s = Sheet()
    s.set("A1", "=1+1")
    s.get("A1")
    count_after_first = s.eval_count
    s.get("A1")
    assert s.eval_count == count_after_first

    s.set("B1", "=a1")  # #PARSE!
    s.get("B1")
    after_parse = s.eval_count
    s.get("B1")
    assert s.eval_count == after_parse

    s.set("C1", "=C1")  # #CYCLE!
    s.get("C1")
    after_cycle = s.eval_count
    s.get("C1")
    assert s.eval_count == after_cycle


def test_short_circuit_never_starts_later_operand():
    s = Sheet()
    s.set("Y1", "=1+1")
    s.set("X1", "=1/0+Y1")
    s.get("X1")
    assert s.eval_count == 1  # only X1 started; Y1 never touched


def test_range_short_circuit_excludes_later_members():
    s = Sheet()
    s.set("A1", "=1/0")  # first in row-major order
    s.set("B1", "=1+1")  # would come after A1; must not be started
    s.set("Q1", "=SUM(A1:B1)")
    s.get("Q1")
    assert s.eval_count == 2  # Q1 + A1 only


def test_count_never_increments_for_range_members():
    s = Sheet()
    s.set("A1", "=1+1")
    s.set("B1", "=2+2")
    s.set("Q1", "=COUNT(A1:B1)")
    s.get("Q1")
    assert s.eval_count == 1  # only Q1 itself
