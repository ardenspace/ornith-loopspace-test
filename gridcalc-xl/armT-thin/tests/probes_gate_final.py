"""Final completion-gate probes — derived from the frozen spec alone.

One scenario per acceptance group G1-G10 plus cross-group integration
scenarios X1/X2, each asserting input -> spec-dictated output with R-ids.
"""

import json

import pytest

import gridcalc
from gridcalc import Workbook


def fresh_sheet(name="S1"):
    wb = Workbook()
    return wb, wb.add_sheet(name)


# ---------------------------------------------------------------- G1: R1/R2
def test_g1_store_validation_and_replacement():
    wb, s = fresh_sheet()
    # R1: invalid addresses raise ValueError, state unchanged
    for bad in ["A01", "a1", "A0", "A100", "AA1", "", " A1", "S1!A1"]:
        with pytest.raises(ValueError):
            s.set(bad, 1)
        with pytest.raises(ValueError):
            s.get(bad)
    with pytest.raises(ValueError):
        s.get(5)
    with pytest.raises(ValueError):
        s.get(None)
    # R2: bool raw rejected despite int subclass
    with pytest.raises(ValueError):
        s.set("A1", True)
    # R2: never-set -> None; failed set left it never-set
    assert s.get("A1") is None
    # R2: int subclass normalized to plain int
    class MyInt(int):
        pass
    s.set("A1", MyInt(5))
    v = s.get("A1")
    assert v == 5 and type(v) is int
    # R2: replacement
    s.set("A1", "hello")
    assert s.get("A1") == "hello"
    # R2: other types rejected, state unchanged
    with pytest.raises(ValueError):
        s.set("A1", 1.5)
    assert s.get("A1") == "hello"


# ------------------------------------------------------------ G2: R3/R4/R5/R6
def test_g2_grammar_division_errors_refs():
    wb, s = fresh_sheet()
    s.set("B1", "=7/-2")
    assert s.get("B1") == -3  # R4 trunc toward zero
    s.set("B2", "=-7/2")
    assert s.get("B2") == -3  # R4
    s.set("B3", "=1/0")
    assert s.get("B3") == "#DIV!"  # R4
    s.set("B4", "=A0")
    assert s.get("B4") == "#REF!"  # R6 non-grid REF
    s.set("B5", "=A01")
    assert s.get("B5") == "#REF!"  # R6 leading-zero digits
    s.set("B6", "=FOO")
    assert s.get("B6") == "#NAME!"  # R3 NAME classification
    s.set("B7", "=AA1")
    assert s.get("B7") == "#NAME!"  # R3
    s.set("B8", "=F")
    assert s.get("B8") == "#PARSE!"  # R3 single letter is neither shape
    s.set("B9", "=1<2<3")
    assert s.get("B9") == 1  # R3 left-assoc comparisons -> (1<2)<3
    s.set("C1", "=007")
    assert s.get("C1") == 7  # R3 INT leading zeros
    s.set("C2", "=")
    assert s.get("C2") == "#PARSE!"  # R3 empty formula
    s.set("C3", "=1 < = 2")
    assert s.get("C3") == "#PARSE!"  # R3 no whitespace inside <=
    # R6: empty-cell single reference contributes 0
    s.set("C4", "=Z99+1")
    assert s.get("C4") == 1
    # R5: first error in textual left-to-right order wins
    s.set("D1", "=A0+1/0")
    assert s.get("D1") == "#REF!"


# --------------------------------------------------------------- G3: R7/R8/R9
def test_g3_ranges_functions_cycles():
    wb, s = fresh_sheet()
    s.set("A1", 1)
    s.set("B1", 2)
    s.set("A2", 3)
    s.set("C1", "=SUM(A1:B2)")
    assert s.get("C1") == 6  # R8 empty B2 contributes nothing
    s.set("C2", "=SUM(A2:A1)")
    assert s.get("C2") == "#REF!"  # R7 row-only mis-order
    s.set("C3", "=SUM(B1:A1)")
    assert s.get("C3") == "#REF!"  # R7 col-only mis-order
    s.set("C4", "=MIN(D5:D9)")
    assert s.get("C4") == "#TYPE!"  # R8 MIN on all-empty range
    s.set("C5", "=SUM(D5:D9)")
    assert s.get("C5") == 0  # R8 SUM on all-empty range
    # R8: COUNT structural, no self-cycle
    s.set("D1", "=COUNT(D1:D1)")
    assert s.get("D1") == 1
    # R9: mutual cycle
    s.set("E1", "=E2")
    s.set("E2", "=E1")
    assert s.get("E1") == "#CYCLE!"
    assert s.get("E2") == "#CYCLE!"
    # R9: off-cycle dependent receives #CYCLE! by propagation
    s.set("E3", "=E1+1")
    assert s.get("E3") == "#CYCLE!"


# ------------------------------------------------------------ G4: R10/R11/R12
def test_g4_incremental_counters_and_bounds():
    wb, s = fresh_sheet()
    s.set("C1", 1)
    s.set("B1", "=C1+1")
    assert s.eval_count == 0  # R10 mutating ops never evaluate
    assert s.get("B1") == 2
    assert s.eval_count == 1  # R10 one formula start
    before = s.eval_count
    assert s.get("B1") == 2
    assert s.eval_count == before  # R10 repeat read +0
    s.set("D9", 99)  # irrelevant edit: D9 not in B1's closure
    assert s.get("B1") == 2
    assert s.eval_count == before  # R10 irrelevant edit +0
    s.set("C1", 5)  # relevant edit
    assert s.get("B1") == 6  # R11 value matches naive recompute
    assert s.eval_count >= before + 1  # R10 relevant edit >= 1
    # R12: ~500-deep unary-minus tower within 512 chars completes
    wb2, t = fresh_sheet()
    tower = "=" + "-" * 500 + "1"
    assert len(tower) <= 513
    t.set("A1", tower)
    assert t.get("A1") == 1  # even count of minus


# ------------------------------------------------------------ G5: R13/R14/R15
def test_g5_strings_concat_len_if():
    wb, s = fresh_sheet()
    s.set("A1", '="a"<"b"')
    assert s.get("A1") == "#TYPE!"  # R13 orderings need int
    s.set("A2", '="x"="x"')
    assert s.get("A2") == 1  # R13 str equality
    s.set("A3", '="x"<>"y"')
    assert s.get("A3") == 1
    s.set("A4", '=1="1"')
    assert s.get("A4") == "#TYPE!"  # R13 mixed comparison
    s.set("A5", '=-"x"')
    assert s.get("A5") == "#TYPE!"  # R13 unary minus needs int
    s.set("B1", '=CONCAT(007,"a")')
    assert s.get("B1") == "7a"  # R14 decimal rendering of the value
    s.set("B2", "=CONCAT(Z99)")
    assert s.get("B2") == "0"  # R14 empty-ref arg renders "0"
    s.set("B3", "=LEN(-12)")
    assert s.get("B3") == 3  # R14
    s.set("B4", '=LEN("")')
    assert s.get("B4") == 0
    # R15: unselected branch never evaluated, its error invisible
    s.set("C2", "=1/0")
    warm_counts = None
    s.set("C1", "=IF(1,2,C2)")
    before = s.eval_count
    assert s.get("C1") == 2
    assert s.eval_count == before + 1  # only C1 started, C2 untouched (R15/R10)
    s.set("C3", '=IF("s",1,2)')
    assert s.get("C3") == "#TYPE!"  # R15 str condition


# ------------------------------------------------------------ G6: R16/R17/R18
def test_g6_absolute_refs_copy_names():
    wb, s = fresh_sheet()
    s.set("B1", 5)
    s.set("A1", "=$B$1+B1")
    assert s.get("A1") == 10  # R16 $ transparent to evaluation
    s.copy("A1", "A2")
    # R17: pinned $B$1 kept, plain B1 shifted to B2 (empty -> 0)
    assert s.get("A2") == 5
    # R17: plain shift with both deltas
    s.set("C1", "=B1")
    s.copy("C1", "D3")  # dcol=+1, drow=+2: B1 -> C3
    s.set("C3", 11)
    assert s.get("D3") == 11
    s.set("D1", "=A1")
    s.copy("D1", "C2")  # dcol=-1, drow=+1: A1 -> col before A = off grid
    assert s.get("C2") == "#REF!"
    # R17: copy never evaluates; ValueError on empty src
    with pytest.raises(ValueError):
        s.copy("Z98", "Z99")
    # R18: names
    wb2, t = fresh_sheet()
    t.set("B2", 7)
    t.define_name("NM", "B2")
    t.set("A1", "=NM")
    assert t.get("A1") == 7  # NAME as primary, 1x1 target
    t.set("A2", "=SUM(NM)")
    assert t.get("A2") == 7  # NAME as RANGE-ARG
    t.set("A3", "=UNDEF_X")
    assert t.get("A3") == "#NAME!"  # R18 undefined NAME
    with pytest.raises(ValueError):
        t.define_name("SUM", "B2")  # R18 function names rejected
    with pytest.raises(ValueError):
        t.define_name("NM", "B2:A1")  # R18 mis-ordered target


# --------------------------------------------------------------- G7: R19/R20
def test_g7_undo_redo_journal():
    wb = Workbook()
    s = wb.add_sheet("S1")
    # add_sheet is journaled (R19); the nothing-to-undo case needs a fresh workbook
    wb2 = Workbook()
    assert wb2.undo() is False
    assert wb2.redo() is False
    s.set("A1", 5)
    s.set("A1", 6)
    assert wb.undo() is True
    assert s.get("A1") == 5  # R19 exact restore
    assert wb.undo() is True
    assert s.get("A1") is None  # R19 never-set state restored
    assert wb.redo() is True
    assert s.get("A1") == 5
    s.set("B1", 1)  # new journaled op clears redo
    assert wb.redo() is False  # R19
    # R19: failed calls never journal
    before_a1 = s.get("A1")
    with pytest.raises(ValueError):
        s.set("A0", 3)
    assert wb.undo() is True  # undoes set B1, not the failed call
    assert s.get("A1") == before_a1
    # R20: counters monotonic across undo/redo
    counts = s.eval_count
    wb.undo()
    wb.redo()
    assert s.eval_count >= counts


# ------------------------------------------------------------ G8: R21/R22/R23
def test_g8_workbook_multisheet():
    assert gridcalc.__all__ == ["Workbook"]  # R21
    wb = Workbook()
    assert wb.sheet_names == []
    with pytest.raises(ValueError):
        wb.add_sheet("1bad")  # R21 must start with a letter
    with pytest.raises(ValueError):
        wb.add_sheet(3)
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    with pytest.raises(ValueError):
        wb.add_sheet("S1")  # duplicate
    assert wb.sheet_names == ["S1", "S2"]  # creation order
    names = wb.sheet_names
    names.append("X")
    assert wb.sheet_names == ["S1", "S2"]  # R21 fresh list each call
    s2.set("B1", 42)
    s1.set("A1", "=S2!B1")
    assert s1.get("A1") == 42  # R22 qualified ref
    s1.set("A2", "=SUM!A1")
    assert s1.get("A2") == "#REF!"  # R22 SHEET-token precedence; no such sheet
    s1.set("A3", "=Ghost!A1")
    assert s1.get("A3") == "#REF!"  # R22 well-shaped, nonexistent
    s1.set("A4", "=S1!A5:S2!B2")
    assert s1.get("A4") == "#PARSE!"  # R22 second qualifier in a range
    # R23: cross-sheet cycle
    s1.set("C1", "=S2!C1")
    s2.set("C1", "=S1!C1")
    assert s1.get("C1") == "#CYCLE!"


# --------------------------------------------------------------- G9: R24/R25
def test_g9_persistence_round_trip():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 5)
    s1.set("A2", 'line"less')
    s1.set("B1", "=$A$1+S2!B2")
    s2.set("B2", 10)
    s1.define_name("NM", "A1")
    s1.set("B2", "=NM")
    wb.advance_clock()
    text = wb.to_json()
    assert isinstance(text, str)
    json.loads(text)  # R24 json.loads accepts it
    w2 = Workbook.from_json(text)
    assert w2.sheet_names == ["S1", "S2"]  # R24 names + creation order
    assert w2.clock == 1  # R24 clock restored
    t1 = w2.sheet("S1")
    assert t1.eval_count == 0  # R24 counters reset
    assert w2.undo() is False  # R24 journal reset
    assert t1.get("B1") == 15  # R25 same values ($ text preserved)
    assert t1.get("B2") == 5  # R24 bindings restored
    assert t1.get("A2") == 'line"less'
    assert t1.eval_count >= 1  # R24 fresh compute on first get
    # R24: rejection cases
    with pytest.raises(ValueError):
        Workbook.from_json(123)
    with pytest.raises(ValueError):
        Workbook.from_json("not json {")
    with pytest.raises(ValueError):
        Workbook.from_json("null")
    with pytest.raises(ValueError):
        Workbook.from_json('{"version": 1.0, "clock": 0, "sheets": []}')


# ------------------------------------------------------------ G10: R26/R27/R28
def test_g10_clock_now_volatility():
    wb = Workbook()
    s = wb.add_sheet("S1")
    assert wb.clock == 0  # R26
    s.set("A1", "=NOW()")
    s.set("A2", "=NOW(1)")
    assert s.get("A2") == "#PARSE!"  # R26 NOW takes no args
    s.set("A3", "=SUM()")
    assert s.get("A3") == "#PARSE!"  # R26 empty parens elsewhere stay illegal
    assert s.get("A1") == 0
    assert wb.advance_clock() == 1  # R26 returns new value
    assert wb.clock == 1
    assert s.get("A1") == 1  # R27 matches naive recompute at current clock
    # R27 warm volatile bound: exactly the volatile cells recompute
    s.set("B1", 3)
    s.set("B2", "=B1+1")  # non-volatile
    s.get("B2")
    s.get("A1")
    before = s.eval_count
    wb.advance_clock()
    assert s.eval_count == before  # R10 mutating op evaluates nothing
    assert s.get("B2") == 4
    assert s.eval_count == before  # R27 clock edit irrelevant to non-volatile
    assert s.get("A1") == 2
    assert s.eval_count == before + 1  # R27 warm volatile: at most 1, value forces >=1
    # R27: NOW inside a STRING literal is text, not a call
    s.set("C1", '="NOW()"')
    s.get("C1")
    before = s.eval_count
    wb.advance_clock()
    assert s.get("C1") == "NOW()"
    assert s.eval_count == before  # not volatile
    # R28: 4096-char string result is within bounds
    s.set("D1", '="' + "x" * 2048 + '"')
    s.set("D2", "=CONCAT(D1,D1)")
    assert s.get("D2") == "x" * 4096


# ------------------------------------------- X1: G6 x G8 x G9 (R18/R23/R24/R25)
def test_x1_cross_sheet_copy_name_resolution_survives_round_trip():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("B1", 7)
    s1.define_name("NM", "B1")
    s1.set("A1", "=NM")
    assert s1.get("A1") == 7
    s1.copy("A1", "S2!A1")  # R23 qualified dst
    assert s2.get("A1") == "#NAME!"  # R23/R18 re-resolved on dst sheet, undefined
    w2 = Workbook.from_json(wb.to_json())
    assert w2.sheet("S1").get("A1") == 7  # R25 semantics preserved
    assert w2.sheet("S2").get("A1") == "#NAME!"
    # R25: subsequent identical calls behave identically
    w2.sheet("S2").define_name("NM", "S1!B1")  # R23 qualified name target
    s2.define_name("NM", "S1!B1")
    assert s2.get("A1") == 7
    assert w2.sheet("S2").get("A1") == 7


# ------------------------------------------- X2: G7 x G10 x G4 (R19/R20/R27)
def test_x2_undo_of_advance_clock_is_a_clock_edit():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()+1")
    assert s.get("A1") == 1
    wb.advance_clock()
    assert s.get("A1") == 2
    counts = s.eval_count
    assert wb.undo() is True  # R19 undoes advance_clock
    assert wb.clock == 0
    assert s.get("A1") == 1  # R20/R27 value obeys restored clock
    assert s.eval_count >= counts + 1  # R20 clock-edit touches volatile cell
    assert wb.redo() is True
    assert wb.clock == 1
    assert s.get("A1") == 2
    assert s.eval_count >= counts + 2  # R20 monotonic, redo is a clock edit too
