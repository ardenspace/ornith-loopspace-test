import pytest
from gridcalc.parser import parse


class TestBasicParsing:
    def test_integer(self):
        assert parse("42") == ("INT", 42)

    def test_integer_with_leading_zeros(self):
        assert parse("007") == ("INT", 7)

    def test_reference(self):
        assert parse("A1") == ("REF", "A1")

    def test_reference_with_leading_zeros(self):
        assert parse("A01") == ("REF", "A01")

    def test_empty_string(self):
        assert parse("") == "#PARSE!"

    def test_whitespace_only(self):
        assert parse("   ") == "#PARSE!"


class TestArithmetic:
    def test_addition(self):
        result = parse("1+2")
        assert result[0] == "ADD"
        assert result[1] == ("INT", 1)
        assert result[2] == ("INT", 2)

    def test_subtraction(self):
        result = parse("5-3")
        assert result[0] == "SUB"
        assert result[1] == ("INT", 5)
        assert result[2] == ("INT", 3)

    def test_multiplication(self):
        result = parse("2*3")
        assert result[0] == "MUL"
        assert result[1] == ("INT", 2)
        assert result[2] == ("INT", 3)

    def test_division(self):
        result = parse("6/2")
        assert result[0] == "DIV"
        assert result[1] == ("INT", 6)
        assert result[2] == ("INT", 2)

    def test_precedence_multiplication_before_addition(self):
        result = parse("1+2*3")
        assert result[0] == "ADD"
        assert result[1] == ("INT", 1)
        assert result[2][0] == "MUL"

    def test_parentheses(self):
        result = parse("(1+2)*3")
        assert result[0] == "MUL"
        assert result[1][0] == "ADD"

    def test_unary_minus(self):
        result = parse("-5")
        assert result[0] == "NEG"
        assert result[1] == ("INT", 5)

    def test_double_unary_minus(self):
        result = parse("--1")
        assert result[0] == "NEG"
        assert result[1][0] == "NEG"


class TestComparisons:
    def test_equal(self):
        result = parse("1=1")
        assert result[0] == "EQ"

    def test_not_equal(self):
        result = parse("1<>2")
        assert result[0] == "NEQ"

    def test_less_than(self):
        result = parse("1<2")
        assert result[0] == "LT"

    def test_less_equal(self):
        result = parse("1<=2")
        assert result[0] == "LTE"

    def test_greater_than(self):
        result = parse("2>1")
        assert result[0] == "GT"

    def test_greater_equal(self):
        result = parse("2>=1")
        assert result[0] == "GTE"

    def test_left_associative_comparisons(self):
        result = parse("1<2<3")
        assert result[0] == "LT"
        assert result[1][0] == "LT"


class TestWhitespace:
    def test_spaces_between_tokens(self):
        result = parse("1 + 2")
        assert result[0] == "ADD"

    def test_tabs_between_tokens(self):
        result = parse("1\t+\t2")
        assert result[0] == "ADD"

    def test_split_two_char_operator(self):
        assert parse("1 < = 2") == "#PARSE!"


class TestErrorCases:
    def test_lowercase(self):
        assert parse("a1") == "#PARSE!"

    def test_unknown_identifier(self):
        assert parse("AA1") == "#PARSE!"

    def test_unbalanced_parens_open(self):
        assert parse("(1+2") == "#PARSE!"

    def test_unbalanced_parens_close(self):
        assert parse("1+2)") == "#PARSE!"

    def test_unknown_character(self):
        assert parse("1+@") == "#PARSE!"

    def test_unknown_function_name(self):
        assert parse("AVG(A1:A2)") == "#PARSE!"

    def test_lowercase_function(self):
        assert parse("sum(A1:B2)") == "#PARSE!"

    def test_range_not_yet_supported(self):
        assert parse("A1:B2") == "#PARSE!"


class TestR12Sizing:
    def test_deep_unary_minus(self):
        formula = "-" * 510 + "1"
        result = parse(formula)
        assert result != "#PARSE!"

    def test_deep_parentheses(self):
        formula = "(" * 32 + "1" + ")" * 32
        result = parse(formula)
        assert result != "#PARSE!"
