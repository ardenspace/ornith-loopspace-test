"""Phase 2 Task 2.1: Parser tests — core grammar (functions excluded)."""
import pytest
from gridcalc.parser import parse, PARSE_ERROR, IntLit, Ref, BinOp, UnaryMinus


# ── basic INT ────────────────────────────────────────────────────────

def test_int_literal():
    assert isinstance(parse("42"), IntLit)
    assert parse("42").value == 42


def test_int_leading_zeros():
    node = parse("007")
    assert isinstance(node, IntLit)
    assert node.value == 7


# ── REF tokens ───────────────────────────────────────────────────────

def test_ref_token():
    node = parse("A1")
    assert isinstance(node, Ref)
    assert node.addr == "A1"


def test_ref_token_large():
    node = parse("Z99")
    assert isinstance(node, Ref)
    assert node.addr == "Z99"


# ── binary operators ─────────────────────────────────────────────────

def test_addition():
    node = parse("1+2")
    assert isinstance(node, BinOp)
    assert node.op == "+"


def test_subtraction():
    node = parse("5-3")
    assert isinstance(node, BinOp)
    assert node.op == "-"


def test_multiplication():
    node = parse("2*3")
    assert isinstance(node, BinOp)
    assert node.op == "*"


def test_division():
    node = parse("6/2")
    assert isinstance(node, BinOp)
    assert node.op == "/"


# ── unary minus ──────────────────────────────────────────────────────

def test_unary_minus():
    node = parse("-1")
    assert isinstance(node, UnaryMinus)


def test_double_unary_minus():
    node = parse("--1")
    assert isinstance(node, UnaryMinus)
    assert isinstance(node.operand, UnaryMinus)


def test_double_minus_expression():
    """=2--3 should parse as 2 - (-3)."""
    node = parse("2--3")
    assert isinstance(node, BinOp)
    assert node.op == "-"
    assert isinstance(node.right, UnaryMinus)


# ── parentheses ──────────────────────────────────────────────────────

def test_parens():
    node = parse("(1+2)*3")
    assert isinstance(node, BinOp)
    assert node.op == "*"


def test_nested_parens():
    node = parse("((1))")
    assert isinstance(node, IntLit)
    assert node.value == 1


# ── comparisons ──────────────────────────────────────────────────────

@pytest.mark.parametrize("op,expected", [
    ("=", "EQ"), ("<", "LT"), (">", "GT"),
    ("<=", "LE"), (">=", "GE"), ("<>", "NE"),
])
def test_comparison_operators(op, expected):
    node = parse(f"1{op}2")
    assert isinstance(node, BinOp)
    op_map = {"EQ": "=", "LT": "<", "GT": ">", "LE": "<=", "GE": ">=", "NE": "<>"}
    assert node.op == op_map[expected]


def test_left_associative_comparison():
    """1<2<3 should be (1<2)<3."""
    node = parse("1<2<3")
    assert isinstance(node, BinOp)
    assert node.op == "<"
    assert isinstance(node.left, BinOp)
    assert node.left.op == "<"


# ── precedence ───────────────────────────────────────────────────────

def test_mul_before_add():
    """1+2*3 should group * first."""
    node = parse("1+2*3")
    assert isinstance(node, BinOp)
    assert node.op == "+"
    assert isinstance(node.right, BinOp)
    assert node.right.op == "*"


def test_unary_minus_before_mul():
    """-2*3 should be (-2)*3."""
    node = parse("-2*3")
    assert isinstance(node, BinOp)
    assert node.op == "*"
    assert isinstance(node.left, UnaryMinus)


# ── whitespace ───────────────────────────────────────────────────────

def test_spaces_between_tokens():
    node = parse("1 + 2")
    assert isinstance(node, BinOp)


def test_tabs_between_tokens():
    node = parse("1\t+\t2")
    assert isinstance(node, BinOp)


def test_spaces_around_comparison():
    node = parse("1 < 2")
    assert isinstance(node, BinOp)


# ── #PARSE! cases ────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    "",
    "1 < = 2",     # split two-char operator
    "a1",          # lowercase
    "AA1",         # two letters
    "sum(A1:B2)",  # lowercase function (stays invalid in final grammar)
    "1 +",         # trailing operator
    "+1",          # leading binary + (ambiguous — but spec says factor := -factor | primary, so leading + is not in grammar)
    "()",          # empty parens
    "(1",          # unbalanced
    "1)",          # unbalanced
    "1 + * 2",     # double operator
    "@",           # unknown char
    "$",           # unknown char
])
def test_parse_error_inputs(bad):
    result = parse(bad)
    assert result is PARSE_ERROR, f"Expected #PARSE! for {bad!r}, got {result!r}"


# ── R12 sizing ───────────────────────────────────────────────────────

def test_deep_unary_minus_tower():
    """~510-deep unary minus within 512 chars."""
    formula = "-" * 510 + "1"
    assert len(formula) <= 512
    result = parse(formula)
    assert result is not PARSE_ERROR


def test_32_deep_parens():
    """32-deep nested parentheses."""
    formula = "(" * 32 + "1" + ")" * 32
    result = parse(formula)
    assert result is not PARSE_ERROR


# ── function-call syntax is #PARSE! at phase 2 boundary ──────────────
# (Phase 3 adds them; phase 2 tests must NOT assert #PARSE! for these
#  since they'll become valid later. We just verify they don't crash.)

def test_sum_syntax_not_crashing():
    """SUM(A1:B2) should not crash parser at phase 2 — it's reserved for phase 3."""
    # At phase 2, function calls aren't in the grammar, so this should be #PARSE!
    # But we don't assert it — phase 3 will change this behavior.
    result = parse("SUM(A1:B2)")
    # Could be PARSE_ERROR or something else; just don't crash.
