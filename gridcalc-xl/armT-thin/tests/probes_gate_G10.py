# Gate G10 probes — R26 (clock/NOW), R27 (volatility), R28 (XL bounds).
# Derived fresh from the spec for this gate round; replaces the prior file.
# Cross-cuts: G4 (R10 counters), G7 (R19/R20 undo/redo), G8 (R22/R23
# qualifiers, per-owner counters), G9 (R24/R25 persistence).

import json

from gridcalc import Workbook


def total(wb):
    return sum(wb.sheet(n).eval_count for n in wb.sheet_names)


# P1 — R26: clock property, advance_clock return/journal, R19 redo-clear.
def test_p1_clock_advance_undo_redo_journal():
    wb = Workbook()
    assert wb.clock == 0
    assert wb.advance_clock() == 1
    assert wb.clock == 1
    assert wb.advance_clock() == 2
    assert wb.advance_clock() == 3
    assert wb.undo() is True
    assert wb.clock == 2
    assert wb.undo() is True
    assert wb.clock == 1
    assert wb.redo() is True
    assert wb.clock == 2
    # a new journaled operation clears the redo stack (R19)
    assert wb.advance_clock() == 3
    assert wb.redo() is False
    assert wb.clock == 3


# P2 — R26 grammar: NOW ( ) exactly; every deviation is #PARSE!.
def test_p2_now_grammar_and_value():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    assert s.get("A1") == 0
    s.set("A2", "= NOW ( ) + 1")  # whitespace legal around every token (R3)
    assert s.get("A2") == 1
    s.set("B1", "=NOW(1)")  # any argument is #PARSE! (R26)
    assert s.get("B1") == "#PARSE!"
    s.set("B2", "=now()")  # lowercase callee (R3)
    assert s.get("B2") == "#PARSE!"
    s.set("B3", "=NOW")  # function name not followed by ( (R3)
    assert s.get("B3") == "#PARSE!"
    s.set("B4", "=SUM()")  # empty parens on other functions stay #PARSE! (R26)
    assert s.get("B4") == "#PARSE!"
    wb.advance_clock()
    assert s.get("A1") == 1  # NOW() is the current clock (R26)
    assert s.get("A2") == 2


# P3 — R27: static/syntactic volatility classes, counter deltas (G4 cross-cut).
def test_p3_volatility_classes_and_counters():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    s.set("B1", "=1+2")            # non-volatile
    s.set("C1", '=LEN("NOW()")')   # NOW inside STRING literal: text, not a call
    s.set("D1", "=IF(1,2,NOW())")  # NOW in the unselected branch: still volatile
    s.set("E1", "=NOW()+")         # #PARSE! cell: never volatile
    assert s.get("A1") == 0
    assert s.get("B1") == 3
    assert s.get("C1") == 5
    assert s.get("D1") == 2
    assert s.get("E1") == "#PARSE!"
    base = total(wb)
    wb.advance_clock()
    assert total(wb) == base  # mutating ops never evaluate (R10)
    # clock edit is irrelevant to non-volatile cells: +0 (R27)
    assert s.get("B1") == 3
    assert s.get("C1") == 5
    assert s.get("E1") == "#PARSE!"
    assert total(wb) == base
    # volatile cells recompute at the new clock: +1 each
    assert s.get("A1") == 1
    assert total(wb) == base + 1
    assert s.get("D1") == 2  # unselected-branch NOW still forces recompute
    assert total(wb) == base + 2
    # repeat read, no edit: +0 even for volatile (R27)
    assert s.get("A1") == 1
    assert s.get("D1") == 2
    assert total(wb) == base + 2


# P4 — R27 tighter warm bound: clock-only edits recompute at most the
# volatile closure members; warm non-volatile members stay cached.
def test_p4_warm_volatile_bound_over_chain():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    s.set("B1", "=5*2")    # non-volatile closure member
    s.set("A2", "=A1+1")
    s.set("A3", "=A2+B1")
    for addr in ("A1", "B1", "A2", "A3"):  # warm every closure member
        s.get(addr)
    assert s.get("A3") == 11  # 0 + 1 + 10
    base = total(wb)
    wb.advance_clock()
    wb.advance_clock()  # "one or more clock-only edits" (R27)
    assert s.get("A3") == 13  # 2 + 1 + 10 — naive value at current clock (R11)
    delta = total(wb) - base
    assert 1 <= delta <= 3  # volatile members are A1, A2, A3; B1 is warm


# P5 — R24/R25 (G9 cross-cut, deferred re-probe): clock restored by
# round-trip; journal/counters/caches reset; to_json pure; independence.
def test_p5_round_trip_restores_clock_and_resets():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()+10")
    wb.advance_clock()
    wb.advance_clock()
    wb.advance_clock()
    assert s.get("A1") == 13
    before = s.eval_count
    dump = wb.to_json()
    assert s.eval_count == before  # to_json is a pure observation (R24)
    wb2 = Workbook.from_json(dump)
    assert wb2.clock == 3            # clock restored exactly (R24)
    s2 = wb2.sheet("S1")
    assert s2.eval_count == 0        # counters reset (R24)
    assert wb2.undo() is False       # journal empty (R24)
    assert s2.get("A1") == 13        # fresh compute at the restored clock
    assert s2.eval_count == 1        # no result carried over (R24/R10)
    # identical subsequent calls agree (R25)
    assert wb.advance_clock() == 4
    assert wb2.advance_clock() == 4
    assert s.get("A1") == 14
    assert s2.get("A1") == 14


# P6 — R28: a stored formula text exceeding R12(a)'s limits is copied
# byte-for-byte unchanged, and the copy journals/undoes normally.
def test_p6_overlong_formula_copied_byte_for_byte():
    wb = Workbook()
    s = wb.add_sheet("S1")
    body = "B1+" + "1+" * 260 + "1"  # with "=": 525 chars > 512 (R12a)
    s.set("A1", "=" + body)
    s.copy("A1", "A2")
    dump = wb.to_json()
    assert dump.count(body) == 2                     # verbatim at A1 and A2
    assert ("B2+" + "1+" * 260 + "1") not in dump    # no shift happened
    assert wb.undo() is True                         # journaled (R28/R19)
    assert s.get("A2") is None
    assert wb.redo() is True
    assert wb.to_json().count(body) == 2
    assert json.loads(wb.to_json()) is not None      # still valid JSON (R24)


def test_p6b_overdeep_verbatim_and_within_bounds_still_rewrites():
    wb = Workbook()
    s = wb.add_sheet("S1")
    deep_body = "(" * 33 + "B1" + ")" * 33  # nesting depth 33 > 32 (R12a)
    s.set("A1", "=" + deep_body)
    s.copy("A1", "A2")
    dump = wb.to_json()
    assert dump.count(deep_body) == 2
    assert "B2" not in dump
    # a clearly-within-bounds formula still gets the R17 rewrite
    ok_body = "B1+" + "1+" * 245 + "1"  # with "=": 495 chars, depth 0
    s.set("C1", "=" + ok_body)
    s.copy("C1", "C2")
    dump2 = wb.to_json()
    assert ok_body in dump2                       # C1 unchanged
    assert ("B2+" + "1+" * 245 + "1") in dump2    # C2 shifted per R17


# P7 — R28: 4096-char string results are within bounds and must succeed.
def test_p7_string_bound_4096_within_bounds():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "x" * 4095)
    s.set("B1", '=CONCAT(A1,"y")')  # result is exactly 4096 chars (R12d/R28)
    assert s.get("B1") == "x" * 4095 + "y"
    s.set("C1", "=LEN(B1)")
    assert s.get("C1") == 4096


# P7b — R28 × G8: the 256-formula-cell reach is counted across all sheets;
# a 128+128 cross-sheet chain is within bounds and must complete.
def test_p7b_reach_256_across_sheets():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    addrs = [c + str(r) for r in range(1, 17) for c in "ABCDEFGH"]  # 128
    prev = None
    for a in addrs:  # base chain on S2
        s2.set(a, "=1" if prev is None else "=" + prev + "+1")
        prev = a
    s2_last = prev  # value 128 at the chain end
    prev = None
    for a in addrs:  # continuation chain on S1, joined by a qualified ref
        if prev is None:
            s1.set(a, "=S2!" + s2_last + "+1")  # R22 qualifier
        else:
            s1.set(a, "=" + prev + "+1")
        prev = a
    assert s1.get(prev) == 256  # reaches exactly 256 formula cells (R12b/R28)
    # each computation increments the owning sheet's counter (R23/R10)
    assert s1.eval_count == 128
    assert s2.eval_count == 128


# P8 — R26/R27 × G7: undo/redo of advance_clock is a clock edit (R20)
# touching exactly the volatile cells.
def test_p8_undo_redo_of_clock_edit():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    s.set("B1", "=100")
    assert s.get("A1") == 0
    assert s.get("B1") == 100
    wb.advance_clock()
    assert s.get("A1") == 1
    base = total(wb)
    assert wb.undo() is True   # reverts advance_clock (R19/R26)
    assert wb.clock == 0
    assert s.get("A1") == 0    # value at the restored clock (R20/R27)
    assert total(wb) == base + 1
    assert s.get("B1") == 100  # non-volatile: irrelevant edit, +0
    assert total(wb) == base + 1
    assert wb.redo() is True   # re-applies exactly (R19)
    assert wb.clock == 1
    assert s.get("A1") == 1
    assert total(wb) == base + 2
    # deeper undos restore the sets LIFO (G7 cross-cut)
    assert wb.undo() is True   # clock back to 0
    assert wb.undo() is True   # reverts set B1
    assert wb.clock == 0
    assert s.get("B1") is None
