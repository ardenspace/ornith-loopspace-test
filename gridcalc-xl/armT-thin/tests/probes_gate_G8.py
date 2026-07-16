# Gate G8 probes — R21/R22/R23, derived fresh from the spec.
# Cross-cuts: G3 (cycles), G4 (R10 counters), G6 (copy/names), G7 (undo/redo).
import pytest

import gridcalc
from gridcalc import Workbook


def _pub(obj):
    return {a for a in dir(obj) if not a.startswith("_")}


# P1 — R21: workbook root, empty start, exact public surface.
def test_p1_workbook_root_and_api_surface():
    assert gridcalc.__all__ == ["Workbook"]
    wb = Workbook()
    assert wb.sheet_names == []
    assert wb.clock == 0
    assert wb.undo() is False
    assert wb.redo() is False
    # Zero-to-value four-liner (User Lens / R21).
    s = wb.add_sheet("S1")
    s.set("A1", "=1+1")
    assert s.get("A1") == 2
    # Exact public surface (R21: "nothing else is public API").
    assert _pub(wb) == {
        "add_sheet", "sheet", "sheet_names", "undo", "redo",
        "advance_clock", "clock", "to_json", "from_json",
    }
    assert _pub(s) == {"set", "get", "copy", "define_name", "eval_count"}
    # sheet_names is a fresh list each call.
    lst = wb.sheet_names
    lst.append("XX")
    assert wb.sheet_names == ["S1"]
    # str subclass sheet name accepted, normalized to plain str (R21/R2).
    class MyStr(str):
        pass
    wb.add_sheet(MyStr("Sub"))
    names = wb.sheet_names
    assert names == ["S1", "Sub"]
    assert all(type(n) is str for n in names)


# P1b — R21: sheet-name validation and case-sensitivity.
def test_p1b_sheet_name_validation():
    wb = Workbook()
    wb.add_sheet("S1")
    for bad in (5, None, b"S", "", "a" * 33, "1abc", "_abc", "ab-c", "ab c", "S1"):
        with pytest.raises(ValueError):
            wb.add_sheet(bad)
    # Case-sensitive: "s1" is a distinct, legal name; 1 and 32 chars legal.
    wb.add_sheet("s1")
    wb.add_sheet("A")
    wb.add_sheet("Z" * 32)
    assert wb.sheet_names == ["S1", "s1", "A", "Z" * 32]
    with pytest.raises(ValueError):
        wb.sheet("nope")
    # Handle address arguments are always unqualified (R21/R1).
    s = wb.sheet("S1")
    with pytest.raises(ValueError):
        s.get("s1!A1")
    with pytest.raises(ValueError):
        s.set("s1!A1", 1)


# P2 — R21 × G7: eval_count is kept per sheet *name* for the workbook's
# lifetime — fresh add_sheet and redo-restore both resume the counter.
def test_p2_eval_count_resumes_per_name():
    wb = Workbook()
    u = wb.add_sheet("U")
    u.set("A1", "=1+1")
    assert u.get("A1") == 2
    assert u.eval_count == 1
    assert wb.undo() is True   # revert set
    assert wb.undo() is True   # revert add_sheet
    with pytest.raises(ValueError):
        u.eval_count           # handle to a missing sheet (R19)
    assert wb.sheet_names == []
    h = wb.add_sheet("U")      # fresh add under the same name
    assert h.eval_count == 1   # counter resumes (R21)
    assert u.eval_count == 1   # old handle rebinds by name (R19)


def test_p2b_eval_count_resumes_across_redo():
    wb = Workbook()
    u = wb.add_sheet("U")
    u.set("A1", "=1+1")
    assert u.get("A1") == 2
    assert u.eval_count == 1
    wb.undo()                  # set
    wb.undo()                  # add_sheet
    assert wb.redo() is True   # restore sheet U
    assert u.eval_count == 1   # resumed, monotonic (R20/R21)
    assert wb.redo() is True   # restore the set — an edit at A1 (R20)
    assert u.get("A1") == 2
    assert u.eval_count == 2   # relevant edit → recompute exactly A1


# P3 — R22: qualifier grammar, tokenization precedence, existence boundary.
def test_p3_qualified_ref_grammar_and_precedence():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("B1", 7)
    s1.set("A1", "=S2!B1")
    assert s1.get("A1") == 7
    # Whitespace (spaces/tabs) around ! is legal (R3/R22).
    s1.set("A2", "=S2 !\tB1")
    assert s1.get("A2") == 7
    # An identifier followed by ! is a SHEET token even when it matches a
    # function name or the REF shape (R22 precedence).
    fsum = wb.add_sheet("SUM")
    fsum.set("B2", 9)
    s1.set("A3", "=SUM!B2")
    assert s1.get("A3") == 9
    ref_shaped = wb.add_sheet("B2")
    ref_shaped.set("C1", 3)
    s1.set("A4", "=B2!C1")
    assert s1.get("A4") == 3
    # No sheet named A1: SHEET-token precedence still wins over REF —
    # well-shaped qualifier, nonexistent sheet → #REF! (not #PARSE!).
    s1.set("A5", "=A1!B2")
    assert s1.get("A5") == "#REF!"
    # An identifier that cannot be a sheet name followed by ! → #PARSE!.
    s1.set("A6", "=_X!A1")
    assert s1.get("A6") == "#PARSE!"
    s1.set("A7", "=Ghost!A1")
    assert s1.get("A7") == "#REF!"
    # Lowercase sheet names are legal and matched case-sensitively.
    lo = wb.add_sheet("data")
    lo.set("A1", 5)
    s1.set("A8", "=data!A1")
    assert s1.get("A8") == 5
    s1.set("A9", "=DATA!A1")
    assert s1.get("A9") == "#REF!"


def test_p3b_qualified_ranges():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    for addr, v in (("A1", 1), ("B1", 2), ("A2", 3), ("B2", 4)):
        s2.set(addr, v)
    s1.set("C1", "=SUM(S2!A1:B2)")
    assert s1.get("C1") == 10
    s1.set("C2", "=SUM( S2 ! A1 : B2 )")
    assert s1.get("C2") == 10
    # A qualifier binds the whole range; a second qualifier is #PARSE!.
    s1.set("C3", "=SUM(S1!A1:S2!B2)")
    assert s1.get("C3") == "#PARSE!"
    s1.set("C4", "=SUM(A1:S2!B2)")
    assert s1.get("C4") == "#PARSE!"


# P4 — R22 × R10 (cross-cut G4): add_sheet (and its undo/redo) is an edit
# touching every formula cell mentioning that qualifier; other adds are
# irrelevant (+0).
def test_p4_add_sheet_is_edit_touching_qualifier_mentions():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "=NEWS!A1")
    assert s1.get("A1") == "#REF!"
    assert s1.eval_count == 1
    wb.add_sheet("NEWS")            # mutating op: never evaluates (R10)
    assert s1.eval_count == 1
    assert s1.get("A1") == 0        # empty NEWS!A1 contributes int 0 (R6)
    assert s1.eval_count == 2       # relevant edit: ≥1 and ≤ closure size 1
    assert wb.undo() is True        # remove NEWS again
    assert s1.get("A1") == "#REF!"
    assert s1.eval_count == 3
    assert wb.redo() is True        # restore NEWS
    assert s1.get("A1") == 0
    assert s1.eval_count == 4
    wb.add_sheet("OTHER")           # touches only qualifier OTHER mentions
    assert s1.get("A1") == 0        # irrelevant edit → +0
    assert s1.eval_count == 4


# P5 — R23 × G3/G4: cycles thread across sheets; each computation
# increments the owning sheet's counter.
def test_p5_cross_sheet_cycle_and_counter_ownership():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", "=S2!A1")
    s2.set("A1", "=S1!A1")
    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A1") == "#CYCLE!"

    wb2 = Workbook()
    t1 = wb2.add_sheet("S1")
    t2 = wb2.add_sheet("S2")
    t1.set("A1", "=S2!B1")
    t2.set("B1", "=2*3")
    assert t1.get("A1") == 6
    assert t1.eval_count == 1
    assert t2.eval_count == 1


# P6 — R23/R17/R22 (cross-cut G6): copy shifts the REF part, never the
# qualifier. Decoy sheet T3 holds different values so a Δ-shifted
# qualifier (S2→T3 under Δ(+1,+1)) produces a visibly wrong value.
def test_p6_copy_shifts_ref_never_qualifier():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    t3 = wb.add_sheet("T3")
    s2.set("B1", 5)
    s2.set("C2", 55)
    t3.set("C2", 99)
    t3.set("B1", 91)
    s1.set("D1", "=S2!B1")
    s1.copy("D1", "E2")             # Δ(+1,+1) → must become =S2!C2
    assert s1.get("E2") == 55
    # $-pinned qualified ref: both components kept, qualifier kept.
    s1.set("D2", "=S2!$B$1")
    s1.copy("D2", "E3")
    assert s1.get("E3") == 5
    # Qualified range: endpoints shift, qualifier does not.
    for addr, v in (("B2", 10), ("C2", 20), ("B3", 30), ("C3", 40)):
        s2.set(addr, v)
    for addr in ("B2", "C2", "B3", "C3"):
        t3.set(addr, 7)
    s1.set("F1", "=SUM(S2!A1:B2)")
    s1.copy("F1", "G2")             # Δ(+1,+1) → =SUM(S2!B2:C3)
    assert s1.get("G2") == 10 + 20 + 30 + 40


def test_p6b_copy_out_of_grid_replaces_whole_qualified_token():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    wb.add_sheet("S2")
    s1.set("A1", "=S2!A99")
    s1.copy("A1", "A2")             # Δrow +1 → row 100 → whole token #REF!
    assert s1.get("A2") == "#REF!"  # =S2!#REF! would be #PARSE!
    s1.set("B1", "=S2!Z1")
    s1.copy("B1", "C1")             # Δcol +1 → past Z → #REF!
    assert s1.get("C1") == "#REF!"
    # Qualified range with an endpoint leaving the grid: whole range → #REF!.
    s1.set("D1", "=SUM(S2!Y1:Z2)+1")
    s1.copy("D1", "E1")
    assert s1.get("E1") == "#REF!"


# P7 — R23: qualified copy/define_name arguments; cross-sheet copy
# re-resolves unqualified refs and NAMEs on the destination sheet (× G6/R18).
def test_p7_qualified_args_and_reresolution():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("B1", 5)
    s1.copy("S2!B1", "A5")          # qualified src
    assert s1.get("A5") == 5
    s1.copy("A5", "S2!D9")          # qualified dst
    assert s2.get("D9") == 5
    # Argument shape is exactly SHEET!ADDR with no whitespace; unknown
    # sheet → ValueError, no state change.
    with pytest.raises(ValueError):
        s1.copy("Nope!A1", "A1")
    with pytest.raises(ValueError):
        s1.copy("S2 !B1", "A1")
    with pytest.raises(ValueError):
        s1.copy("A5", "S2! D1")
    # NAME re-resolution on the destination sheet.
    s1.set("B5", 42)
    s1.define_name("NN", "B5")
    s1.set("C1", "=NN")
    assert s1.get("C1") == 42
    s1.copy("C1", "S2!C1")
    assert s2.get("C1") == "#NAME!"  # NN undefined on S2 (R18/R23)
    s2.set("B7", 13)
    s2.define_name("NN", "B7")       # edit touching S2 mentions of NN
    assert s2.get("C1") == 13
    # Unqualified REFs re-resolve to the destination sheet too.
    s1.set("C2", "=B5")
    s1.copy("C2", "S2!C2")
    assert s2.get("C2") == 0         # S2!B5 is empty → 0 (R6)


def test_p7b_define_name_qualified_target():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("A1", 2)
    s2.set("B1", 3)
    s1.define_name("REMOTE", "S2!A1:B1")
    s1.set("F1", "=SUM(REMOTE)")
    assert s1.get("F1") == 5
    with pytest.raises(ValueError):
        s1.define_name("BAD", "Nope!A1")
    with pytest.raises(ValueError):
        s1.define_name("BAD", "S2! A1")
    assert s1.get("F1") == 5
