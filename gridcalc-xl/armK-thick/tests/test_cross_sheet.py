import pytest

from gridcalc import Workbook
from gridcalc.formula import PARSE_ERROR, REF_ERROR


def _addresses(count):
    cells = []
    for col_ord in range(ord("A"), ord("Z") + 1):
        for row in range(1, 100):
            cells.append(f"{chr(col_ord)}{row}")
            if len(cells) == count:
                return cells
    return cells


def test_cross_sheet_formula_chain_counts_owning_sheets_and_caches():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", "=S2!A1+1")
    s2.set("A1", "=S1!B1+1")
    s1.set("B1", 10)

    assert s1.get("A1") == 12
    assert (s1.eval_count, s2.eval_count) == (1, 1)
    assert s1.get("A1") == 12
    assert (s1.eval_count, s2.eval_count) == (1, 1)

    s1.set("B1", 20)

    assert s1.get("A1") == 22
    assert (s1.eval_count, s2.eval_count) == (2, 2)


def test_cross_sheet_cycles_through_refs_and_ranges_propagate_cycle_error():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", "=SUM(S2!A1:A2)")
    s2.set("A1", 1)
    s2.set("A2", "=S1!A1+1")
    s1.set("B1", "=S1!A1+1")

    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A2") == "#CYCLE!"
    assert s1.get("B1") == "#CYCLE!"


def test_copied_formula_rebinds_unqualified_refs_and_names_to_destination_sheet():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 1)
    s1.set("B1", 10)
    s1.define_name("XX", "B1")
    s1.set("C1", "=A1+XX")
    s2.set("A1", 2)
    s2.set("B1", 20)
    s2.define_name("XX", "B1")

    s1.copy("C1", "S2!C1")

    assert s2.get("C1") == 22


def test_copy_accepts_qualified_arguments_and_rejects_bad_qualified_arguments_atomically():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 7)
    s2.set("B1", "old")

    s1.copy("S1!A1", "S2!B1")
    assert s2.get("B1") == 7
    s2.copy("S1!A1", "C1")
    assert s2.get("C1") == 7

    before = s2.get("B1")
    journal = list(wb._journal)
    for src, dst in (
        ("Missing!A1", "S2!D1"),
        ("S1!A1", "Missing!D1"),
        ("S1 ! A1", "S2!D1"),
        ("S1!A1", "S2 ! D1"),
    ):
        with pytest.raises(ValueError):
            s1.copy(src, dst)
        assert s2.get("B1") == before
        assert wb._journal == journal


def test_copy_shifts_in_grid_qualified_relative_refs_and_ranges_only():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("B2", 2)
    s2.set("C2", 3)
    s2.set("B3", 4)
    s2.set("C3", 5)
    s1.set("A1", "=S2!A1+SUM(S2!A1:B1)")

    s1.copy("A1", "B2")

    assert s1._cells["B2"] == "=S2!B2+SUM(S2!B2:C2)"
    assert s1.get("B2") == 7


def test_copy_shifts_qualified_refs_preserves_qualifiers_and_ref_errors_whole_ranges():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("Y98", "=S2!Z99 + SUM(S2!Y98:Z99) + S2!$Z$99")

    s1.copy("Y98", "Z99")


    assert s1._cells["Z99"] == "=#REF! + SUM(#REF!) + S2!$Z$99"
    assert s1.get("Z99") == REF_ERROR


def test_define_name_accepts_qualified_cell_and_range_targets():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("A1", 3)
    s2.set("A2", 4)

    s1.define_name("REMOTE", "S2!A1")
    s1.define_name("REMOTERANGE", "S2!A1:A2")
    s1.set("B1", "=REMOTE+SUM(REMOTERANGE)")

    assert s1.get("B1") == 10
    with pytest.raises(ValueError):
        s1.define_name("BADREMOTE", "Missing!A1")
    with pytest.raises(ValueError):
        s1.define_name("BADSPACE", "S2 ! A1")


def test_cross_sheet_left_to_right_short_circuit_does_not_reach_later_sheet():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s3 = wb.add_sheet("S3")
    s1.set("A1", '="text" + S2!A1 + S3!A1')
    s2.set("A1", "=1+1")
    s3.set("A1", "=1+1")

    assert s1.get("A1") == "#TYPE!"
    assert (s1.eval_count, s2.eval_count, s3.eval_count) == (1, 0, 0)


def test_cross_sheet_range_visits_row_major_for_error_precedence():
    wb = Workbook()
    local = wb.add_sheet("Local")
    remote = wb.add_sheet("Remote")
    remote.set("A1", 1)
    remote.set("B1", "=1/0")
    remote.set("A2", '="text"+1')
    remote.set("B2", 4)
    local.set("A1", "=SUM(Remote!A1:B2)")

    assert local.get("A1") == "#DIV!"


def test_cross_sheet_reached_formula_limit_counts_all_sheets():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    identities = [("S1" if i % 2 == 0 else "S2", addr) for i, addr in enumerate(_addresses(258))]
    for (sheet_name, addr), (next_sheet, next_addr) in zip(identities, identities[1:]):
        (s1 if sheet_name == "S1" else s2).set(addr, f"={next_sheet}!{next_addr}+1")
    last_sheet, last_addr = identities[-1]
    (s1 if last_sheet == "S1" else s2).set(last_addr, 0)

    assert s1.get("A1") == "#PARSE!"
    assert s1.eval_count + s2.eval_count == 256


def test_cross_sheet_long_closure_invalidates_without_recursion_error():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    cells = _addresses(1100)
    for addr, next_addr in zip(cells, cells[1:]):
        s2.set(addr, f"={next_addr}+1")
    s2.set(cells[-1], 1)
    s1.set("A1", "=IF(1,1,SUM(S2!A1:L99))")

    assert s1.get("A1") == 1
    formula_members = [
        identity for identity in s1._identity_closure_cache["A1"]
        if identity == ("S1", "A1") or identity[0] == "S2" and identity[1] in cells[:-1]
    ]
    assert len(formula_members) <= 256


def test_cross_sheet_cycle_through_qualified_name_marks_all_members_and_dependents():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.define_name("REMOTE", "S2!A1")
    s1.set("A1", "=REMOTE+1")
    s2.set("A1", "=S1!A1+1")
    s2.set("B1", "=A1+1")

    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A1") == "#CYCLE!"
    assert s2.get("B1") == "#CYCLE!"


def test_copy_shifts_qualified_refs_with_formula_whitespace_around_bang():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("B2", 4)
    s2.set("C2", 5)
    s1.set("A1", "=S2 ! A1 + SUM(S2 ! A1:B1)")

    s1.copy("A1", "B2")

    assert s1._cells["B2"] == "=S2 ! B2 + SUM(S2 ! B2:C2)"
    assert s1.get("B2") == 13


def test_copy_ref_errors_whole_qualified_ranges_with_formula_whitespace():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    wb.add_sheet("S2")
    s1.set("Y98", "=SUM(S2 ! Y98:Z99)")

    s1.copy("Y98", "Z99")

    assert s1._cells["Z99"] == "=SUM(#REF!)"
    assert s1.get("Z99") == REF_ERROR


def test_empty_single_reference_cells_evaluate_to_zero_across_sheets():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    wb.add_sheet("S2")
    s1.set("A1", "=S2!A1+1")

    assert s1.get("A1") == 1


def test_single_quoted_formula_strings_are_parse_errors():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "='not a string'")

    assert s1.get("A1") == PARSE_ERROR
