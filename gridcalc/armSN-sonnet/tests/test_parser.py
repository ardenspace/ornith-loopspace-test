import pytest

from gridcalc.parser import parse


def is_perr(node):
    return node == ("perr",)


def test_int_with_leading_zeros():
    assert parse("007") == ("int", 7)


def test_ref_token():
    assert parse("A1") == ("ref", "A1")
    assert parse("A01") == ("ref", "A01")


def test_binary_ops_parse():
    for op in ("+", "-", "*", "/"):
        node = parse(f"1{op}2")
        assert node[0] == "bin" and node[1] == op


def test_stacked_unary_minus():
    assert parse("--1") == ("neg", 2, ("int", 1))
    assert parse("2--3") == ("bin", "-", ("int", 2), ("neg", 1, ("int", 3)))


def test_parentheses():
    node = parse("(1+2)")
    assert node == ("bin", "+", ("int", 1), ("int", 2))


def test_all_six_comparisons():
    for op in ("=", "<>", "<", "<=", ">", ">="):
        node = parse(f"1{op}2")
        assert node == ("bin", op, ("int", 1), ("int", 2))


def test_spaces_and_tabs_between_tokens():
    assert parse("1 + 2") == ("bin", "+", ("int", 1), ("int", 2))
    assert parse("1\t+\t2") == ("bin", "+", ("int", 1), ("int", 2))


def test_precedence_mul_binds_tighter_than_add():
    node = parse("1+2*3")
    assert node == ("bin", "+", ("int", 1), ("bin", "*", ("int", 2), ("int", 3)))


def test_comparison_left_associative():
    node = parse("1<2<3")
    assert node == ("bin", "<", ("bin", "<", ("int", 1), ("int", 2)), ("int", 3))


def test_unary_minus_binds_tighter_than_mul():
    node = parse("-2*3")
    assert node == ("bin", "*", ("neg", 1, ("int", 2)), ("int", 3))


@pytest.mark.parametrize(
    "text",
    ["", "1 < = 2", "a1", "AA1", "sum(A1:B2)", "1&2", "1@2", "(1+2", "1+2)"],
)
def test_parse_error_on_invalid_inputs(text):
    assert is_perr(parse(text))


def test_uppercase_function_call_parses():
    # Range/function semantics are exercised in depth in test_functions.py;
    # this only confirms the grammar accepts the syntax.
    assert not is_perr(parse("SUM(A1:B2)"))


def test_deep_unary_minus_tower_within_bounds():
    text = "-" * 500 + "1"
    assert len(text) <= 512
    node = parse(text)
    assert node == ("neg", 500, ("int", 1))


def test_deeply_nested_parens_within_bounds():
    depth = 32
    text = "(" * depth + "1" + ")" * depth
    node = parse(text)
    assert node == ("int", 1)
