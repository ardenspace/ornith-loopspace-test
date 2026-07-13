"""Task 2.1: Tokenizer + parser — core grammar (functions excluded)."""
import pytest
from gridcalc.parser import parse


class TestParserCoreGrammar:
    """Tests for parser per R3 and Task 2.1 acceptance criteria."""

    def test_integer_with_leading_zeros(self):
        """INT with leading zeros parses."""
        assert parse("007") == ("INT", 7)

    def test_reference_tokens(self):
        """REF tokens parse (validity is evaluator's job)."""
        assert parse("A1") == ("REF", "A1")
        assert parse("A01") == ("REF", "A01")  # leading zero in REF is parser-level OK

    def test_binary_operators(self):
        """Binary + - * / parse."""
        assert parse("1+2") == ("ADD", ("INT", 1), ("INT", 2))
        assert parse("1-2") == ("SUB", ("INT", 1), ("INT", 2))
        assert parse("1*2") == ("MUL", ("INT", 1), ("INT", 2))
        assert parse("1/2") == ("DIV", ("INT", 1), ("INT", 2))

    def test_stacked_unary_minus(self):
        """Stacked unary minus parses."""
        assert parse("--1") == ("NEG", ("NEG", ("INT", 1)))
        # "2--3" = 2 - (-3) = 5, so AST is SUB(2, NEG(3))
        assert parse("2--3") == ("SUB", ("INT", 2), ("NEG", ("INT", 3)))

    def test_parentheses(self):
        """Parentheses parse."""
        assert parse("(1+2)") == ("ADD", ("INT", 1), ("INT", 2))

    def test_all_six_comparisons(self):
        """All six comparisons parse."""
        assert parse("1<2") == ("LT", ("INT", 1), ("INT", 2))
        assert parse("1<=2") == ("LTE", ("INT", 1), ("INT", 2))
        assert parse("1>2") == ("GT", ("INT", 1), ("INT", 2))
        assert parse("1>=2") == ("GTE", ("INT", 1), ("INT", 2))
        assert parse("1=2") == ("EQ", ("INT", 1), ("INT", 2))
        assert parse("1<>2") == ("NEQ", ("INT", 1), ("INT", 2))

    def test_spaces_and_tabs_between_tokens(self):
        """Spaces and tabs allowed between tokens."""
        assert parse("1 + 2") == ("ADD", ("INT", 1), ("INT", 2))
        assert parse("1\t+\t2") == ("ADD", ("INT", 1), ("INT", 2))

    def test_precedence_multiplication_before_addition(self):
        """'1+2*3' groups * first."""
        result = parse("1+2*3")
        assert result[0] == "ADD"
        assert result[1] == ("INT", 1)
        assert result[2][0] == "MUL"

    def test_precedence_left_associative_comparisons(self):
        """'1<2<3' associates left."""
        result = parse("1<2<3")
        assert result[0] == "LT"
        assert result[1] == ("LT", ("INT", 1), ("INT", 2))
        assert result[2] == ("INT", 3)

    def test_precedence_unary_minus_before_multiplication(self):
        """Unary minus binds tighter than * /."""
        result = parse("-1*2")
        assert result[0] == "MUL"
        assert result[1][0] == "NEG"

    def test_empty_string_parses_to_error(self):
        """Empty formula yields #PARSE!."""
        with pytest.raises(Exception):
            parse("")

    def test_split_two_char_operator(self):
        """'1 < = 2' (split two-char operator) yields #PARSE!."""
        with pytest.raises(Exception):
            parse("1 < = 2")

    def test_lowercase_parses_to_error(self):
        """Lowercase identifiers yield #PARSE!."""
        with pytest.raises(Exception):
            parse("a1")

    def test_multi_letter_non_function_parses_to_error(self):
        """Multi-letter non-function names yield #PARSE!."""
        with pytest.raises(Exception):
            parse("AA1")

    def test_unknown_characters_parses_to_error(self):
        """Unknown characters yield #PARSE!."""
        with pytest.raises(Exception):
            parse("1 @ 2")

    def test_unbalanced_parens_parses_to_error(self):
        """Unbalanced parentheses yield #PARSE!."""
        with pytest.raises(Exception):
            parse("(1+2")
        with pytest.raises(Exception):
            parse("1+2)")

    def test_function_call_syntax_not_yet_parsed(self):
        """Uppercase function-call syntax does NOT yield #PARSE! yet (phase 3 adds it)."""
        # This should parse as REF + LPAREN + ... — we just verify it doesn't raise #PARSE!
        # The exact parse tree is phase 3's concern
        try:
            parse("SUM(A1:B2)")
        except Exception as e:
            # If it raises, it should NOT be a #PARSE! error
            assert "PARSE" not in str(e).upper()

    def test_range_syntax_not_yet_parsed(self):
        """Range syntax outside function does NOT yield #PARSE! yet (phase 3 adds it)."""
        try:
            parse("A1:B2")
        except Exception as e:
            assert "PARSE" not in str(e).upper()

    def test_r12_unary_minus_tower(self):
        """~510-deep unary-minus tower within 512 chars parses without raising."""
        formula = "-" * 510 + "1"
        assert len(formula) <= 512
        # Should not raise
        parse(formula)

    def test_r12_nested_parentheses(self):
        """32-deep nested parentheses parse without raising."""
        formula = "(" * 32 + "1" + ")" * 32
        # Should not raise
        parse(formula)
