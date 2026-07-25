from gridcalc import Workbook


def test_cross_sheet_first_error_short_circuits_later_sheet_formula():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")

    s2.set("A1", "=1/0")
    s2.set("B1", "=99")
    s1.set("A1", "=S2!A1 + S2!B1")

    assert s1.get("A1") == "#DIV!"
    assert s2.eval_count == 1


def test_cycle_crosses_qualified_range_and_propagates_to_dependent():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")

    s1.set("A1", "=SUM(S2!A1:A2)")
    s1.set("B1", "=S1!A1+1")
    s2.set("A1", 1)
    s2.set("A2", "=S1!A1")

    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A2") == "#CYCLE!"
    assert s1.get("B1") == "#CYCLE!"


def test_absent_qualified_reference_recomputes_after_sheet_is_added():
    wb = Workbook()
    s1 = wb.add_sheet("S1")

    s1.set("A1", "=Ghost!A1+1")
    assert s1.get("A1") == "#REF!"
    before = s1.eval_count

    ghost = wb.add_sheet("Ghost")
    ghost.set("A1", 4)

    assert s1.get("A1") == 5
    assert s1.eval_count == before + 1


def test_cross_sheet_copy_rebinds_names_and_shifts_qualified_refs():
    wb = Workbook()
    src = wb.add_sheet("Src")
    dst = wb.add_sheet("Dst")
    other = wb.add_sheet("Other")

    src.define_name("VAL", "A1")
    dst.define_name("VAL", "B1")
    src.set("A1", 10)
    dst.set("B1", 20)
    other.set("B2", 7)
    src.set("A1", "=VAL + Other!A1")

    src.copy("Src!A1", "Dst!B2")

    assert dst.get("B2") == 27
