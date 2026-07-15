"""Held-out oracle for gridcalc-xl (Experiment W'). Authored from
gridcalc-xl/SPEC.md alone, pre-registered before any arm ran. Grade an
arm with:

    PYTHONPATH=<arm-repo> python3 -m pytest gridcalc_xl_oracle.py -q

Test names carry their R-group (test_rNN_*) so the trajectory grader can
compute per-requirement pass rates per snapshot. Counter-pattern tests
(R10/R20/R23/R24/R27) are marked `counters`; the naive reference does
not model eval_count, so the self-test excludes them:

    PYTHONPATH=.:selftest_shim \\
        python3 -m pytest gridcalc_xl_oracle.py -q -m "not counters"

The seeded differential (R11/R25) runs GRIDCALC_XL_DIFF_SEEDS sequences
(default 120; the deep pre-registered floor is 1000 — set the env var
for final grading).

v1 subset ported from gridcalc/grading/gridcalc_oracle.py (134 cases)
with the four Engineer-Lens deltas applied: typed reference reads,
multi-letter identifiers as NAME tokens, newly-legal texts, and the
Workbook API root.
"""
import json
import os
import random
import re

import pytest

from gridcalc import Workbook
from gridcalc_xl_ref import RefWorkbook

counters = pytest.mark.counters


def one():
    """One sheet of a fresh workbook (v1-subset harness, R21)."""
    return Workbook().add_sheet("S1")


# ======================================================================
# R1 — addressing
# ======================================================================
def test_r01_valid_addresses():
    s = one()
    for a in ("A1", "Z99", "M50", "A99", "Z1"):
        s.set(a, 1)
        assert s.get(a) == 1


@pytest.mark.parametrize("bad", [
    "a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1", "1A", "A",
    "1", "S1!A1", "$A$1", "A1:B2",
])
def test_r01_invalid_address_strings(bad):
    s = one()
    with pytest.raises(ValueError):
        s.get(bad)
    with pytest.raises(ValueError):
        s.set(bad, 1)


@pytest.mark.parametrize("bad", [5, None, True, 1.5])
def test_r01_non_str_addresses(bad):
    s = one()
    with pytest.raises(ValueError):
        s.get(bad)


@counters
def test_r01_failing_get_state_unchanged():
    s = one()
    s.set("A1", "=1+1")
    before = s.eval_count
    with pytest.raises(ValueError):
        s.get("A100")
    assert s.eval_count == before
    assert s.get("A1") == 2


# ======================================================================
# R2 — cell store
# ======================================================================
def test_r02_literal_roundtrip_and_none():
    s = one()
    assert s.get("B2") is None
    s.set("B2", 42)
    assert s.get("B2") == 42
    s.set("B2", "hello")
    assert s.get("B2") == "hello"
    s.set("B2", -7)
    assert s.get("B2") == -7


def test_r02_bool_and_bad_types_raise():
    s = one()
    for bad in (True, False, 1.5, None, [1], {"a": 1}):
        with pytest.raises(ValueError):
            s.set("A1", bad)
    assert s.get("A1") is None  # failed sets left the sheet unchanged


def test_r02_subclass_normalization():
    class MyInt(int):
        pass

    class MyStr(str):
        pass

    s = one()
    s.set("A1", MyInt(7))
    assert type(s.get("A1")) is int and s.get("A1") == 7
    s.set("A2", MyStr("hi"))
    assert type(s.get("A2")) is str and s.get("A2") == "hi"
    s.set(MyStr("A3"), 5)  # str subclass in the address position
    assert s.get("A3") == 5
    s.set("A4", MyStr("=1+1"))  # subclass formula raw
    assert s.get("A4") == 2


def test_r02_set_returns_none_and_replaces():
    s = one()
    assert s.set("A1", 1) is None
    s.set("A1", "text")
    assert s.get("A1") == "text"
    s.set("A1", "=1+1")
    assert s.get("A1") == 2


def test_r02_error_looking_string_literal_roundtrip():
    s = one()
    for lit in ("#REF!", "#DIV!", "#CYCLE!", "#PARSE!", "#TYPE!", "#NAME!"):
        s.set("A1", lit)
        assert s.get("A1") == lit


def test_r02_failed_set_leaves_content():
    s = one()
    s.set("A1", 3)
    with pytest.raises(ValueError):
        s.set("A1", True)
    assert s.get("A1") == 3


# ======================================================================
# R3 — grammar (v1 core + XL identifier classification)
# ======================================================================
@pytest.mark.parametrize("src,expected", [
    ("=1+2*3", 7),
    ("=(1+2)*3", 9),
    ("=--1", 1),
    ("=2--3", 5),
    ("=007", 7),
    ("=1<2<3", 1),      # left-associative chaining
    ("=1+1=2", 1),
    ("=2<>2", 0),
    ("=3>=3", 1),
    ("=2<=1", 0),
    ("=5>4", 1),
    ("=-2*3", -6),
    ("=\t1 +\t2", 3),   # tabs between tokens
])
def test_r03_grammar_values(src, expected):
    s = one()
    s.set("A1", src)
    assert s.get("A1") == expected


@pytest.mark.parametrize("src", [
    "=", "=1 < = 2", "=a1", "=sum(A1:B2)", "=AVG(A1:B2)",
    "=1++", "=(1+2", "=1 ? 2", "=SUM(A1)", "=A1:B2", "=SUM((A1:B2))",
    "=F",                     # single letter: neither REF nor NAME shape
    "=" + "X" * 33,           # 33+ chars: neither shape
    "=SUM", "=NOW",           # function name not followed by (
    "=SUM()", "=CONCAT()", "=NOW(1)", "=IF(1,2)", "=LEN(1,2)",
    "=IF(1,2,3", "=Foo", "=foo", "=AA1(1)",
    '="unterminated', '="a""b"',   # no escapes: adjacent primaries
    "=1\n+1",                 # newline is not formula whitespace
])
def test_r03_parse_errors(src):
    s = one()
    s.set("A1", src)
    assert s.get("A1") == "#PARSE!"


def test_r03_multiletter_identifier_is_name_not_parse():
    s = one()  # delta 2: v1 graded =AA1 as #PARSE!
    s.set("A1", "=AA1")
    assert s.get("A1") == "#NAME!"
    s.set("A2", "=FOO")
    assert s.get("A2") == "#NAME!"


def test_r03_function_call_whitespace():
    s = one()
    s.set("A1", 1)
    s.set("A2", 2)
    s.set("B1", "=SUM ( A1 : A2 )")
    assert s.get("B1") == 3


# ======================================================================
# R4 — division
# ======================================================================
@pytest.mark.parametrize("src,expected", [
    ("=7/2", 3),
    ("=-7/2", -3),
    ("=7/-2", -3),
    ("=0/5", 0),
    ("=7/0", "#DIV!"),
])
def test_r04_division(src, expected):
    s = one()
    s.set("A1", src)
    assert s.get("A1") == expected


# ======================================================================
# R5 — error values and ordering
# ======================================================================
def test_r05_error_propagates_through_refs():
    s = one()
    s.set("A1", "=1/0")
    s.set("B1", "=A1+1")
    assert s.get("B1") == "#DIV!"


def test_r05_leftmost_error_wins_textually():
    s = one()
    s.set("B1", "=1/0")       # DIV
    s.set("C1", "=A0")        # REF
    s.set("D1", "=Z9+B1*C1")  # Z9 empty(0), then B1 -> DIV first
    assert s.get("D1") == "#DIV!"
    s.set("E1", "=C1+B1")
    assert s.get("E1") == "#REF!"


# ======================================================================
# R6 — typed reference reads (delta 1 from v1's numeric reads)
# ======================================================================
def test_r06_reference_reads_are_typed():
    s = one()
    s.set("A1", "=Z9+1")          # empty ref contributes int 0
    assert s.get("A1") == 1
    s.set("B1", "hi")
    s.set("B2", "=B1")            # bare ref to string -> the string (XL)
    assert s.get("B2") == "hi"
    s.set("B3", "=B1+1")          # string in arithmetic -> #TYPE!
    assert s.get("B3") == "#TYPE!"
    s.set("B4", "=B1=1")          # mixed comparison -> #TYPE!
    assert s.get("B4") == "#TYPE!"
    s.set("B5", '=B1="hi"')       # str-vs-str comparison is legal (XL)
    assert s.get("B5") == 1
    s.set("C1", "=C2")            # bare ref to empty -> 0
    assert s.get("C1") == 0


@pytest.mark.parametrize("src", ["=A01", "=A0", "=A100"])
def test_r06_refshaped_but_out_of_grid(src):
    s = one()
    s.set("B1", src)
    assert s.get("B1") == "#REF!"


def test_r06_formula_chain():
    s = one()
    s.set("A1", 5)
    s.set("A2", "=A1*2")
    s.set("A3", "=A2+1")
    assert s.get("A3") == 11
    s.set("A1", 6)
    assert s.get("A3") == 13  # values reflect current contents


def test_r06_literal_error_string_is_type_fuel_not_error():
    s = one()
    s.set("A1", "#REF!")
    s.set("B1", "=A1")     # typed read: the string itself (XL)
    s.set("B2", "=A1+1")   # ...but #TYPE! fuel in arithmetic
    assert s.get("B1") == "#REF!"  # a str equal to the error text (R2)
    assert s.get("B2") == "#TYPE!"


# ======================================================================
# R7 — ranges
# ======================================================================
@pytest.mark.parametrize("src", ["=SUM(B2:A1)", "=SUM(A0:B2)",
                                 "=SUM(A1:A100)", "=MIN(A01:B2)"])
def test_r07_invalid_ranges(src):
    s = one()
    s.set("C5", src)
    assert s.get("C5") == "#REF!"


def test_r07_whitespace_around_colon():
    s = one()
    s.set("A1", 1)
    s.set("B2", 2)
    s.set("C5", "=SUM(A1 : B2)")
    assert s.get("C5") == 3


def test_r07_function_composes_as_primary():
    s = one()
    s.set("A1", 1)
    s.set("A2", 3)
    s.set("C5", "=SUM(A1:A2)+1")
    assert s.get("C5") == 5
    s.set("C6", "=-MAX(A1:A2)*2")
    assert s.get("C6") == -6
    s.set("C7", "=SUM(A1:A2)>3")
    assert s.get("C7") == 1


def test_r07_first_error_in_row_major_order():
    s = one()
    s.set("A1", 1)
    s.set("B1", "oops")   # visited before A2 (row-major)
    s.set("A2", "=1/0")
    s.set("C5", "=SUM(A1:B2)")
    assert s.get("C5") == "#TYPE!"


def test_r07_formula_members_contribute():
    s = one()
    s.set("A1", 1)
    s.set("A2", "=A1+1")
    s.set("C5", "=SUM(A1:A2)")
    assert s.get("C5") == 3


# ======================================================================
# R8 — SUM/MIN/MAX/COUNT semantics
# ======================================================================
def test_r08_sum_skips_empty_and_zero_on_all_empty():
    s = one()
    s.set("A1", 5)
    s.set("C5", "=SUM(A1:A3)")
    assert s.get("C5") == 5
    s.set("C6", "=SUM(D1:D3)")
    assert s.get("C6") == 0


def test_r08_min_max():
    s = one()
    s.set("A1", 5)
    s.set("A2", -3)
    s.set("A3", "=A1*2")
    s.set("C5", "=MIN(A1:A3)")
    s.set("C6", "=MAX(A1:A3)")
    assert s.get("C5") == -3
    assert s.get("C6") == 10
    s.set("C7", "=MIN(D1:D3)")  # all-empty
    assert s.get("C7") == "#TYPE!"


def test_r08_string_in_range_types_sum_min_max_not_count():
    s = one()
    s.set("A1", 1)
    s.set("A2", "hi")
    for f, exp in (("SUM", "#TYPE!"), ("MIN", "#TYPE!"), ("MAX", "#TYPE!"),
                   ("COUNT", 2)):
        s.set("C5", f"={f}(A1:A2)")
        assert s.get("C5") == exp


def test_r08_string_valued_formula_in_range_is_type_fuel():
    s = one()
    s.set("A1", '=CONCAT("h","i")')
    s.set("A2", 1)
    s.set("C5", "=SUM(A1:A2)")
    assert s.get("C5") == "#TYPE!"


def test_r08_literal_error_string_in_range():
    s = one()
    s.set("A1", 1)
    s.set("A2", "#DIV!")  # string literal, not an error value
    for f, exp in (("SUM", "#TYPE!"), ("MIN", "#TYPE!"), ("MAX", "#TYPE!"),
                   ("COUNT", 2)):
        s.set("C5", f"={f}(A1:A2)")
        assert s.get("C5") == exp


def test_r08_count_structural():
    s = one()
    s.set("A1", 1)
    s.set("A2", "text")
    s.set("A3", "=1/0")   # formula cell counts; never evaluated by COUNT
    s.set("C5", "=COUNT(A1:A4)")
    assert s.get("C5") == 3
    s.set("A1", "=COUNT(A1:A1)")  # self-inclusion is NOT a cycle
    assert s.get("A1") == 1


# ======================================================================
# R9 — cycles
# ======================================================================
def test_r09_self_reference():
    s = one()
    s.set("A1", "=A1")
    assert s.get("A1") == "#CYCLE!"


def test_r09_mutual_cycle():
    s = one()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    assert s.get("B1") == "#CYCLE!"


def test_r09_cycle_through_range_and_propagation():
    s = one()
    s.set("A1", "=SUM(A1:B1)")
    assert s.get("A1") == "#CYCLE!"
    s.set("C1", "=A1+1")
    assert s.get("C1") == "#CYCLE!"


def test_r09_recovery_after_breaking_cycle():
    s = one()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    s.set("B1", 3)
    assert s.get("A1") == 3
    assert s.get("B1") == 3


# ======================================================================
# R10 — lazy evaluation and incremental recomputation (counters)
# ======================================================================
@counters
def test_r10_mutating_ops_never_evaluate():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.copy("B1", "B2")
    s.define_name("FOO", "A1")
    wb.add_sheet("S2")
    wb.advance_clock()
    wb.undo()
    wb.redo()
    assert s.eval_count == 0


@counters
def test_r10_counting_and_repeat_read():
    s = one()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    c0 = s.eval_count
    assert s.get("B1") == 2
    assert s.eval_count - c0 == 1  # B1 only; A1 is a literal
    c1 = s.eval_count
    assert s.get("B1") == 2
    assert s.eval_count == c1      # repeat read adds 0
    c2 = s.eval_count
    assert s.get("A1") == 1        # literal read
    assert s.eval_count == c2


@counters
def test_r10_error_results_cached():
    s = one()
    s.set("A1", "=A1")
    c0 = s.eval_count
    assert s.get("A1") == "#CYCLE!"
    assert s.eval_count - c0 == 1
    c1 = s.eval_count
    assert s.get("A1") == "#CYCLE!"
    assert s.eval_count == c1
    s.set("B1", "=)")
    c2 = s.eval_count
    s.get("B1")
    s.get("B1")
    assert s.eval_count - c2 <= 1  # #PARSE! computed at most once


@counters
def test_r10_irrelevant_edit_adds_zero():
    s = one()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("D9", 5)            # outside B1's closure
    assert s.get("B1") == 2
    assert s.eval_count == c0


@counters
def test_r10_relevant_edit_bounds():
    s = one()
    s.set("A1", 1)
    s.set("B1", "=A1")
    s.set("C1", "=B1")
    s.set("E5", "=D5+1")      # unrelated formula, warmed
    s.get("C1")
    s.get("E5")
    c0 = s.eval_count
    s.set("A1", 9)
    assert s.get("C1") == 9
    assert 1 <= s.eval_count - c0 <= 2  # formula cells in closure: C1, B1
    c1 = s.eval_count
    assert s.get("E5") == 1   # untouched dependent chain stayed cached
    assert s.eval_count == c1


@counters
def test_r10_set_x_itself_is_relevant():
    s = one()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("B1", "=A1*3")
    assert s.get("B1") == 3
    assert s.eval_count - c0 >= 1


@counters
def test_r10_edit_to_literal_adds_zero():
    s = one()
    s.set("B1", "=1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("B1", 5)
    assert s.get("B1") == 5
    assert s.eval_count == c0


@counters
def test_r10_noop_set_still_counts_as_edit():
    s = one()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("A1", 1)            # identical content: still an edit
    assert s.get("B1") == 2
    assert s.eval_count - c0 >= 1


@counters
def test_r10_count_members_not_evaluated():
    s = one()
    s.set("A1", "=1+1")
    s.set("A2", "=2+2")
    s.set("B5", "=COUNT(A1:A3)")
    c0 = s.eval_count
    assert s.get("B5") == 2
    assert s.eval_count - c0 == 1  # B5 only


@counters
def test_r10_short_circuit_observable():
    s = one()
    s.set("G1", "=1+1")
    s.set("F1", "=1/0+G1")
    c0 = s.eval_count
    assert s.get("F1") == "#DIV!"
    assert s.eval_count - c0 == 1  # G1 never started
    c1 = s.eval_count
    assert s.get("G1") == 2
    assert s.eval_count - c1 == 1  # proves G1 wasn't computed before


@counters
def test_r10_type_offender_short_circuit_observable():
    s = one()
    s.set("G1", "=1+1")
    s.set("F1", '="x"+G1')    # string offends first, textually
    c0 = s.eval_count
    assert s.get("F1") == "#TYPE!"
    assert s.eval_count - c0 == 1  # G1 never started
    c1 = s.eval_count
    assert s.get("G1") == 2
    assert s.eval_count - c1 == 1


@counters
def test_r10_range_short_circuit_observable():
    s = one()
    s.set("A1", "boom")       # first member is #TYPE! fuel
    s.set("B1", "=1+1")
    s.set("H5", "=SUM(A1:B1)")
    c0 = s.eval_count
    assert s.get("H5") == "#TYPE!"
    assert s.eval_count - c0 == 1  # B1 never started
    c1 = s.eval_count
    assert s.get("B1") == 2
    assert s.eval_count - c1 == 1


@counters
def test_r10_range_member_edit_is_relevant():
    s = one()
    s.set("C5", "=SUM(A1:B2)")
    s.get("C5")
    c0 = s.eval_count
    s.set("B2", 4)            # empty->filled inside the range: in closure
    assert s.get("C5") == 4
    assert s.eval_count - c0 >= 1


@counters
def test_r10_if_static_closure_and_unselected_branch():
    s = one()
    s.set("B9", "=1+1")
    s.set("A1", "=IF(1, 5, B9)")
    c0 = s.eval_count
    assert s.get("A1") == 5
    assert s.eval_count - c0 == 1   # B9 (unselected) never started
    s.get("B9")                     # warm B9 too
    c1 = s.eval_count
    s.set("B9", "=2+2")             # in A1's STATIC closure
    assert s.get("A1") == 5
    assert s.eval_count - c1 >= 1   # relevant edit: recompute started
    c2 = s.eval_count
    s.set("D9", 1)                  # not in closure
    assert s.get("A1") == 5
    assert s.eval_count == c2


@counters
def test_r10_no_full_sheet_recompute_bound():
    s = one()
    for r in range(1, 9):
        s.set(f"H{r}", f"=G{r}+1")  # 8 unrelated formulas
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.set("C1", "=B1+1")
    for r in range(1, 9):
        s.get(f"H{r}")
    s.get("C1")
    c0 = s.eval_count
    s.set("A1", 2)
    assert s.get("C1") == 4
    assert s.eval_count - c0 <= 2  # closure formulas only: C1, B1


# ======================================================================
# R12 — bounds (single-sheet core; cross-sheet reach under R28)
# ======================================================================
def test_r12_nested_parens_depth_32():
    s = one()
    s.set("A1", "=" + "(" * 32 + "1" + ")" * 32)
    assert s.get("A1") == 1


def test_r12_unary_minus_tower():
    n = 509
    s = one()
    s.set("A1", "=" + "-" * n + "1")   # 511 chars incl. '='
    assert s.get("A1") == (1 if n % 2 == 0 else -1)


def test_r12_reference_chain_256():
    s = one()
    addrs = [f"{c}{r}" for r in range(1, 12)
             for c in "ABCDEFGHIJKLMNOPQRSTUVWX"]
    chain = addrs[:257]
    for i in range(256):
        s.set(chain[i], f"={chain[i + 1]}")
    s.set(chain[256], 7)
    assert s.get(chain[0]) == 7


def test_r12_magnitude_bounds():
    s = one()
    s.set("A1", "=1024*1024*1024*1024*1024*1024")  # 2**60
    assert s.get("A1") == 2 ** 60
    s.set("A2", "=9223372036854775807")            # 2**63 - 1 exactly
    assert s.get("A2") == 2 ** 63 - 1
    s.set("A3", "=-9223372036854775807")
    assert s.get("A3") == -(2 ** 63 - 1)


def test_r12_out_of_bounds_confined():
    s = one()
    big = "=" + "+".join(["1"] * 400)  # ~800 chars: out of bounds
    s.set("Z9", big)                   # set must still succeed
    try:
        s.get("Z9")                    # may return or raise; must terminate
    except Exception:
        pass
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    assert s.get("B1") == 2            # within-bounds gets keep guarantees


# ======================================================================
# R13 — strings in formulas, closed typing
# ======================================================================
@pytest.mark.parametrize("src,expected", [
    ('="hi"', "hi"),
    ('=""', ""),
    ('="a b\tc"', "a b\tc"),
    ('="#DIV!"', "#DIV!"),          # error-shaped text is just a string
    ('="A1"', "A1"),
    ('="x"+1', "#TYPE!"),
    ('=1+"x"', "#TYPE!"),
    ('=-"x"', "#TYPE!"),
    ('="a"<"b"', "#TYPE!"),         # orderings require ints
    ('="a"<=1', "#TYPE!"),
    ('="a"="a"', 1),
    ('="a"="A"', 0),                # case-sensitive
    ('="a"<>"b"', 1),
    ('="ab"<>"ab"', 0),
    ('=1="a"', "#TYPE!"),           # mixed comparison
    ('="1"=1', "#TYPE!"),
    ('=("a"="a")+1', 2),            # comparison yields int
])
def test_r13_string_literals_and_typing(src, expected):
    s = one()
    s.set("A1", src)
    assert s.get("A1") == expected


def test_r13_newline_survives_in_string_literal():
    s = one()
    s.set("A1", '="line\nbreak"')
    assert s.get("A1") == "line\nbreak"


def test_r13_first_offender_positional():
    s = one()
    s.set("A1", "=1/0")
    s.set("B1", '="x"+A1')  # string offends first, textually
    assert s.get("B1") == "#TYPE!"
    s.set("B2", '=A1+"x"')  # error reached first
    assert s.get("B2") == "#DIV!"


def test_r13_string_valued_formula_contribution():
    s = one()
    s.set("A1", '="x"')
    s.set("B1", "=A1")
    assert s.get("B1") == "x"
    s.set("B2", '=A1="x"')
    assert s.get("B2") == 1
    s.set("B3", "=A1*2")
    assert s.get("B3") == "#TYPE!"


# ======================================================================
# R14 — CONCAT and LEN
# ======================================================================
@pytest.mark.parametrize("src,expected", [
    ('=CONCAT("a","b")', "ab"),
    ('=CONCAT("a")', "a"),
    ('=CONCAT(1,"x",2+3)', "1x5"),
    ("=CONCAT(007)", "7"),          # decimal rendering of the value
    ("=CONCAT(-5)", "-5"),
    ('=CONCAT("")', ""),
    ('=CONCAT(CONCAT("a","b"),"c")', "abc"),
    ('=CONCAT(1=2, 2=2)', "01"),
    ('=LEN("abc")', 3),
    ('=LEN("")', 0),
    ("=LEN(-12)", 3),
    ("=LEN(0)", 1),
    ('=LEN(CONCAT("ab","c"))', 3),
    ('=LEN("a b")', 3),
])
def test_r14_concat_len_values(src, expected):
    s = one()
    s.set("C9", src)
    assert s.get("C9") == expected


def test_r14_empty_cell_argument_renders_zero():
    s = one()
    s.set("B1", "=CONCAT(A1)")   # empty ref contributes int 0 -> "0"
    assert s.get("B1") == "0"
    s.set("B2", "=LEN(A1)")
    assert s.get("B2") == 1


def test_r14_error_propagation_left_to_right():
    s = one()
    s.set("B1", '=CONCAT(1/0,"x")')
    assert s.get("B1") == "#DIV!"
    s.set("B2", '=CONCAT("x",A0)')
    assert s.get("B2") == "#REF!"
    s.set("B3", "=LEN(1/0)")
    assert s.get("B3") == "#DIV!"


def test_r14_concat_range_is_parse_error():
    s = one()
    s.set("B1", "=CONCAT(A1:A2)")
    assert s.get("B1") == "#PARSE!"


# ======================================================================
# R15 — IF
# ======================================================================
@pytest.mark.parametrize("src,expected", [
    ("=IF(1,10,20)", 10),
    ("=IF(0,10,20)", 20),
    ("=IF(5,10,20)", 10),        # any nonzero selects the second arg
    ("=IF(-1,10,20)", 10),
    ('=IF(2>1,"y","n")', "y"),
    ('=IF(1,"s",2)', "s"),       # result may be any type
    ("=IF(1/0,1,2)", "#DIV!"),   # error condition is the result
    ('=IF("x",1,2)', "#TYPE!"),  # str condition
    ("=IF(1,7,1/0)", 7),         # unselected branch error invisible
    ("=IF(0,A0,7)", 7),
    ("=IF(0,1/0,IF(1,9,8))", 9),
])
def test_r15_if_values(src, expected):
    s = one()
    s.set("C9", src)
    assert s.get("C9") == expected


def test_r15_selected_branch_error_propagates():
    s = one()
    s.set("C9", "=IF(1,1/0,7)")
    assert s.get("C9") == "#DIV!"


def test_r15_unselected_branch_cell_untouched_by_value():
    s = one()
    s.set("B1", "=B1")             # would be #CYCLE! if evaluated
    s.set("C1", "=IF(1,42,B1)")
    assert s.get("C1") == 42


# ======================================================================
# R16 — $ marks
# ======================================================================
def test_r16_dollar_forms_all_denote_same_cell():
    s = one()
    s.set("A1", 7)
    for src in ("=$A$1", "=$A1", "=A$1", "=A1"):
        s.set("B1", src)
        assert s.get("B1") == 7, src


def test_r16_dollar_in_ranges_and_validity():
    s = one()
    s.set("A1", 1)
    s.set("B2", 2)
    s.set("C5", "=SUM($A$1:B$2)")
    assert s.get("C5") == 3
    s.set("C6", "=$A$0")           # denotes what A0 denotes
    assert s.get("C6") == "#REF!"


def test_r16_dollar_cycle_unaffected():
    s = one()
    s.set("A1", "=$A$1")
    assert s.get("A1") == "#CYCLE!"


@pytest.mark.parametrize("src", ["=$FOO", "=$$A1", "=A1$", "=$A", "=$1"])
def test_r16_bad_dollar_is_parse_error(src):
    s = one()
    s.set("B1", src)
    assert s.get("B1") == "#PARSE!"


# ======================================================================
# R17 — copy
# ======================================================================
def test_r17_literal_copy_and_return():
    s = one()
    s.set("A1", 42)
    assert s.copy("A1", "B2") is None
    assert s.get("B2") == 42
    s.set("A2", "text")
    s.copy("A2", "B3")
    assert s.get("B3") == "text"


def test_r17_relative_shift_and_anchors():
    s = one()
    s.set("A1", 1)
    s.set("B1", 10)
    s.set("C2", 100)
    s.set("B2", "=$A$1+B1")
    s.copy("B2", "C3")            # delta (+1,+1): "=$A$1+C2"
    assert s.get("C3") == 101
    s.set("D2", "=A$1+$A2")       # col shifts on first, row on second
    s.set("A2", 5)
    s.copy("D2", "E3")            # -> "=B$1+$A3"
    s.set("B1", 10)
    s.set("A3", 7)
    assert s.get("E3") == 17


def test_r17_out_of_grid_ref_becomes_reference_error():
    s = one()
    s.set("A1", "=Z99+1")
    s.copy("A1", "B1")            # Z99 -> column out of grid
    assert s.get("B1") == "#REF!"
    s.set("A2", "=A1+1")
    s.copy("A2", "A1")            # A1 -> row 0: out of grid
    assert s.get("A1") == "#REF!"


def test_r17_out_of_grid_range_replaced_whole():
    s = one()
    s.set("B2", "=SUM(A1:B2)+5")
    s.copy("B2", "A1")            # both endpoints shift out -> =SUM(#REF!)+5
    assert s.get("A1") == "#REF!"
    s = one()
    s.set("A1", 1)
    s.set("B2", "=SUM(A1:Z99)")
    s.copy("B2", "B3")            # only BR leaves the grid: whole range
    assert s.get("B3") == "#REF!"


def test_r17_string_contents_never_touched():
    s = one()
    s.set("A1", 5)
    s.set("A2", '=CONCAT("B2", A1)')
    assert s.get("A2") == "B25"
    s.copy("A2", "A3")            # -> =CONCAT("B2", A2)
    assert s.get("A3") == "B2B25"
    s.set("B1", '="A1"')
    s.copy("B1", "C2")
    assert s.get("C2") == "A1"    # literal text preserved


def test_r17_nongrid_ref_token_kept_verbatim():
    s = one()
    s.set("A2", 9)
    s.set("B1", "=A1+A01")
    s.copy("B1", "B2")            # A1 shifts to A2; A01 kept verbatim
    assert s.get("B2") == "#REF!"  # a shifted-A01 misread would give 9+9


def test_r17_ref_error_token_kept():
    s = one()
    s.set("A1", "=#REF!")
    s.copy("A1", "B2")
    assert s.get("B2") == "#REF!"


def test_r17_unparseable_copied_byte_for_byte():
    s = one()
    s.set("A1", "=)")
    s.copy("A1", "B2")
    assert s.get("B2") == "#PARSE!"
    s.set("A2", "=A1:B2")         # grammar-illegal range position
    s.copy("A2", "C3")
    assert s.get("C3") == "#PARSE!"


def test_r17_copy_same_cell_and_journal():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=1+1")
    s.copy("A1", "A1")            # legal: zero shift
    assert s.get("A1") == 2
    assert wb.undo() is True      # the copy was journaled
    assert wb.undo() is True      # the set
    assert s.get("A1") is None


def test_r17_digit_growth():
    s = one()
    s.set("A9", 3)
    s.set("A10", 4)
    s.set("B1", "=A9+1")
    s.copy("B1", "B2")            # =A10+1
    assert s.get("B2") == 5


def test_r17_copy_value_errors_and_no_journal():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    for src, dst in (("D4", "E5"),      # empty src
                     ("A0", "B1"),      # invalid src address
                     ("A1", "B0"),      # invalid dst address
                     ("Ghost!A1", "B1"),  # unknown sheet qualifier
                     ("S1 !A1", "B1")):   # whitespace in qualified arg
        with pytest.raises(ValueError):
            s.copy(src, dst)
    with pytest.raises(ValueError):
        s.copy(None, "B1")
    assert wb.undo() is True      # failed copies journaled nothing
    assert s.get("A1") is None


def test_r17_cross_sheet_copy_rehosts_unqualified_refs():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 1)
    s2.set("A1", 2)
    s1.set("B1", "=A1")
    s1.copy("B1", "S2!B1")
    assert s2.get("B1") == 2      # re-resolves against the hosting sheet
    s2.copy("S1!B1", "C2")        # qualified src: "=A1" shifts by (+1,+1)
    s2.set("B2", 30)
    assert s2.get("C2") == 30     # "=B2" hosted on S2


def test_r17_qualifier_preserved_not_shifted():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("B2", 7)
    s1.set("A1", "=S2!A1")
    s1.copy("A1", "B2")           # -> =S2!B2 (qualifier kept)
    assert s1.get("B2") == 7


def test_r17_ghost_qualifier_still_shifts_ref_part():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "=Ghost!A1")
    s1.copy("A1", "B2")           # -> =Ghost!B2
    assert s1.get("B2") == "#REF!"
    g = wb.add_sheet("Ghost")
    g.set("A1", 3)
    g.set("B2", 5)
    assert s1.get("B2") == 5      # proves the ref part was shifted


# ======================================================================
# R18 — named ranges
# ======================================================================
def test_r18_define_and_use_name():
    s = one()
    s.set("A1", 7)
    assert s.define_name("FOO", "A1") is None
    s.set("B1", "=FOO")
    assert s.get("B1") == 7
    s.set("B2", "=SUM(FOO)")
    assert s.get("B2") == 7
    s.define_name("RECT", "A1:B2")
    s.set("C1", "=SUM(RECT)")
    assert s.get("C1") == 21      # A1=7, B1(=FOO)=7, B2(=SUM(FOO))=7
    s.set("C2", "=RECT")          # larger target used as a primary
    assert s.get("C2") == "#REF!"
    s.define_name("ONE", "A1:A1")  # 1x1 range acts as single address
    s.set("C3", "=ONE")
    assert s.get("C3") == 7


def test_r18_undefined_name():
    s = one()
    s.set("B1", "=NOPE")
    assert s.get("B1") == "#NAME!"
    s.set("B2", "=SUM(NOPE)")
    assert s.get("B2") == "#NAME!"


def test_r18_redefinition_replaces():
    s = one()
    s.set("A1", 1)
    s.set("A2", 2)
    s.define_name("N_X", "A1")
    s.set("B1", "=N_X")
    assert s.get("B1") == 1
    s.define_name("N_X", "A2")
    assert s.get("B1") == 2


def test_r18_count_over_name_structural():
    s = one()
    s.set("A1", 1)
    s.set("A2", "=1/0")
    s.define_name("POOL", "A1:A3")
    s.set("B1", "=COUNT(POOL)")
    assert s.get("B1") == 2


@pytest.mark.parametrize("bad", [
    "A1", "B22",          # REF shape
    "SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW",
    "foo", "Fo",          # lowercase
    "F", "_",             # too short
    "X" * 33,             # too long
    "1AB",                # starts with a digit
    "A-B", "A B",         # illegal characters
])
def test_r18_invalid_names_raise(bad):
    s = one()
    with pytest.raises(ValueError):
        s.define_name(bad, "A1")


@pytest.mark.parametrize("bad", [
    "B2:A1", "A0", "A1:A100", "a1", "A1:B2:C3", "", " A1", "A1 ",
    "$A$1", "Ghost!A1", "S1 !A1", "S1! A1", None, 5,
])
def test_r18_invalid_targets_raise(bad):
    wb = Workbook()
    s = wb.add_sheet("S1")
    with pytest.raises(ValueError):
        s.define_name("GOOD", bad)
    assert wb.undo() is True      # nothing was journaled by the failures
    assert wb.sheet_names == []


def test_r18_valid_name_shapes():
    s = one()
    s.set("A1", 3)
    for nm in ("_OK", "AB", "A_1", "ZZ", "X" * 32, "_2"):
        s.define_name(nm, "A1")
        s.set("B1", f"={nm}")
        assert s.get("B1") == 3, nm


def test_r18_per_sheet_namespaces():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 1)
    s1.define_name("FOO", "A1")
    s2.set("B1", "=FOO")          # resolution uses the hosting sheet
    assert s2.get("B1") == "#NAME!"
    s1.set("B1", "=FOO")
    assert s1.get("B1") == 1


def test_r18_qualified_target_cross_sheet():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("A1", 9)
    s1.define_name("FAR", "S2!A1")
    s1.set("B1", "=FAR")
    assert s1.get("B1") == 9
    s1.define_name("FARR", "S2!A1:B2")
    s2.set("B2", 1)
    s1.set("B2", "=SUM(FARR)")
    assert s1.get("B2") == 10


def test_r18_name_binding_snapshot_not_text():
    # the binding is resolved at define time to a target, and formulas
    # read the *current* binding thereafter
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", 1)
    s1.define_name("FOO", "A1")
    s1.set("C1", "=FOO+0")
    assert s1.get("C1") == 1
    s1.set("A1", 5)               # binding targets the cell, not the value
    assert s1.get("C1") == 5


def test_r18_journal_lifo_prevents_dangling():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    wb.add_sheet("S2")
    s1.define_name("FOO", "S2!A1")
    s1.set("B1", "=FOO")
    assert s1.get("B1") == 0
    assert wb.undo() is True      # undoes the set
    assert wb.undo() is True      # undoes define_name FIRST
    assert s1.get("B1") is None
    s1.set("B1", "=FOO")
    assert s1.get("B1") == "#NAME!"  # binding gone before S2 can go
    wb2 = Workbook()
    t1 = wb2.add_sheet("T1")
    wb2.add_sheet("T2")
    t1.define_name("N_A", "T2!A1")
    wb2.undo()                    # define undone
    assert wb2.undo() is True     # only now can T2 be removed
    assert wb2.sheet_names == ["T1"]


# ======================================================================
# R19 — undo/redo journal
# ======================================================================
def test_r19_empty_journal():
    wb = Workbook()
    assert wb.undo() is False
    assert wb.redo() is False


def test_r19_full_lifo_cycle():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.define_name("N_1", "A1")
    wb.advance_clock()
    s.copy("A1", "B1")
    s.set("C1", "=N_1")
    assert s.get("B1") == 1
    assert s.get("C1") == 1
    assert wb.undo() is True                 # C1 set
    assert s.get("C1") is None
    assert wb.undo() is True                 # copy
    assert s.get("B1") is None
    assert wb.undo() is True                 # clock
    assert wb.clock == 0
    assert wb.undo() is True                 # define_name
    assert wb.undo() is True                 # A1 set
    assert s.get("A1") is None
    assert wb.undo() is True                 # add_sheet
    assert wb.sheet_names == []
    assert wb.undo() is False
    for _ in range(6):                       # exact re-application, in order
        assert wb.redo() is True
    assert wb.redo() is False
    assert wb.sheet_names == ["S1"]
    assert wb.clock == 1
    assert s.get("A1") == 1
    assert s.get("B1") == 1
    assert s.get("C1") == 1


def test_r19_set_restores_never_set_state():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("A1", 2)
    assert wb.undo() is True
    assert s.get("A1") == 1
    assert wb.undo() is True
    assert s.get("A1") is None
    assert wb.redo() is True
    assert s.get("A1") == 1
    assert wb.redo() is True
    assert s.get("A1") == 2


def test_r19_new_op_clears_redo():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    assert wb.undo() is True
    s.set("B1", 2)                # journaled: clears redo
    assert wb.redo() is False
    assert s.get("A1") is None


def test_r19_observers_do_not_journal_or_clear_redo():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("B1", 2)
    assert wb.undo() is True
    s.get("A1")
    wb.sheet_names
    wb.clock
    wb.to_json()
    wb.sheet("S1")
    s.eval_count
    assert wb.redo() is True      # redo stack survived the observers
    assert s.get("B1") == 2


def test_r19_failed_calls_never_journal():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    with pytest.raises(ValueError):
        s.set("A0", 2)
    with pytest.raises(ValueError):
        s.set("A2", True)
    with pytest.raises(ValueError):
        s.define_name("A1", "A1")
    with pytest.raises(ValueError):
        s.copy("D4", "E5")
    with pytest.raises(ValueError):
        wb.add_sheet("S1")        # duplicate
    assert wb.undo() is True
    assert s.get("A1") is None    # the undo reverted the successful set


def test_r19_handle_bound_to_name():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    wb.undo()
    wb.undo()                     # sheet gone
    for access in (lambda: s.get("A1"), lambda: s.set("A1", 1),
                   lambda: s.copy("A1", "B1"),
                   lambda: s.define_name("N_1", "A1"),
                   lambda: s.eval_count):
        with pytest.raises(ValueError):
            access()
    assert wb.redo() is True      # sheet restored
    assert s.get("A1") is None    # same handle works again
    wb2 = Workbook()
    t = wb2.add_sheet("T1")
    wb2.undo()
    wb2.add_sheet("T1")           # fresh add_sheet of the same name
    t.set("A1", 5)                # old handle revives
    assert t.get("A1") == 5


def test_r19_advance_clock_journaled():
    wb = Workbook()
    assert wb.advance_clock() == 1
    assert wb.advance_clock() == 2
    assert wb.undo() is True
    assert wb.clock == 1
    assert wb.redo() is True
    assert wb.clock == 2


# ======================================================================
# R20 — undo/redo vs values (counters variants marked)
# ======================================================================
def test_r20_values_follow_restored_state():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("B1", "=A1*10")
    assert s.get("B1") == 10
    s.set("A1", 2)
    assert s.get("B1") == 20
    wb.undo()
    assert s.get("B1") == 10      # R11 against the restored contents
    wb.redo()
    assert s.get("B1") == 20


@counters
def test_r20_counters_monotonic_across_undo():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=1+1")
    s.get("A1")
    c0 = s.eval_count
    wb.undo()
    assert s.eval_count >= c0
    wb.redo()
    assert s.eval_count >= c0


@counters
def test_r20_undo_is_an_edit_no_content_comparison():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    s.set("A1", 1)                # identical content
    s.get("B1")
    c0 = s.eval_count
    wb.undo()                     # restores A1=1 (equal to prior state!)
    assert s.get("B1") == 2
    assert s.eval_count - c0 >= 1


@counters
def test_r20_irrelevant_undo_adds_zero():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    s.set("D9", 5)                # outside B1's closure
    s.get("B1")
    c0 = s.eval_count
    wb.undo()                     # reverts D9: still outside the closure
    assert s.get("B1") == 2
    assert s.eval_count == c0


# ======================================================================
# R21 — Workbook API root
# ======================================================================
def test_r21_empty_workbook():
    wb = Workbook()
    assert wb.sheet_names == []
    assert wb.clock == 0
    assert wb.undo() is False


def test_r21_add_sheet_and_lookup():
    wb = Workbook()
    s = wb.add_sheet("Sheet_1")
    s.set("A1", 1)
    assert wb.sheet("Sheet_1").get("A1") == 1
    with pytest.raises(ValueError):
        wb.sheet("Nope")
    with pytest.raises(ValueError):
        wb.sheet(5)


@pytest.mark.parametrize("bad", [
    "", "_x", "1a", "a" * 33, "S 1", "S-1", "S!1", None, 5, True,
])
def test_r21_invalid_sheet_names(bad):
    wb = Workbook()
    with pytest.raises(ValueError):
        wb.add_sheet(bad)
    assert wb.sheet_names == []


def test_r21_valid_and_case_sensitive_sheet_names():
    wb = Workbook()
    for nm in ("a", "A", "a" * 32, "Sheet_1", "s1", "S1"):
        wb.add_sheet(nm)
    assert wb.sheet_names == ["a", "A", "a" * 32, "Sheet_1", "s1", "S1"]
    with pytest.raises(ValueError):
        wb.add_sheet("S1")        # exact duplicate


def test_r21_sheet_names_fresh_list():
    wb = Workbook()
    wb.add_sheet("S1")
    lst = wb.sheet_names
    lst.append("junk")
    assert wb.sheet_names == ["S1"]


def test_r21_public_surface_exact():
    import gridcalc
    assert list(gridcalc.__all__) == ["Workbook"]
    assert not hasattr(gridcalc, "Sheet")
    wb = Workbook()
    h = wb.add_sheet("S1")
    assert {a for a in dir(wb) if not a.startswith("_")} == {
        "add_sheet", "sheet", "sheet_names", "undo", "redo",
        "advance_clock", "clock", "to_json", "from_json"}
    assert {a for a in dir(h) if not a.startswith("_")} == {
        "set", "get", "copy", "define_name", "eval_count"}


def test_r21_str_subclasses_api_wide():
    class MyStr(str):
        pass

    wb = Workbook()
    s = wb.add_sheet(MyStr("Q1"))
    assert all(type(n) is str for n in wb.sheet_names)
    s.set(MyStr("A1"), 1)
    assert wb.sheet(MyStr("Q1")).get("A1") == 1
    s.define_name(MyStr("FOO"), MyStr("A1"))
    s.set("B1", "=FOO")
    assert s.get("B1") == 1


def test_r21_handles_carry_no_identity_semantics():
    wb = Workbook()
    wb.add_sheet("S1")
    h1 = wb.sheet("S1")
    h2 = wb.sheet("S1")
    h1.set("A1", 3)
    assert h2.get("A1") == 3


@counters
def test_r21_eval_count_per_name_lifetime():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=1+1")
    s.get("A1")
    c0 = s.eval_count
    assert c0 >= 1
    wb.undo()                     # A1 gone
    wb.undo()                     # sheet gone
    wb.redo()                     # sheet back (empty)
    assert wb.sheet("S1").eval_count >= c0   # resumed, monotonic
    wb2 = Workbook()
    t = wb2.add_sheet("T1")
    t.set("A1", "=1+1")
    t.get("A1")
    c1 = t.eval_count
    wb2.undo()
    wb2.undo()
    t2 = wb2.add_sheet("T1")      # fresh add_sheet, same name
    assert t2.eval_count >= c1    # counter resumes per name


# ======================================================================
# R22 — sheet qualifiers
# ======================================================================
def test_r22_qualified_ref_and_range():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("A1", 10)
    s2.set("B2", 20)
    s1.set("A1", "=S2!A1+1")
    assert s1.get("A1") == 11
    s1.set("A2", "=SUM(S2!A1:B2)")
    assert s1.get("A2") == 30
    s1.set("A3", "= S2 ! A1 + 1")   # whitespace around ! and tokens
    assert s1.get("A3") == 11
    s1.set("A4", "=S2!$B$2")
    assert s1.get("A4") == 20


def test_r22_unknown_qualifier_is_ref_error_then_live():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "=Ghost!B1+1")
    assert s1.get("A1") == "#REF!"
    g = wb.add_sheet("Ghost")
    g.set("B1", 5)
    assert s1.get("A1") == 6      # add_sheet made the qualifier live
    wb.undo()                     # removes the B1 set
    wb.undo()                     # removes Ghost
    assert s1.get("A1") == "#REF!"


def test_r22_tokenization_precedence():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    a1 = wb.add_sheet("A1")       # sheet named like a REF
    su = wb.add_sheet("SUM")      # sheet named like a function
    a1.set("B2", 7)
    su.set("A1", 8)
    s1.set("C1", "=A1!B2")
    assert s1.get("C1") == 7
    s1.set("C2", "=SUM!A1")
    assert s1.get("C2") == 8
    s1.set("C3", "=FOO!A1")       # NAME-shaped but well-shaped qualifier
    assert s1.get("C3") == "#REF!"


def test_r22_bad_qualifier_shapes():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "=_FOO!A1")      # cannot be a sheet name -> grammar
    assert s1.get("A1") == "#PARSE!"
    s1.set("A2", "=SUM(S1!A1:S1!B2)")   # second qualifier in a range
    assert s1.get("A2") == "#PARSE!"
    s1.set("A3", "=SUM(A1:S1!B2)")
    assert s1.get("A3") == "#PARSE!"
    s1.set("A4", "=S1!A1:B2")     # a range is not a primary
    assert s1.get("A4") == "#PARSE!"


def test_r22_case_sensitive_sheet_match():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    wb.add_sheet("Data")
    s1.set("A1", "=DATA!B1")
    assert s1.get("A1") == "#REF!"


@counters
def test_r22_add_sheet_edit_touches_mentioning_formulas():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s1.set("A1", "=Ghost!B1+1")
    s1.set("A2", "=1+1")          # does not mention Ghost
    assert s1.get("A1") == "#REF!"
    assert s1.get("A2") == 2
    c0 = s1.eval_count
    wb.add_sheet("Ghost")         # edit touching A1, not A2
    assert s1.get("A2") == 2
    assert s1.eval_count == c0    # irrelevant for A2
    assert s1.get("A1") == 1
    assert s1.eval_count - c0 >= 1


# ======================================================================
# R23 — v1 semantics lifted to (sheet, address)
# ======================================================================
def test_r23_cross_sheet_cycle():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", "=S2!A1")
    s2.set("A1", "=S1!A1")
    assert s1.get("A1") == "#CYCLE!"
    assert s2.get("A1") == "#CYCLE!"
    s2.set("A1", 4)
    assert s1.get("A1") == 4


def test_r23_cross_sheet_range_row_major_order():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("A1", "x")             # visited first: #TYPE! fuel
    s2.set("B1", "=1/0")
    s1.set("C1", "=SUM(S2!A1:B1)")
    assert s1.get("C1") == "#TYPE!"


def test_r23_qualified_copy_and_define_args():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 5)
    s1.copy("S1!A1", "S2!B2")
    assert s2.get("B2") == 5
    with pytest.raises(ValueError):
        s1.copy("A1", "Nope!B2")
    with pytest.raises(ValueError):
        s1.define_name("N_1", "Nope!A1")


@counters
def test_r23_counters_increment_owning_sheet():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s2.set("B1", "=1+1")
    s1.set("A1", "=S2!B1")
    c1, c2 = s1.eval_count, s2.eval_count
    assert s1.get("A1") == 2
    assert s1.eval_count - c1 == 1   # A1 owned by S1
    assert s2.eval_count - c2 == 1   # B1 owned by S2


# ======================================================================
# R24 — persistence
# ======================================================================
def _rich_workbook():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("s2")
    s1.set("A1", -7)
    s1.set("A2", "")
    s1.set("A3", "#REF!")
    s1.set("A4", "line\nbreak\ttab")
    s1.set("B1", "=A1+1")
    s1.set("B2", "=$A$1")
    s1.set("B3", "=s2!B9+NOW()")
    s1.set("B4", "=#REF!")
    s1.set("B5", "=)")
    s1.set("B6", '=CONCAT("x", A1)')
    s1.set("B7", "=  A1 +  1")
    s2.set("B9", 100)
    s1.define_name("FOO", "A1:B2")
    s2.define_name("FAR", "S1!A1")
    wb.advance_clock()
    wb.advance_clock()
    s1.set("C9", 1)
    wb.undo()                     # C9 gone: undone state is not persisted
    return wb


_PROBE = [("S1", a) for a in ("A1", "A2", "A3", "A4", "B1", "B2", "B3",
                              "B4", "B5", "B6", "B7", "C9")] + \
    [("s2", "B9")]


def test_r24_to_json_is_loadable_str():
    wb = _rich_workbook()
    out = wb.to_json()
    assert type(out) is str
    json.loads(out)


def test_r24_round_trip_restores_exactly():
    wb = _rich_workbook()
    w2 = Workbook.from_json(wb.to_json())
    assert w2.sheet_names == wb.sheet_names
    assert w2.clock == wb.clock == 2
    for sname, addr in _PROBE:
        assert w2.sheet(sname).get(addr) == wb.sheet(sname).get(addr), \
            (sname, addr)
    assert w2.sheet("S1").get("B3") == 102   # qualified + NOW at clock 2
    assert w2.undo() is False     # journal reset
    assert w2.redo() is False


def test_r24_loaded_workbook_is_new_and_independent():
    wb = _rich_workbook()
    w2 = Workbook.from_json(wb.to_json())
    w2.sheet("S1").set("A1", 999)
    assert wb.sheet("S1").get("A1") == -7
    wb.sheet("S1").set("A2", "changed")
    assert w2.sheet("S1").get("A2") == ""


@counters
def test_r24_to_json_pure_observation():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=1+1")
    wb.to_json()
    assert s.eval_count == 0      # evaluated nothing
    assert wb.undo() is True      # journaled nothing: undo pops the set
    assert s.get("A1") is None


@counters
def test_r24_loaded_counters_zero_and_fresh_compute():
    wb = _rich_workbook()
    wb.sheet("S1").get("B1")
    assert wb.sheet("S1").eval_count > 0
    w2 = Workbook.from_json(wb.to_json())
    assert w2.sheet("S1").eval_count == 0
    assert w2.sheet("s2").eval_count == 0
    c0 = w2.sheet("S1").eval_count
    assert w2.sheet("S1").get("B1") == -6
    assert w2.sheet("S1").eval_count - c0 == 1  # computed fresh


@pytest.mark.parametrize("bad", [
    5, None, b"{}", [], {}, True, 1.5,
])
def test_r24_from_json_non_str_raises(bad):
    with pytest.raises(ValueError):
        Workbook.from_json(bad)


@pytest.mark.parametrize("bad", [
    "", "{", "not json", "{'a':1}", "=1+1", "nul", "{]",
])
def test_r24_from_json_invalid_json_raises(bad):
    with pytest.raises(ValueError):
        Workbook.from_json(bad)


@pytest.mark.parametrize("bad", [
    "null", "[]", "5", '"x"', "-3", '["sheets"]', '[[]]',
    "[" * 30 + "1" + "]" * 30,
])
def test_r24_from_json_wrong_shape_raises(bad):
    with pytest.raises(ValueError):
        Workbook.from_json(bad)


@pytest.mark.parametrize("bad", [
    "1.0", "1.5", "NaN", "Infinity", "-Infinity", "1e3", "[1.5]",
    '{"clock": 1.0, "sheets": []}',
])
def test_r24_from_json_floats_raise(bad):
    with pytest.raises(ValueError):
        Workbook.from_json(bad)


def test_r24_security_static_smoke():
    """Engineer Lens probe: runtime code contains no code-execution
    primitives. Bare eval(/exec(/compile( calls are flagged; attribute
    access like re.compile( is not code execution and is allowed."""
    import gridcalc
    pkg = gridcalc.__file__
    files = []
    if os.path.basename(pkg) == "__init__.py":
        root = os.path.dirname(pkg)
        for dirpath, _dirs, names in os.walk(root):
            files += [os.path.join(dirpath, n) for n in names
                      if n.endswith(".py")]
    else:
        files = [pkg]
    bad = re.compile(
        r"(?<![A-Za-z0-9_.])(?:eval|exec|compile)\s*\(|"
        r"__import__|(?<![A-Za-z0-9_])importlib|(?<![A-Za-z0-9_])pickle")
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        m = bad.search(src)
        assert not m, (f, m.group(0))


# ======================================================================
# R25 — round-trip equivalence under further operations
# ======================================================================
def test_r25_same_ops_after_round_trip():
    wb = _rich_workbook()
    w2 = Workbook.from_json(wb.to_json())
    for w in (wb, w2):
        h = w.sheet("S1")
        h.copy("B1", "C2")            # rewrite happens over restored text
        h.set("D1", "=SUM(FOO)")
        h.define_name("FOO", "A1:A1")
        w.advance_clock()
    for sname, addr in _PROBE + [("S1", "C2"), ("S1", "D1")]:
        assert w2.sheet(sname).get(addr) == wb.sheet(sname).get(addr), \
            (sname, addr)
    assert wb.clock == w2.clock


def test_r25_copy_rewrites_restored_text_identically():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=Z99+$A$2+B1")
    w2 = Workbook.from_json(wb.to_json())
    s.copy("A1", "B2")
    w2.sheet("S1").copy("A1", "B2")
    # both rewrites: Z99 -> out of grid -> #REF!; $A$2 kept; B1 -> C2
    for w in (wb, w2):
        w.sheet("S1").set("C2", 5)
        w.sheet("S1").set("A2", 3)
    assert wb.sheet("S1").get("B2") == w2.sheet("S1").get("B2") == "#REF!"
    # and the same starting from a value-bearing formula
    wb2 = Workbook()
    t = wb2.add_sheet("S1")
    t.set("A1", "=$A$2+B1")
    t.set("A2", 3)
    w3 = Workbook.from_json(wb2.to_json())
    t.copy("A1", "B2")
    w3.sheet("S1").copy("A1", "B2")
    t.set("C2", 5)
    w3.sheet("S1").set("C2", 5)
    assert t.get("B2") == w3.sheet("S1").get("B2") == 8


def test_r25_second_round_trip():
    wb = _rich_workbook()
    w2 = Workbook.from_json(wb.to_json())
    w3 = Workbook.from_json(w2.to_json())
    for sname, addr in _PROBE:
        assert w3.sheet(sname).get(addr) == wb.sheet(sname).get(addr)


# ======================================================================
# R26 — clock and NOW()
# ======================================================================
def test_r26_clock_property_and_advance():
    wb = Workbook()
    assert wb.clock == 0
    assert wb.advance_clock() == 1
    assert wb.advance_clock() == 2
    assert wb.clock == 2


def test_r26_now_values():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    assert s.get("A1") == 0
    wb.advance_clock()
    assert s.get("A1") == 1
    s.set("A2", "=NOW ( )")       # whitespace is fine
    assert s.get("A2") == 1
    s.set("A3", "=NOW()*10+NOW()")
    assert s.get("A3") == 11
    s.set("A4", "=-NOW()")
    assert s.get("A4") == -1


@pytest.mark.parametrize("src", ["=NOW(1)", "=now()", "=NOW", "=NOW(A1)"])
def test_r26_bad_now_forms(src):
    s = one()
    s.set("B1", src)
    assert s.get("B1") == "#PARSE!"


def test_r26_clock_undo_redo_affects_now():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()+B1")
    s.set("B1", 100)
    wb.advance_clock()
    wb.advance_clock()
    assert s.get("A1") == 102
    wb.undo()
    assert s.get("A1") == 101     # values obey R11 at the restored clock
    wb.redo()
    assert s.get("A1") == 102


# ======================================================================
# R27 — volatility (counter patterns marked)
# ======================================================================
def test_r27_volatile_chain_values():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    s.set("B1", "=A1*2")
    assert s.get("B1") == 0
    wb.advance_clock()
    assert s.get("B1") == 2       # naive-equivalent at the current clock


@counters
def test_r27_repeat_read_stable_within_clock():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", "=NOW()")
    s.get("A1")
    c0 = s.eval_count
    assert s.get("A1") == 0       # no edit between: adds 0 even if volatile
    assert s.eval_count == c0


@counters
def test_r27_clock_edit_irrelevant_for_nonvolatile():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    wb.advance_clock()
    assert s.get("B1") == 2
    assert s.eval_count == c0     # closure has no volatile member


@counters
def test_r27_tight_volatile_bound_after_warmup():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("A1", 5)
    s.set("X1", "=NOW()+A1")      # volatile
    s.set("Y1", "=A1*2")          # not volatile
    s.set("W1", "=X1+Y1")         # volatile via closure
    s.get("X1")
    s.get("Y1")
    s.get("W1")                   # warm every closure member
    c0 = s.eval_count
    wb.advance_clock()
    wb.advance_clock()            # clock-only edits
    assert s.get("W1") == 5 + 2 + 10
    assert s.eval_count - c0 <= 2  # volatile members only: W1, X1


@counters
def test_r27_now_in_unselected_branch_is_volatile():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("V1", "=IF(0, NOW(), 5)")
    s.get("V1")
    c0 = s.eval_count
    wb.advance_clock()            # touches V1: syntactically volatile
    assert s.get("V1") == 5
    assert s.eval_count - c0 == 1


@counters
def test_r27_now_inside_string_is_not_volatile():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("V1", '=CONCAT("NOW()", "")')
    s.get("V1")
    c0 = s.eval_count
    wb.advance_clock()
    assert s.get("V1") == "NOW()"
    assert s.eval_count == c0     # text, not a call


@counters
def test_r27_undo_of_clock_is_clock_edit():
    wb = Workbook()
    s = wb.add_sheet("S1")
    s.set("V1", "=NOW()")
    wb.advance_clock()
    assert s.get("V1") == 1
    c0 = s.eval_count
    wb.undo()
    assert s.get("V1") == 0
    assert s.eval_count - c0 >= 1


# ======================================================================
# R28 — XL bounds
# ======================================================================
def test_r28_cross_sheet_reach_within_bounds():
    wb = Workbook()
    sheets = [wb.add_sheet(f"P{i}") for i in range(3)]
    addrs = [f"{c}{r}" for r in range(1, 5)
             for c in "ABCDEFGHIJKLMNOPQRSTU"]  # 84 per sheet
    chain = [(i % 3, addrs[i // 3]) for i in range(250)]
    for i in range(249):
        nsheet, naddr = chain[i + 1]
        sheets[chain[i][0]].set(chain[i][1], f"=P{nsheet}!{naddr}")
    sheets[chain[249][0]].set(chain[249][1], 7)
    assert sheets[chain[0][0]].get(chain[0][1]) == 7


def test_r28_string_bound_4096():
    s = one()
    s.set("A1", '="' + "x" * 256 + '"')
    args = ",".join(["A1"] * 16)
    s.set("B1", f"=CONCAT({args})")
    assert s.get("B1") == "x" * 4096   # exactly at the bound: guaranteed
    s.set("C1", "=LEN(B1)")
    assert s.get("C1") == 4096


def test_r28_oversized_stored_text_copies_byte_for_byte():
    wb = Workbook()
    s = wb.add_sheet("S1")
    big = "=" + "+".join(["A1"] * 200)   # parseable but > 512 chars
    s.set("C1", big)                     # set stores verbatim
    s.copy("C1", "C2")                   # still succeeds and journals
    assert wb.undo() is True
    assert s.get("C2") is None
    assert wb.redo() is True
    assert wb.undo() is True and wb.undo() is True
    assert s.get("C1") is None


def test_r28_out_of_bounds_damage_confined_across_sheets():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("Z9", "=" + "+".join(["1"] * 400))   # out of bounds
    try:
        s1.get("Z9")
    except Exception:
        pass
    s2.set("A1", 1)
    s2.set("B1", "=A1+S1!A1+1")
    assert s2.get("B1") == 2      # within-bounds gets keep every guarantee


# ======================================================================
# R11 / R25 — dense small-region differential (12 cells x 3 sheets)
# ======================================================================
_D_SHEETS = ("S1", "S2", "S3")
_D_ADDRS = ("A1", "A2", "B1", "B2")
_D_NAMES = ("FOO", "BAR", "BAZ")
_D_STRINGS = ("", "x", "hi", "#DIV!", "A1", "NOW()")


def _d_ref(rng):
    a = rng.choice(_D_ADDRS)
    if rng.random() < 0.25:
        a = (("$" if rng.random() < 0.5 else "") + a[0] +
             ("$" if rng.random() < 0.5 else "") + a[1:])
    if rng.random() < 0.30:
        a = rng.choice(_D_SHEETS) + "!" + a
    return a


def _d_range(rng):
    if rng.random() < 0.05:
        core = "B2:A1"            # mis-ordered: #REF! coverage
    else:
        c1, c2 = sorted(rng.choice("AB") for _ in range(2))
        r1, r2 = sorted(rng.choice("12") for _ in range(2))
        core = f"{c1}{r1}:{c2}{r2}"
    if rng.random() < 0.30:
        core = rng.choice(_D_SHEETS) + "!" + core
    return core


def _d_expr(rng, depth):
    r = rng.random()
    if depth <= 0 or r < 0.30:
        leaf = rng.random()
        if leaf < 0.35:
            return str(rng.randrange(-9, 100))
        if leaf < 0.70:
            return _d_ref(rng)
        if leaf < 0.80:
            return '"' + rng.choice(_D_STRINGS) + '"'
        if leaf < 0.86:
            return "NOW()"
        if leaf < 0.94:
            return rng.choice(_D_NAMES)
        return rng.choice(("#REF!", "A0", "A100"))
    if r < 0.55:
        op = rng.choice(("+", "-", "/", "=", "<>", "<", "<=", ">", ">="))
        return f"({_d_expr(rng, depth - 1)}{op}{_d_expr(rng, depth - 1)})"
    if r < 0.62:  # keep magnitudes within R12(c): multiply by constants
        return f"({_d_expr(rng, depth - 1)}*{rng.randrange(0, 4)})"
    if r < 0.78:
        f = rng.choice(("SUM", "MIN", "MAX", "COUNT"))
        arg = rng.choice(_D_NAMES) if rng.random() < 0.15 else _d_range(rng)
        return f"{f}({arg})"
    if r < 0.86:  # keep string growth within R12(d): one ref + literal
        return (f'CONCAT({_d_expr(rng, 0)},'
                f'"{rng.choice(_D_STRINGS)}")')
    if r < 0.92:
        return f"LEN({_d_expr(rng, depth - 1)})"
    return (f"IF({_d_expr(rng, depth - 1)},{_d_expr(rng, depth - 1)},"
            f"{_d_expr(rng, depth - 1)})")


def _d_formula(rng):
    if rng.random() < 0.03:
        return rng.choice(("=)", "=A1:B2", "=", "=$FOO"))
    return "=" + _d_expr(rng, 2)


def _d_parity(arm_call, ref_call, ctx):
    """Run the same call on both sides: identical ValueError behavior and
    identical return values."""
    try:
        a = arm_call()
        a_raised = False
    except ValueError:
        a_raised = True
        a = None
    try:
        e = ref_call()
        e_raised = False
    except ValueError:
        e_raised = True
        e = None
    assert a_raised == e_raised, (ctx, "ValueError parity")
    if not a_raised:
        assert a == e, (ctx, a, e)


def _d_sweep(arm_wb, ref_wb, ctx):
    assert arm_wb.sheet_names == ref_wb.sheet_names, ctx
    assert arm_wb.clock == ref_wb.clock, ctx
    for sname in ref_wb.sheet_names:
        ah, rh = arm_wb.sheet(sname), ref_wb.sheet(sname)
        for addr in _D_ADDRS:
            assert ah.get(addr) == rh.get(addr), (ctx, sname, addr)


def _run_differential(seed, n_ops=70):
    rng = random.Random(seed)
    arm_wb, ref_wb = Workbook(), RefWorkbook()
    for nm in _D_SHEETS:
        arm_wb.add_sheet(nm)
        ref_wb.add_sheet(nm)

    def ensure(sname):
        if sname not in ref_wb.sheet_names:
            arm_wb.add_sheet(sname)
            ref_wb.add_sheet(sname)

    for i in range(n_ops):
        ctx = (seed, i)
        r = rng.random()
        host = rng.choice(_D_SHEETS)
        if r < 0.44:  # set (literal int / literal str / formula)
            addr = rng.choice(_D_ADDRS)
            kind = rng.random()
            if kind < 0.35:
                raw = rng.randrange(-99, 1000)
            elif kind < 0.50:
                raw = rng.choice(_D_STRINGS)
            else:
                raw = _d_formula(rng)
            ensure(host)
            _d_parity(lambda: arm_wb.sheet(host).set(addr, raw),
                      lambda: ref_wb.sheet(host).set(addr, raw),
                      (ctx, "set", host, addr, raw))
        elif r < 0.58:  # get
            addr = rng.choice(_D_ADDRS)
            ensure(host)
            a = arm_wb.sheet(host).get(addr)
            e = ref_wb.sheet(host).get(addr)
            assert a == e, (ctx, "get", host, addr, a, e)
        elif r < 0.66:  # copy (may legally raise: empty src / ghost sheet)
            src, dst = rng.choice(_D_ADDRS), rng.choice(_D_ADDRS)
            if rng.random() < 0.4:
                src = rng.choice(_D_SHEETS + ("Ghost",)) + "!" + src
            if rng.random() < 0.3:
                dst = rng.choice(_D_SHEETS) + "!" + dst
            ensure(host)
            _d_parity(lambda: arm_wb.sheet(host).copy(src, dst),
                      lambda: ref_wb.sheet(host).copy(src, dst),
                      (ctx, "copy", host, src, dst))
        elif r < 0.74:  # define_name (rare invalid targets)
            nm = rng.choice(_D_NAMES)
            tr = rng.random()
            if tr < 0.4:
                target = rng.choice(_D_ADDRS)
            elif tr < 0.7:
                target = _d_range(rng)        # maybe qualified, no spaces
            else:
                target = rng.choice(("B2:A1", "Ghost!A1", "A0", "$A$1"))
            ensure(host)
            _d_parity(
                lambda: arm_wb.sheet(host).define_name(nm, target),
                lambda: ref_wb.sheet(host).define_name(nm, target),
                (ctx, "define_name", host, nm, target))
        elif r < 0.79:  # advance_clock
            a = arm_wb.advance_clock()
            e = ref_wb.advance_clock()
            assert a == e, (ctx, "advance_clock", a, e)
        elif r < 0.88:  # undo
            assert arm_wb.undo() == ref_wb.undo(), (ctx, "undo")
        elif r < 0.95:  # redo
            assert arm_wb.redo() == ref_wb.redo(), (ctx, "redo")
        else:  # to_json/from_json round-trip on both sides
            arm_wb = Workbook.from_json(arm_wb.to_json())
            ref_wb = RefWorkbook.from_json(ref_wb.to_json())
            assert arm_wb.sheet_names == ref_wb.sheet_names, ctx
            assert arm_wb.clock == ref_wb.clock, ctx
        if i % 10 == 9:
            _d_sweep(arm_wb, ref_wb, (ctx, "sweep"))
    _d_sweep(arm_wb, ref_wb, (seed, "final"))


_N_SEEDS = int(os.environ.get("GRIDCALC_XL_DIFF_SEEDS", "120"))


@pytest.mark.parametrize("seed", range(_N_SEEDS))
def test_r11_dense_differential_vs_naive_reference(seed):
    _run_differential(seed)
