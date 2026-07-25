from gridcalc import Workbook


def test_cross_sheet_range_short_circuits_before_later_sheet_formula():
    """R7/R10/R23: qualified range visits row-major on owning sheet and stops at first error."""
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")

    s2.set("A1", "=1/0")
    s2.set("B1", "=1+1")
    s1.set("A1", "=SUM(S2!A1:B1)")

    assert s1.get("A1") == "#DIV!"
    assert s1.eval_count == 1
    assert s2.eval_count == 1


def test_cross_sheet_cycle_through_range_marks_cycle_and_dependent():
    """R9/R23: cycles may thread through qualified ranges and propagate to dependents."""
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")

    s1.set("A1", "=SUM(S2!A1:A1)")
    s2.set("A1", "=S1!A1")
    s2.set("B1", "=S1!A1+1")

    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A1") == "#CYCLE!"
    assert s2.get("B1") == "#CYCLE!"


def test_cross_sheet_copy_preserves_qualified_refs_but_rebinds_names_and_unqualified_refs():
    """R17/R18/R23: copied formula text shifts refs, preserves qualifiers, and host-binds names."""
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    other = wb.add_sheet("Other")

    s1.set("A1", 2)
    s2.set("B2", 3)
    s1.set("C3", 5)
    s2.set("D4", 7)
    other.set("C3", 11)
    s1.define_name("PAIR", "C3")
    s2.define_name("PAIR", "D4")
    s1.set("B2", "=A1 + Other!B2 + PAIR")

    s1.copy("B2", "S2!C3")

    assert s2.get("C3") == 21
