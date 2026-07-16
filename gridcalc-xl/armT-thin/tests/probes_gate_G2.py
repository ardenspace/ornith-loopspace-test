"""Gate G2 probes — derived fresh from the spec (R3, R4, R5, R6) this round.

Scenarios (input -> exact expected output, R-id cited):
  S1  R3: closed scalar grammar — INT/leading zeros, stacked unary minus,
      precedence, parentheses, left-associativity (additive, term,
      comparisons), whitespace rules, and closed-grammar #PARSE! rejections.
  S2  R3 (XL identifier-classification note): multi-letter uppercase
      identifiers are NAME tokens -> #NAME! when undefined; single letter
      and 33+ char identifiers are neither shape -> #PARSE!; lowercase and
      mixed-case identifiers -> #PARSE!.  (Re-probe of prior round's finding,
      re-derived fresh.)
  S3  R4: truncating-toward-zero division; division by zero -> #DIV!.
  S4  R5 (+R6 propagation): first error in textual left-to-right operand
      order is the result; referenced formula cells contribute their result.
  S5  R6: typed reference reads — int cell -> int, string-literal cell ->
      str, formula cell -> its result, empty cell -> 0; REF tokens with
      leading zeros or out-of-range rows parse but denote no cell -> #REF!.
  S6  Cross-cutting G1 x G2 (G1 passed per ledger): R2 replacement re-read
      through a formula, failed-set atomicity observed through evaluation,
      int/str subclass normalization feeding evaluation, and the R1 API
      address boundary vs R3 formula identifier classification.
"""

import pytest

from gridcalc import Workbook


def fresh():
    wb = Workbook()
    return wb, wb.add_sheet("S1")


# ---------------------------------------------------------------- S1: R3


SCALAR_CASES = [
    ("=007", 7),
    ("=0", 0),
    ("=--1", 1),
    ("=----5", 5),
    ("=2--3", 5),
    ("=-2*3", -6),
    ("=2*-3", -6),
    ("=2+3*4", 14),
    ("=(2+3)*4", 20),
    ("=10-3-4", 3),
    ("=100/10/5", 2),
    ("=1<2<3", 1),
    ("=3>2>2", 0),
    ("=1<=2", 1),
    ("=2>=3", 0),
    ("=1<>2", 1),
    ("=1<>1", 0),
    ("=1=1", 1),
    ("=-1<1", 1),
    ("= 1 + 2", 3),
    ("=\t1\t<=\t2", 1),
    ("= ( 1 + 2 ) * 3", 9),
]


@pytest.mark.parametrize("formula,expected", SCALAR_CASES)
def test_r3_scalar_grammar(formula, expected):
    _, s = fresh()
    s.set("H8", formula)
    assert s.get("H8") == expected


PARSE_CASES = [
    "=",            # empty formula (R3, explicit)
    "=1 < = 2",     # two-char operator with interior whitespace (R3, explicit)
    "=1 > = 2",
    "=1 < > 2",
    "=1++2",        # no unary plus in the grammar
    "=+1",
    "=(1",          # unbalanced paren
    "=1)",          # trailing unconsumed token
    "=1 2",         # two primaries, no operator
    "=1/",          # dangling operator
    "=A1:B2",       # range outside RANGE-ARG position (R3, explicit)
    "=SUM",         # function name not followed by ( (R3, explicit)
    "=IF",
    "=sum(1)",      # lowercase callee (R3, explicit)
    "=AVG(A1:B2)",  # unknown callee (R3, explicit)
    "=AA1(1)",      # NAME-shaped identifier used as callee (R3, explicit)
    "=foo",         # lowercase identifier (R3 delta note)
    "=Foo",         # mixed-case identifier
    "=F",           # single letter: neither REF nor NAME shape (R3, explicit)
    "=" + "A" * 33, # 33 chars: exceeds NAME's 32-char cap -> neither shape
    "=_",           # 1 char: below NAME's 2-char floor
]


@pytest.mark.parametrize("formula", PARSE_CASES)
def test_r3_closed_grammar_parse_errors(formula):
    _, s = fresh()
    s.set("H8", formula)
    assert s.get("H8") == "#PARSE!"


# ---------------------------------------------------------------- S2: R3 names


NAME_CASES = [
    "=AA1",             # spec's own example
    "=FOO",             # spec's own example
    "=A1B",             # not REF shape (letter then non-digit tail)
    "=_X",              # NAME may start with underscore (R18 shape)
    "=X_1",
    "=SUM1",            # not a function name, NAME shape
    "=" + "A" + "B" * 31,  # exactly 32 chars: still NAME shape
]


@pytest.mark.parametrize("formula", NAME_CASES)
def test_r3_multiletter_identifier_is_name_not_parse(formula):
    _, s = fresh()
    s.set("H8", formula)
    assert s.get("H8") == "#NAME!"


def test_r3_name_error_propagates_through_operators():
    _, s = fresh()
    s.set("H8", "=-FOO")
    assert s.get("H8") == "#NAME!"
    s.set("H7", "=FOO+1")
    assert s.get("H7") == "#NAME!"


# ---------------------------------------------------------------- S3: R4


DIVISION_CASES = [
    ("=7/2", 3),
    ("=-7/2", -3),
    ("=7/-2", -3),
    ("=-7/-2", 3),
    ("=0/5", 0),
    ("=1/0", "#DIV!"),
    ("=0/0", "#DIV!"),
    ("=8/(3-3)", "#DIV!"),
]


@pytest.mark.parametrize("formula,expected", DIVISION_CASES)
def test_r4_truncating_division(formula, expected):
    _, s = fresh()
    s.set("H8", formula)
    assert s.get("H8") == expected


# ---------------------------------------------------------------- S4: R5


def _error_fixture():
    _, s = fresh()
    s.set("B1", "=1/0")  # -> #DIV!
    s.set("C1", "=(")    # -> #PARSE! formula cell
    return s


def test_r5_first_error_in_textual_order_ref_before_div():
    s = _error_fixture()
    s.set("H8", "=A100+B1")  # A100 -> #REF! is textually first
    assert s.get("H8") == "#REF!"


def test_r5_first_error_in_textual_order_div_before_ref():
    s = _error_fixture()
    s.set("H8", "=B1+A100")
    assert s.get("H8") == "#DIV!"


def test_r5_referenced_parse_error_propagates_first():
    s = _error_fixture()
    s.set("H8", "=C1+B1")  # C1's result #PARSE! is textually first (R6)
    assert s.get("H8") == "#PARSE!"


def test_r5_div_before_parse_in_textual_order():
    s = _error_fixture()
    s.set("H8", "=B1*C1+A100")
    assert s.get("H8") == "#DIV!"


def test_r5_name_error_ordering_vs_div():
    s = _error_fixture()
    s.set("H8", "=FOO+B1")
    assert s.get("H8") == "#NAME!"
    s.set("H7", "=B1+FOO")
    assert s.get("H7") == "#DIV!"


# ---------------------------------------------------------------- S5: R6


def test_r6_typed_reads():
    _, s = fresh()
    s.set("A1", 5)          # number cell
    s.set("A2", "hi")       # string-literal cell
    s.set("A3", "=2*3")     # formula cell

    s.set("H8", "=A1")
    assert s.get("H8") == 5
    s.set("H7", "=A1+1")
    assert s.get("H7") == 6

    s.set("H6", "=A2")      # typed read: the str itself (XL delta 1)
    got = s.get("H6")
    assert got == "hi" and type(got) is str

    s.set("H5", "=A3+1")    # formula cell contributes its result
    assert s.get("H5") == 7


def test_r6_empty_cell_reads_as_zero():
    _, s = fresh()
    s.set("H8", "=Z99")
    assert s.get("H8") == 0
    s.set("H7", "=Z99+1")
    assert s.get("H7") == 1


BAD_REF_CASES = ["=A0", "=A01", "=A100", "=A007", "=Z100"]


@pytest.mark.parametrize("formula", BAD_REF_CASES)
def test_r6_out_of_grid_ref_token_is_ref_error(formula):
    _, s = fresh()
    s.set("H8", formula)
    assert s.get("H8") == "#REF!"


# ---------------------------------------------------------------- S6: cross-cutting G1 x G2


def test_crosscut_r2_replacement_reflected_through_formula():
    _, s = fresh()
    s.set("A1", 2)
    s.set("B1", "=A1*10")
    assert s.get("B1") == 20
    s.set("A1", 5)  # R2: set replaces content
    assert s.get("B1") == 50  # R6 reads currently stored value


def test_crosscut_r2_failed_set_leaves_evaluation_unchanged():
    _, s = fresh()
    s.set("A1", 5)
    s.set("B1", "=A1*10")
    assert s.get("B1") == 50
    with pytest.raises(ValueError):
        s.set("A1", True)   # bool raw rejected (R2)
    with pytest.raises(ValueError):
        s.set("A1", 1.5)    # unsupported type (R2)
    assert s.get("B1") == 50  # atomicity observed through evaluation


def test_crosscut_r2_subclass_normalization_feeds_evaluation():
    class MyInt(int):
        pass

    class MyStr(str):
        pass

    _, s = fresh()
    s.set(MyStr("A1"), MyInt(7))
    stored = s.get("A1")
    assert stored == 7 and type(stored) is int  # normalized on storage (R2)
    s.set("B1", MyStr("=A1+1"))  # str-subclass raw stored as formula
    result = s.get(MyStr("B1"))
    assert result == 8 and type(result) is int


def test_crosscut_r1_api_address_boundary_vs_r3_classification():
    _, s = fresh()
    with pytest.raises(ValueError):
        s.get("AA1")        # R1: invalid address argument
    with pytest.raises(ValueError):
        s.set("AA1", 1)
    with pytest.raises(ValueError):
        s.get("A100")
    s.set("H8", "=AA1")     # same text inside a formula is a NAME (R3)
    assert s.get("H8") == "#NAME!"
    s.set("H7", "=A100")    # and a parseable-but-denoting-nothing REF (R6)
    assert s.get("H7") == "#REF!"
    # the failed gets changed nothing (R1): evaluation still works
    assert s.get("H8") == "#NAME!"
