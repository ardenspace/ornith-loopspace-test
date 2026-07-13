"""Held-out oracle for gridcalc (Experiment W). Authored from spec.md
alone, pre-registered before either arm ran. Grade an arm with:

    PYTHONPATH=<arm-repo> python3 -m pytest gridcalc_oracle.py -q

Test names carry their R-group (test_rNN_*) so the trajectory grader can
compute per-requirement pass rates per snapshot. Self-test (reference
graded against itself; R10 excluded — the naive reference doesn't model
eval_count):

    PYTHONPATH=grading:grading/selftest_shim \
        python3 -m pytest grading/gridcalc_oracle.py -q -k "not r10"
"""
import random

import pytest

from gridcalc import Sheet
from gridcalc_ref import RefSheet


# ---------------------------------------------------------------- R1
def test_r01_valid_addresses():
    s = Sheet()
    for a in ("A1", "Z99", "M50", "A99", "Z1"):
        s.set(a, 1)
        assert s.get(a) == 1


@pytest.mark.parametrize("bad", [
    "a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1", "1A", "A", "1",
])
def test_r01_invalid_address_strings(bad):
    s = Sheet()
    with pytest.raises(ValueError):
        s.get(bad)
    with pytest.raises(ValueError):
        s.set(bad, 1)


@pytest.mark.parametrize("bad", [5, None, True, 1.5])
def test_r01_non_str_addresses(bad):
    s = Sheet()
    with pytest.raises(ValueError):
        s.get(bad)


def test_r01_failing_get_state_unchanged():
    s = Sheet()
    s.set("A1", "=1+1")
    before = s.eval_count
    with pytest.raises(ValueError):
        s.get("A100")
    assert s.eval_count == before
    assert s.get("A1") == 2


# ---------------------------------------------------------------- R2
def test_r02_literal_roundtrip_and_none():
    s = Sheet()
    assert s.get("B2") is None
    s.set("B2", 42)
    assert s.get("B2") == 42
    s.set("B2", "hello")
    assert s.get("B2") == "hello"
    s.set("B2", -7)
    assert s.get("B2") == -7


def test_r02_bool_and_bad_types_raise():
    s = Sheet()
    for bad in (True, False, 1.5, None, [1], {"a": 1}):
        with pytest.raises(ValueError):
            s.set("A1", bad)
    assert s.get("A1") is None  # failed sets left the sheet unchanged


def test_r02_subclass_normalization():
    class MyInt(int):
        pass

    class MyStr(str):
        pass

    s = Sheet()
    s.set("A1", MyInt(7))
    assert type(s.get("A1")) is int and s.get("A1") == 7
    s.set("A2", MyStr("hi"))
    assert type(s.get("A2")) is str and s.get("A2") == "hi"
    s.set(MyStr("A3"), 5)  # str subclass in the address position
    assert s.get("A3") == 5


def test_r02_set_returns_none_and_replaces():
    s = Sheet()
    assert s.set("A1", 1) is None
    s.set("A1", "text")
    assert s.get("A1") == "text"
    s.set("A1", "=1+1")
    assert s.get("A1") == 2


# ---------------------------------------------------------------- R3
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
    s = Sheet()
    s.set("A1", src)
    assert s.get("A1") == expected


@pytest.mark.parametrize("src", [
    "=", "=1 < = 2", "=a1", "=AA1", "=sum(A1:B2)", "=AVG(A1:A2)",
    "=1++", "=(1+2", "=1 ? 2", "=SUM(A1)", "=A1:B2", "=SUM((A1:B2))",
])
def test_r03_parse_errors(src):
    s = Sheet()
    s.set("A1", src)
    assert s.get("A1") == "#PARSE!"


# ---------------------------------------------------------------- R4
@pytest.mark.parametrize("src,expected", [
    ("=7/2", 3),
    ("=-7/2", -3),
    ("=7/-2", -3),
    ("=0/5", 0),
    ("=7/0", "#DIV!"),
])
def test_r04_division(src, expected):
    s = Sheet()
    s.set("A1", src)
    assert s.get("A1") == expected


# ---------------------------------------------------------------- R5
def test_r05_error_propagates_through_refs():
    s = Sheet()
    s.set("A1", "=1/0")
    s.set("B1", "=A1+1")
    assert s.get("B1") == "#DIV!"


def test_r05_leftmost_error_wins_textually():
    s = Sheet()
    s.set("B1", "=1/0")   # DIV
    s.set("C1", "=A0")    # REF
    s.set("D1", "=Z9+B1*C1")  # Z9 empty(0), then B1 → DIV first
    assert s.get("D1") == "#DIV!"
    s.set("E1", "=C1+B1")
    assert s.get("E1") == "#REF!"


# ---------------------------------------------------------------- R6
def test_r06_reference_numeric_contexts():
    s = Sheet()
    assert_bare = Sheet()
    s.set("A1", "=Z9+1")            # empty ref contributes 0
    assert s.get("A1") == 1
    s.set("B1", "hi")
    s.set("B2", "=B1")              # bare ref to string → #TYPE!
    assert s.get("B2") == "#TYPE!"
    s.set("B3", "=B1+1")
    assert s.get("B3") == "#TYPE!"
    s.set("B4", "=B1=1")            # comparison with string → #TYPE!
    assert s.get("B4") == "#TYPE!"
    assert_bare.set("C1", "=C2")    # bare ref to empty → 0
    assert assert_bare.get("C1") == 0


@pytest.mark.parametrize("src", ["=A01", "=A0", "=A100"])
def test_r06_refshaped_but_out_of_grid(src):
    s = Sheet()
    s.set("B1", src)
    assert s.get("B1") == "#REF!"


def test_r06_formula_chain():
    s = Sheet()
    s.set("A1", 5)
    s.set("A2", "=A1*2")
    s.set("A3", "=A2+1")
    assert s.get("A3") == 11
    s.set("A1", 6)
    assert s.get("A3") == 13  # values reflect current sheet


# ---------------------------------------------------------------- R7
@pytest.mark.parametrize("src", ["=SUM(B2:A1)", "=SUM(A0:B2)", "=SUM(A1:A100)"])
def test_r07_invalid_ranges(src):
    s = Sheet()
    s.set("C5", src)
    assert s.get("C5") == "#REF!"


def test_r07_whitespace_around_colon():
    s = Sheet()
    s.set("A1", 1)
    s.set("B2", 2)
    s.set("C5", "=SUM(A1 : B2)")
    assert s.get("C5") == 3


def test_r07_function_composes_as_primary():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", 3)
    s.set("C5", "=SUM(A1:A2)+1")
    assert s.get("C5") == 5
    s.set("C6", "=-MAX(A1:A2)*2")
    assert s.get("C6") == -6
    s.set("C7", "=SUM(A1:A2)>3")
    assert s.get("C7") == 1


def test_r07_first_error_in_row_major_order():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "oops")   # visited before A2 (row-major)
    s.set("A2", "=1/0")
    s.set("C5", "=SUM(A1:B2)")
    assert s.get("C5") == "#TYPE!"


def test_r07_formula_members_contribute():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", "=A1+1")
    s.set("C5", "=SUM(A1:A2)")
    assert s.get("C5") == 3


# ---------------------------------------------------------------- R8
def test_r08_sum_skips_empty_and_zero_on_all_empty():
    s = Sheet()
    s.set("A1", 5)
    s.set("C5", "=SUM(A1:A3)")
    assert s.get("C5") == 5
    s.set("C6", "=SUM(D1:D3)")
    assert s.get("C6") == 0


def test_r08_min_max():
    s = Sheet()
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
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", "hi")
    for f, exp in (("SUM", "#TYPE!"), ("MIN", "#TYPE!"), ("MAX", "#TYPE!"),
                   ("COUNT", 2)):
        s.set("C5", f"={f}(A1:A2)")
        assert s.get("C5") == exp


def test_r02_error_looking_string_literal_roundtrip():
    # Non-Goals: "a string literal is always a string … never treated as an
    # error value"; get returns the stored str unchanged.
    s = Sheet()
    for lit in ("#REF!", "#DIV!", "#CYCLE!", "#PARSE!", "#TYPE!"):
        s.set("A1", lit)
        assert s.get("A1") == lit


def test_r06_literal_error_string_is_type_fuel_not_error():
    # A cell holding the *string* "#REF!" is #TYPE! fuel in numeric
    # contexts — referencing it must not propagate it as an error value.
    s = Sheet()
    s.set("A1", "#REF!")
    s.set("B1", "=A1")
    s.set("B2", "=A1+1")
    assert s.get("B1") == "#TYPE!"
    assert s.get("B2") == "#TYPE!"


def test_r08_literal_error_string_in_range():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", "#DIV!")  # string literal, not an error value
    for f, exp in (("SUM", "#TYPE!"), ("MIN", "#TYPE!"), ("MAX", "#TYPE!"),
                   ("COUNT", 2)):
        s.set("C5", f"={f}(A1:A2)")
        assert s.get("C5") == exp


def test_r08_count_structural():
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", "text")
    s.set("A3", "=1/0")   # formula cell counts; never evaluated by COUNT
    s.set("C5", "=COUNT(A1:A4)")
    assert s.get("C5") == 3
    s.set("A1", "=COUNT(A1:A1)")  # self-inclusion is NOT a cycle
    assert s.get("A1") == 1


# ---------------------------------------------------------------- R9
def test_r09_self_reference():
    s = Sheet()
    s.set("A1", "=A1")
    assert s.get("A1") == "#CYCLE!"


def test_r09_mutual_cycle():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    assert s.get("B1") == "#CYCLE!"


def test_r09_cycle_through_range_and_propagation():
    s = Sheet()
    s.set("A1", "=SUM(A1:B1)")
    assert s.get("A1") == "#CYCLE!"
    s.set("C1", "=A1+1")
    assert s.get("C1") == "#CYCLE!"


def test_r09_recovery_after_breaking_cycle():
    s = Sheet()
    s.set("A1", "=B1")
    s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    s.set("B1", 3)
    assert s.get("A1") == 3
    assert s.get("B1") == 3


# ---------------------------------------------------------------- R10
def test_r10_set_never_evaluates():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    assert s.eval_count == 0


def test_r10_counting_and_repeat_read():
    s = Sheet()
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


def test_r10_error_results_cached():
    s = Sheet()
    s.set("A1", "=A1")
    c0 = s.eval_count
    assert s.get("A1") == "#CYCLE!"
    d = s.eval_count - c0
    assert d == 1
    c1 = s.eval_count
    assert s.get("A1") == "#CYCLE!"
    assert s.eval_count == c1
    s.set("B1", "=)")
    c2 = s.eval_count
    s.get("B1"); s.get("B1")
    assert s.eval_count - c2 <= 1  # #PARSE! computed at most once


def test_r10_irrelevant_edit_adds_zero():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("D9", 5)            # outside B1's closure
    assert s.get("B1") == 2
    assert s.eval_count == c0


def test_r10_relevant_edit_bounds():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1")
    s.set("C1", "=B1")
    s.set("E5", "=D5+1")      # unrelated formula, warmed
    s.get("C1"); s.get("E5")
    c0 = s.eval_count
    s.set("A1", 9)
    assert s.get("C1") == 9
    d = s.eval_count - c0
    assert 1 <= d <= 2        # at most formula cells in closure (C1, B1)
    c1 = s.eval_count
    assert s.get("E5") == 1   # untouched dependent chain stayed cached
    assert s.eval_count == c1


def test_r10_set_x_itself_is_relevant():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("B1", "=A1*3")
    assert s.get("B1") == 3
    assert s.eval_count - c0 >= 1


def test_r10_edit_to_literal_adds_zero():
    s = Sheet()
    s.set("B1", "=1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("B1", 5)
    assert s.get("B1") == 5
    assert s.eval_count == c0


def test_r10_noop_set_still_counts_as_edit():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    c0 = s.eval_count
    s.set("A1", 1)            # identical content
    assert s.get("B1") == 2
    assert s.eval_count - c0 >= 1


def test_r10_count_members_not_evaluated():
    s = Sheet()
    s.set("A1", "=1+1")
    s.set("A2", "=2+2")
    s.set("B5", "=COUNT(A1:A3)")
    c0 = s.eval_count
    assert s.get("B5") == 2
    assert s.eval_count - c0 == 1  # B5 only


def test_r10_short_circuit_observable():
    s = Sheet()
    s.set("G1", "=1+1")
    s.set("F1", "=1/0+G1")
    c0 = s.eval_count
    assert s.get("F1") == "#DIV!"
    assert s.eval_count - c0 == 1  # G1 never started
    c1 = s.eval_count
    assert s.get("G1") == 2
    assert s.eval_count - c1 == 1  # proves G1 wasn't computed before


def test_r10_range_short_circuit_observable():
    s = Sheet()
    s.set("A1", "boom")       # first member errors as #TYPE!
    s.set("B1", "=1+1")
    s.set("H5", "=SUM(A1:B1)")
    c0 = s.eval_count
    assert s.get("H5") == "#TYPE!"
    assert s.eval_count - c0 == 1  # B1 never started
    c1 = s.eval_count
    assert s.get("B1") == 2
    assert s.eval_count - c1 == 1


def test_r10_range_member_edit_is_relevant():
    s = Sheet()
    s.set("C5", "=SUM(A1:B2)")
    s.get("C5")
    c0 = s.eval_count
    s.set("B2", 4)            # empty→filled inside the range: in closure
    assert s.get("C5") == 4
    assert s.eval_count - c0 >= 1


# ---------------------------------------------------------------- R11
def _random_ops(seed, n_ops):
    rng = random.Random(seed)
    cols, rows = "ABC", (1, 2, 3, 4)
    region = [f"{c}{r}" for c in cols for r in rows]

    def addr():
        return rng.choice(region)

    def formula():
        kind = rng.randrange(6)
        if kind == 0:
            return f"={addr()}+{rng.randrange(0, 9)}"
        if kind == 1:
            return f"={addr()}*{addr()}"
        if kind == 2:
            a, b = sorted(rng.sample(region, 2))
            return f"={rng.choice(('SUM', 'MIN', 'MAX', 'COUNT'))}({a}:{b})"
        if kind == 3:
            return f"={addr()}/{addr()}"
        if kind == 4:
            return f"={addr()}<{addr()}"
        return f"=({addr()}+{addr()})*2-{addr()}"

    ops = []
    for _ in range(n_ops):
        r = rng.random()
        if r < 0.35:
            ops.append(("set", addr(), rng.randrange(-5, 10)))
        elif r < 0.45:
            ops.append(("set", addr(), rng.choice(("hi", "x", ""))))
        elif r < 0.75:
            ops.append(("set", addr(), formula()))
        else:
            ops.append(("get", addr()))
    return region, ops


@pytest.mark.parametrize("seed", range(40))
def test_r11_differential_vs_naive_reference(seed):
    arm, ref = Sheet(), RefSheet()
    region, ops = _random_ops(seed, 60)
    for op in ops:
        if op[0] == "set":
            arm.set(op[1], op[2])
            ref.set(op[1], op[2])
        else:
            assert arm.get(op[1]) == ref.get(op[1]), (seed, op)
    for a in region:  # final sweep
        assert arm.get(a) == ref.get(a), (seed, a)


# ---------------------------------------------------------------- R12
def test_r12_nested_parens_depth_32():
    s = Sheet()
    s.set("A1", "=" + "(" * 32 + "1" + ")" * 32)
    assert s.get("A1") == 1


def test_r12_unary_minus_tower():
    n = 509
    s = Sheet()
    s.set("A1", "=" + "-" * n + "1")   # 511 chars incl. '='
    assert s.get("A1") == (1 if n % 2 == 0 else -1)


def test_r12_reference_chain_256():
    s = Sheet()
    addrs = [f"{c}{r}" for r in range(1, 12) for c in "ABCDEFGHIJKLMNOPQRSTUVWX"]
    chain = addrs[:257]
    for i in range(256):
        s.set(chain[i], f"={chain[i + 1]}")
    s.set(chain[256], 7)
    assert s.get(chain[0]) == 7


def test_r12_magnitude_within_bounds():
    s = Sheet()
    s.set("A1", "=1024*1024*1024*1024*1024*1024")  # 2**60
    assert s.get("A1") == 2 ** 60


def test_r12_out_of_bounds_confined():
    s = Sheet()
    big = "=" + "+".join(["1"] * 400)  # ~800 chars: out of bounds
    s.set("Z9", big)                   # set must still succeed
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    assert s.get("B1") == 2            # within-bounds gets keep guarantees
