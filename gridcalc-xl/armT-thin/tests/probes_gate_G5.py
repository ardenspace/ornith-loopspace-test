"""Gate G5 probes — derived fresh from spec.md (R13, R14, R15) alone.

Cross-lineage verifier probes. Every expected value below is dictated by
the frozen spec text, cited per assertion; the lead's own tests are not
consulted for these expectations.

Groups gated so far: G1 (R1/R2 store), G2 (R3-R6 scalar grammar),
G3 (R7-R9 ranges/cycles), G4 (R10-R12 incremental). Cross-cutting probes
below thread G5 behavior through G1 storage, G2 R5 ordering, and G4 R10
eval_count.
"""

from gridcalc import Workbook


def _sheet(name="S1"):
    wb = Workbook()
    return wb, wb.add_sheet(name)


# ---------------------------------------------------------------------------
# Scenario 1 — R13 string literals + equality/inequality typing
# R13: STRING primary evaluates to its contents (str). `=`/`<>` compare two
# strs (exact, code-point, case-sensitive) yielding 1/0; a mixed int-vs-str
# comparison is #TYPE!.
# ---------------------------------------------------------------------------
def test_r13_string_literal_and_equality():
    wb, s = _sheet()
    s.set("A1", '="hello"')
    assert s.get("A1") == "hello"                      # R13 STRING primary
    s.set("A2", '="a"="a"')
    assert s.get("A2") == 1                             # R13 str==str true
    s.set("A3", '="a"="b"')
    assert s.get("A3") == 0                             # R13 str==str false
    s.set("A4", '="a"<>"b"')
    assert s.get("A4") == 1                             # R13 str<>str true
    s.set("A5", '="a"<>"a"')
    assert s.get("A5") == 0                             # R13 str<>str false
    s.set("A6", '="A"="a"')
    assert s.get("A6") == 0                             # R13 case-sensitive
    s.set("A7", '=1="1"')
    assert s.get("A7") == "#TYPE!"                      # R13 mixed int/str
    s.set("A8", '="1"=1')
    assert s.get("A8") == "#TYPE!"                      # R13 mixed str/int


# ---------------------------------------------------------------------------
# Scenario 2 — R13 arithmetic / orderings / unary minus require int operands
# R13: `+ - * /`, unary minus, and the orderings `< <= > >=` require int
# operands; a str operand makes that operand position contribute #TYPE!.
# (This is exactly the branch the prior G5 FAIL flagged as untested.)
# ---------------------------------------------------------------------------
def test_r13_ordering_arith_unary_require_int():
    wb, s = _sheet()
    cases = {
        "B1": '="a"<"b"',    # ordering with str  -> #TYPE!
        "B2": '="a"<="b"',   # ordering with str  -> #TYPE!
        "B3": '="a">"b"',    # ordering with str  -> #TYPE!
        "B4": '="a">="b"',   # ordering with str  -> #TYPE!
        "B5": '=-"x"',       # unary minus on str -> #TYPE!
        "B6": '="x"+1',      # + with str         -> #TYPE!
        "B7": '=1-"x"',      # - with str         -> #TYPE!
        "B8": '="x"*2',      # * with str         -> #TYPE!
        "B9": '="x"/1',      # / with str         -> #TYPE!
    }
    for addr, formula in cases.items():
        s.set(addr, formula)
    for addr, formula in cases.items():
        assert s.get(addr) == "#TYPE!", (addr, formula, s.get(addr))


# ---------------------------------------------------------------------------
# Scenario 3 (CROSS G2/R5 + G4/R10) — positional discovery + short-circuit
# R13: offenders are discovered in R5's textual left-to-right order; the
# first offender (error OR forbidden type) determines the result, and
# operands after it are not evaluated (observable through R10 counters).
#   =A1+"x" with A1 -> #DIV!  is #DIV!  (A1 is the first offender)
#   ="x"+A1                    is #TYPE! regardless of A1, A1 never started
# ---------------------------------------------------------------------------
def test_r13_positional_short_circuit_and_counter():
    wb, s = _sheet()
    s.set("A1", "=1/0")                 # A1 -> #DIV!
    s.set("C1", '=A1+"x"')
    assert s.get("C1") == "#DIV!"       # R5/R13 first offender is A1's error

    wb2 = Workbook()
    s2 = wb2.add_sheet("S1")
    s2.set("A1", "=99")                 # a formula cell (would count if started)
    s2.set("D1", '="x"+A1')             # str is first offender, textually before A1
    assert s2.get("D1") == "#TYPE!"     # R13 #TYPE! regardless of A1
    # R10: only D1's computation started; A1 after the first offender is never
    # started -> owning-sheet counter == 1.
    assert s2.eval_count == 1, s2.eval_count


# ---------------------------------------------------------------------------
# Scenario 4 (CROSS G1/R2 + R6) — references read typed as str
# R13 (Engineer Lens delta 1): a reference to a string-literal cell returns
# that str; string-vs-string comparisons via references are legal, orderings
# via references are still #TYPE!.
# ---------------------------------------------------------------------------
def test_r13_typed_reference_reads():
    wb, s = _sheet()
    s.set("A1", "apple")               # string literal (no leading '=')
    s.set("B1", "apple")               # string literal
    s.set("E1", "=A1")                 # typed read of a str cell
    assert s.get("E1") == "apple"      # R13 typed reference read
    s.set("E2", "=A1=B1")
    assert s.get("E2") == 1            # R13 str==str via references
    s.set("E3", "=A1<B1")
    assert s.get("E3") == "#TYPE!"     # R13 ordering on str refs -> #TYPE!
    # newline inside a string literal is legal and preserved verbatim (R13)
    s.set("F1", '="a\nb"')
    assert s.get("F1") == "a\nb"


# ---------------------------------------------------------------------------
# Scenario 5 (CROSS R6 empty-cell) — CONCAT rendering and short-circuit (R14)
# R14: CONCAT renders int args in base-10 (value, not source text; leading
# '-' for negatives, no leading zeros), takes str args as-is; an empty-cell
# reference arg contributes int 0 -> "0". Args evaluate L-to-R with R5
# short-circuit on the first error.
# ---------------------------------------------------------------------------
def test_r14_concat():
    wb, s = _sheet()
    s.set("A1", '=CONCAT("a","b")')
    assert s.get("A1") == "ab"
    s.set("A2", "=CONCAT(1,2)")
    assert s.get("A2") == "12"
    s.set("A3", "=CONCAT(007)")
    assert s.get("A3") == "7"           # value not source text
    s.set("A4", "=CONCAT(-12)")
    assert s.get("A4") == "-12"
    s.set("A5", '=CONCAT("x",1,"y")')
    assert s.get("A5") == "x1y"
    s.set("A6", "=CONCAT(Z9)")          # Z9 empty -> int 0 -> "0"
    assert s.get("A6") == "0"           # R6 empty single-ref contributes 0
    s.set("A7", '=CONCAT(1/0,"z")')
    assert s.get("A7") == "#DIV!"       # R5 short-circuit on first error
    s.set("A8", '=CONCAT("z",1/0)')
    assert s.get("A8") == "#DIV!"


# ---------------------------------------------------------------------------
# Scenario 6 — LEN (R14)
# R14: LEN returns the number of characters of a str arg, or of the decimal
# rendering of an int arg. LEN("") is 0, LEN(-12) is 3.
# ---------------------------------------------------------------------------
def test_r14_len():
    wb, s = _sheet()
    s.set("A1", '=LEN("")')
    assert s.get("A1") == 0
    s.set("A2", '=LEN("hello")')
    assert s.get("A2") == 5
    s.set("A3", "=LEN(-12)")
    assert s.get("A3") == 3             # rendering "-12" has length 3
    s.set("A4", "=LEN(0)")
    assert s.get("A4") == 1
    s.set("A5", "=LEN(100)")
    assert s.get("A5") == 3
    s.set("A6", "=LEN(007)")            # value 7 -> "7" -> length 1
    assert s.get("A6") == 1


# ---------------------------------------------------------------------------
# Scenario 7 — IF selection, typing, error condition (R15)
# R15: condition evaluated first; error condition is the result; str
# condition is #TYPE!; nonzero -> 2nd arg, zero -> 3rd arg; result is the
# selected branch's value of any type; an error in the UNSELECTED branch is
# invisible.
# ---------------------------------------------------------------------------
def test_r15_if_selection_and_typing():
    wb, s = _sheet()
    s.set("A1", "=IF(1,10,20)")
    assert s.get("A1") == 10            # nonzero -> 2nd arg
    s.set("A2", "=IF(0,10,20)")
    assert s.get("A2") == 20            # zero -> 3rd arg
    s.set("A3", "=IF(5,10,20)")
    assert s.get("A3") == 10            # any nonzero -> 2nd
    s.set("A4", "=IF(-3,10,20)")
    assert s.get("A4") == 10            # negative is nonzero -> 2nd
    s.set("A5", '=IF("x",10,20)')
    assert s.get("A5") == "#TYPE!"      # str condition -> #TYPE!
    s.set("A6", "=IF(1/0,10,20)")
    assert s.get("A6") == "#DIV!"       # error condition is the result
    s.set("A7", '=IF(1,"yes","no")')
    assert s.get("A7") == "yes"         # str result of selected branch
    s.set("A8", "=IF(0,1/0,42)")
    assert s.get("A8") == 42            # unselected 2nd branch error invisible
    s.set("A9", "=IF(1,42,1/0)")
    assert s.get("A9") == 42            # unselected 3rd branch error invisible


# ---------------------------------------------------------------------------
# Scenario 8 (CROSS G4/R10) — IF evaluates only the selected branch
# R15: only the selected branch's cells are evaluated; the unselected
# branch's cells are never evaluated, observable through R10 counters.
# A1 = IF(0, B1, C1): cond 0 selects C1; B1 (unselected) is never started.
# ---------------------------------------------------------------------------
def test_r15_unselected_branch_not_evaluated_counter():
    wb, s = _sheet()
    s.set("B1", "=200")                 # unselected branch formula cell
    s.set("C1", "=100")                 # selected branch formula cell
    s.set("A1", "=IF(0,B1,C1)")
    assert s.get("A1") == 100           # cond 0 -> 3rd arg C1
    # Started: A1 and C1 only. B1 (unselected) never started.
    assert s.eval_count == 2, s.eval_count

    # Symmetric: cond nonzero selects B1, C1 never started.
    wb2 = Workbook()
    s2 = wb2.add_sheet("S1")
    s2.set("B1", "=200")
    s2.set("C1", "=100")
    s2.set("A1", "=IF(1,B1,C1)")
    assert s2.get("A1") == 200
    assert s2.eval_count == 2, s2.eval_count
