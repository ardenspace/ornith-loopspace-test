"""Task 2.1: Parser for Phase 2 scalar expressions — R3 Phase 2 slice tests."""
import ast
import os

import pytest

from gridcalc.formula import PARSE_ERROR, parse_formula


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = os.path.join(os.path.dirname(__file__), "..", "gridcalc")


def _source_has_forbidden(path):
    """Return set of forbidden runtime patterns found in source file."""
    bad = set()
    tree = ast.parse(open(path).read(), path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("eval", "exec", "compile", "__import__"):
                bad.add(name)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ("pickle", "importlib"):
                    bad.add(alias.name)
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in ("pickle", "importlib"):
                bad.add(node.module)
    return bad


# ---------------------------------------------------------------------------
# 1. Integer literals
# ---------------------------------------------------------------------------

class TestIntegerLiterals:
    def test_simple_integer(self):
        """A plain integer literal evaluates to its numeric value."""
        assert parse_formula("42") == 42

    def test_zero(self):
        """Zero evaluates to 0."""
        assert parse_formula("0") == 0

    def test_single_digit(self):
        """Single digit 1-9 evaluates correctly."""
        for d in range(10):
            assert parse_formula(str(d)) == d

    def test_leading_zeros_allowed(self):
        """Leading zeros are allowed and evaluated by numeric value."""
        assert parse_formula("007") == 7
        assert parse_formula("0000") == 0
        assert parse_formula("00123") == 123
        assert parse_formula("0000000001") == 1

    def test_large_integer(self):
        """Larger integers evaluate correctly."""
        assert parse_formula("123456789") == 123456789
        assert parse_formula("99999999") == 99999999

    def test_integer_with_surrounding_spaces(self):
        """Spaces around an integer literal are allowed."""
        assert parse_formula("  42  ") == 42
        assert parse_formula("\t42\t") == 42


# ---------------------------------------------------------------------------
# 2. Comparisons — left-associative, yield integers 1/0
# ---------------------------------------------------------------------------

class TestComparisons:
    def test_equal_true(self):
        """1=1 evaluates to 1."""
        assert parse_formula("1=1") == 1

    def test_equal_false(self):
        """1=2 evaluates to 0."""
        assert parse_formula("1=2") == 0

    def test_not_equal_true(self):
        """1<>2 evaluates to 1."""
        assert parse_formula("1<>2") == 1

    def test_not_equal_false(self):
        """1<>1 evaluates to 0."""
        assert parse_formula("1<>1") == 0

    def test_less_than_true(self):
        """1<2 evaluates to 1."""
        assert parse_formula("1<2") == 1

    def test_less_than_false(self):
        """2<1 evaluates to 0."""
        assert parse_formula("2<1") == 0

    def test_less_than_or_equal_true(self):
        """1<=1 and 1<=2 both evaluate to 1."""
        assert parse_formula("1<=1") == 1
        assert parse_formula("1<=2") == 1

    def test_less_than_or_equal_false(self):
        """2<=1 evaluates to 0."""
        assert parse_formula("2<=1") == 0

    def test_greater_than_true(self):
        """2>1 evaluates to 1."""
        assert parse_formula("2>1") == 1

    def test_greater_than_false(self):
        """1>2 evaluates to 0."""
        assert parse_formula("1>2") == 0

    def test_greater_than_or_equal_true(self):
        """2>=2 and 2>=1 both evaluate to 1."""
        assert parse_formula("2>=2") == 1
        assert parse_formula("2>=1") == 1

    def test_greater_than_or_equal_false(self):
        """1>=2 evaluates to 0."""
        assert parse_formula("1>=2") == 0

    def test_comparison_with_spaces(self):
        """Spaces around comparison operators are allowed."""
        assert parse_formula("1 = 1") == 1
        assert parse_formula("1  =  1") == 1
        assert parse_formula("1 <> 2") == 1
        assert parse_formula("1 <= 2") == 1

    def test_comparison_with_tabs(self):
        """Tabs around comparison operators are allowed."""
        assert parse_formula("1\t=\t1") == 1
        assert parse_formula("1\t<>\t2") == 1

    def test_left_associative_chained_equal(self):
        """Chained = are left-associative: 1=1=1 → (1=1)=1 → 1."""
        assert parse_formula("1=1=1") == 1

    def test_left_associative_chained_equal_false(self):
        """Chained = are left-associative: 1=2=1 → (1=2)=1 → 0=1 → 0."""
        assert parse_formula("1=2=1") == 0

    def test_left_associative_mixed_comparisons(self):
        """Mixed comparisons are left-associative: 5>3>1 → (5>3)>1 → 1>1 → 0."""
        assert parse_formula("5>3>1") == 0

    def test_left_associative_gt_lt(self):
        """5>3<10 → (5>3)<10 → 1<10 → 1."""
        assert parse_formula("5>3<10") == 1

    def test_comparison_with_large_numbers(self):
        """Comparisons work with multi-digit numbers."""
        assert parse_formula("100>=99") == 1
        assert parse_formula("50<=49") == 0
        assert parse_formula("10<>10") == 0


# ---------------------------------------------------------------------------
# 3. Additive operators (+ and -)
# ---------------------------------------------------------------------------

class TestAdditive:
    def test_addition(self):
        """1+2 evaluates to 3."""
        assert parse_formula("1+2") == 3

    def test_subtraction(self):
        """5-3 evaluates to 2."""
        assert parse_formula("5-3") == 2

    def test_addition_with_spaces(self):
        """Spaces around + are allowed."""
        assert parse_formula("1 + 2") == 3

    def test_subtraction_with_spaces(self):
        """Spaces around - are allowed."""
        assert parse_formula("5 - 3") == 2

    def test_chained_addition(self):
        """1+2+3 evaluates left-to-right: (1+2)+3 = 6."""
        assert parse_formula("1+2+3") == 6

    def test_chained_subtraction(self):
        """10-3-2 evaluates left-to-right: (10-3)-2 = 5."""
        assert parse_formula("10-3-2") == 5

    def test_mixed_add_sub(self):
        """10-3+2 evaluates left-to-right: (10-3)+2 = 9."""
        assert parse_formula("10-3+2") == 9

    def test_addition_with_tabs(self):
        """Tabs around + are allowed."""
        assert parse_formula("1\t+\t2") == 3


# ---------------------------------------------------------------------------
# 4. Multiplicative operators (* and /)
# ---------------------------------------------------------------------------

class TestMultiplicative:
    def test_multiplication(self):
        """3*4 evaluates to 12."""
        assert parse_formula("3*4") == 12

    def test_division(self):
        """10/2 evaluates to 5."""
        assert parse_formula("10/2") == 5

    def test_multiplication_with_spaces(self):
        """Spaces around * are allowed."""
        assert parse_formula("3 * 4") == 12

    def test_division_with_spaces(self):
        """Spaces around / are allowed."""
        assert parse_formula("10 / 2") == 5

    def test_chained_multiplication(self):
        """2*3*4 evaluates left-to-right: (2*3)*4 = 24."""
        assert parse_formula("2*3*4") == 24

    def test_chained_division(self):
        """24/4/2 evaluates left-to-right: (24/4)/2 = 3."""
        assert parse_formula("24/4/2") == 3

    def test_multiplication_with_tabs(self):
        """Tabs around * are allowed."""
        assert parse_formula("3\t*\t4") == 12


# ---------------------------------------------------------------------------
# 5. Operator precedence (additive vs multiplicative)
# ---------------------------------------------------------------------------

class TestOperatorPrecedence:
    def test_mul_before_add(self):
        """2+3*4 evaluates to 2+(3*4) = 14, not (2+3)*4 = 20."""
        assert parse_formula("2+3*4") == 14

    def test_div_before_sub(self):
        """10-12/3 evaluates to 10-(12/3) = 6."""
        assert parse_formula("10-12/3") == 6

    def test_mul_div_same_precedence_left_assoc(self):
        """12/3*4 evaluates left-to-right: (12/3)*4 = 16."""
        assert parse_formula("12/3*4") == 16

    def test_add_sub_same_precedence_left_assoc(self):
        """10-3+2 evaluates left-to-right: (10-3)+2 = 9."""
        assert parse_formula("10-3+2") == 9

    def test_complex_expression(self):
        """2+3*4-1 evaluates to 2+(3*4)-1 = 13."""
        assert parse_formula("2+3*4-1") == 13


# ---------------------------------------------------------------------------
# 6. Unary minus
# ---------------------------------------------------------------------------

class TestUnaryMinus:
    def test_unary_minus_simple(self):
        """-5 evaluates to -5."""
        assert parse_formula("-5") == -5

    def test_unary_minus_with_addition(self):
        """1+-2 evaluates to -1."""
        assert parse_formula("1+-2") == -1

    def test_unary_minus_with_subtraction(self):
        """1--2 evaluates to 3."""
        assert parse_formula("1--2") == 3

    def test_unary_minus_with_multiplication(self):
        """-3*4 evaluates to -12."""
        assert parse_formula("-3*4") == -12

    def test_double_unary_minus(self):
        """--5 evaluates to 5."""
        assert parse_formula("--5") == 5

    def test_triple_unary_minus(self):
        """---5 evaluates to -5."""
        assert parse_formula("---5") == -5

    def test_unary_minus_with_spaces(self):
        """Spaces between - and operand are not allowed (grammar: factor := - factor)."""
        # "- 5" has a space between - and 5, which means after - we expect a factor
        # but the next token is INT 5 with a space before it. Actually spaces are
        # skipped between tokens, so "- 5" should parse as unary minus applied to 5.
        assert parse_formula("- 5") == -5


# ---------------------------------------------------------------------------
# 7. Parentheses
# ---------------------------------------------------------------------------

class TestParentheses:
    def test_simple_parens(self):
        """(1+2) evaluates to 3."""
        assert parse_formula("(1+2)") == 3

    def test_parens_override_precedence(self):
        """(2+3)*4 evaluates to 5*4 = 20, not 2+3*4 = 14."""
        assert parse_formula("(2+3)*4") == 20

    def test_nested_parens(self):
        """((1+2)*3) evaluates to 9."""
        assert parse_formula("((1+2)*3)") == 9

    def test_parens_with_comparison(self):
        """(1+2)=(3+0) evaluates to 1."""
        assert parse_formula("(1+2)=(3+0)") == 1

    def test_parens_with_spaces(self):
        """Spaces inside parens are allowed."""
        assert parse_formula("( 1 + 2 )") == 3

    def test_empty_parens_invalid(self):
        """() is not a valid expression."""
        assert parse_formula("()") == PARSE_ERROR


# ---------------------------------------------------------------------------
# 8. Single-cell references (REF shape: one uppercase A-Z + one or more digits)
# ---------------------------------------------------------------------------

class TestReferences:
    def test_valid_reference_a1(self):
        """A1 is a valid reference and parses successfully."""
        # References are recognized as valid primaries; evaluation returns 0
        # as a placeholder (future tasks wire up actual cell values).
        assert parse_formula("A1") == 0

    def test_valid_reference_z99(self):
        """Z99 is a valid reference."""
        assert parse_formula("Z99") == 0

    def test_reference_in_expression(self):
        """A1+B1 parses successfully (both are valid references)."""
        assert parse_formula("A1+B1") == 0

    def test_reference_with_comparison(self):
        """A1>B1 parses successfully."""
        assert parse_formula("A1>B1") == 0

    def test_reference_with_spaces(self):
        """Spaces around references are allowed."""
        assert parse_formula(" A1 ") == 0


# ---------------------------------------------------------------------------
# 9. Malformed formula text → #PARSE!
# ---------------------------------------------------------------------------

class TestMalformed:
    def test_empty_formula(self):
        """Empty formula text returns #PARSE!."""
        assert parse_formula("") == PARSE_ERROR

    def test_only_spaces(self):
        """Formula with only spaces returns #PARSE!."""
        assert parse_formula("   ") == PARSE_ERROR
        assert parse_formula("\t\t") == PARSE_ERROR
        assert parse_formula(" \t ") == PARSE_ERROR

    def test_lowercase_identifier(self):
        """Lowercase identifiers like a1 return #PARSE!."""
        assert parse_formula("a1") == PARSE_ERROR
        assert parse_formula("z99") == PARSE_ERROR
        assert parse_formula("abc") == PARSE_ERROR

    def test_mixed_case_identifier(self):
        """Mixed-case identifiers like A1b return #PARSE!."""
        assert parse_formula("A1b") == PARSE_ERROR
        assert parse_formula("a1B") == PARSE_ERROR
        assert parse_formula("AB1c") == PARSE_ERROR

    def test_invalid_whitespace_in_less_than_or_equal(self):
        """< = (space between < and =) returns #PARSE!."""
        assert parse_formula("< =") == PARSE_ERROR

    def test_invalid_whitespace_in_greater_than_or_equal(self):
        """> = (space between > and =) returns #PARSE!."""
        assert parse_formula("> =") == PARSE_ERROR

    def test_invalid_whitespace_in_not_equal(self):
        """< > (space between < and >) returns #PARSE!."""
        assert parse_formula("< >") == PARSE_ERROR

    def test_invalid_identifier_two_letters(self):
        """AB1 (two uppercase letters before digits) is a NAME token -> #NAME!."""
        from gridcalc.formula import NAME_ERROR
        assert parse_formula("AB1") == NAME_ERROR
        assert parse_formula("ZA99") == NAME_ERROR

    def test_invalid_identifier_digit_first(self):
        """1A (digit before letter) returns #PARSE!."""
        assert parse_formula("1A") == PARSE_ERROR

    def test_invalid_character(self):
        """Invalid characters like !, @, # return #PARSE!."""
        assert parse_formula("1!") == PARSE_ERROR
        assert parse_formula("@") == PARSE_ERROR
        assert parse_formula("#") == PARSE_ERROR

    def test_orphan_open_paren(self):
        """Unmatched open paren returns #PARSE!."""
        assert parse_formula("(1+2") == PARSE_ERROR

    def test_orphan_close_paren(self):
        """Unmatched close paren returns #PARSE!."""
        assert parse_formula("1+2)") == PARSE_ERROR

    def test_double_operator(self):
        """Double operators like ++ are not valid in this grammar."""
        # ++ is not in the grammar; after + we expect a term/factor/primary
        # but + is not a valid primary, so it should fail.
        assert parse_formula("1++2") == PARSE_ERROR

    def test_operator_at_end(self):
        """Trailing operator returns #PARSE!."""
        assert parse_formula("1+") == PARSE_ERROR
        assert parse_formula("1*") == PARSE_ERROR

    def test_operator_at_start_non_unary(self):
        """Leading * or / (not unary minus) returns #PARSE!."""
        assert parse_formula("*1") == PARSE_ERROR
        assert parse_formula("/1") == PARSE_ERROR

    def test_only_operator(self):
        """A single operator is not a valid expression."""
        assert parse_formula("+") == PARSE_ERROR
        assert parse_formula("*") == PARSE_ERROR

    def test_newline_rejected(self):
        """Newlines in formula text are invalid."""
        assert parse_formula("1\n2") == PARSE_ERROR
        assert parse_formula("1+2\n") == PARSE_ERROR


# ---------------------------------------------------------------------------
# 10. Combined expressions
# ---------------------------------------------------------------------------

class TestCombinedExpressions:
    def test_arithmetic_with_comparison(self):
        """1+2=3 evaluates to 1 (comparison of arithmetic results)."""
        assert parse_formula("1+2=3") == 1

    def test_arithmetic_with_comparison_false(self):
        """1+2=4 evaluates to 0."""
        assert parse_formula("1+2=4") == 0

    def test_parens_with_arithmetic_and_comparison(self):
        """(1+2)*(3+4) > 20 evaluates to 0 (21 > 20 is 1, wait: 21>20=1)."""
        assert parse_formula("(1+2)*(3+4) > 20") == 1

    def test_complex_expression(self):
        """2+3*4-1=13 evaluates to 1."""
        assert parse_formula("2+3*4-1=13") == 1

    def test_unary_minus_in_comparison(self):
        """-1 < 0 evaluates to 1."""
        assert parse_formula("-1 < 0") == 1

    def test_nested_parens_with_arithmetic(self):
        """((2+3)*(4-1)) evaluates to 15."""
        assert parse_formula("((2+3)*(4-1))") == 15


# ---------------------------------------------------------------------------
# 11. Security: no forbidden runtime patterns
# ---------------------------------------------------------------------------

class TestSecurityNoForbiddenPatterns:
    def test_no_forbidden_patterns_in_formula(self):
        """formula.py must not contain eval/exec/compile/__import__/importlib/pickle."""
        src = os.path.join(_PACKAGE_ROOT, "formula.py")
        bad = _source_has_forbidden(src)
        assert bad == set(), f"Forbidden patterns in formula.py: {bad}"


# ---------------------------------------------------------------------------
# 12. Division semantics (R4 integer truncation toward zero + #DIV!)
# ---------------------------------------------------------------------------

class TestDivisionSemantics:
    def test_integer_division_truncates_toward_zero(self):
        """7/2 evaluates to 3 (integer truncation toward zero), not 3.5."""
        assert parse_formula("7/2") == 3

    def test_integer_division_negative_truncates_toward_zero(self):
        """-7/2 evaluates to -3 (truncation toward zero), not -4."""
        assert parse_formula("-7/2") == -3

    def test_integer_division_exact(self):
        """10/2 evaluates to 5 (exact division)."""
        assert parse_formula("10/2") == 5

    def test_division_by_zero_returns_div_error(self):
        """1/0 evaluates to #DIV!, not #PARSE!."""
        from gridcalc.formula import DIV_ERROR
        assert parse_formula("1/0") == DIV_ERROR

    def test_division_by_zero_complex_expr(self):
        """(1+2)/(3-3) evaluates to #DIV!."""
        from gridcalc.formula import DIV_ERROR
        assert parse_formula("(1+2)/(3-3)") == DIV_ERROR

    def test_division_by_zero_propagates_through_addition(self):
        """1/0+2 propagates #DIV! rather than returning #PARSE!."""
        from gridcalc.formula import DIV_ERROR
        assert parse_formula("1/0+2") == DIV_ERROR

    def test_division_by_zero_propagates_through_multiplication(self):
        """3*(1/0) propagates #DIV! rather than returning #PARSE!."""
        from gridcalc.formula import DIV_ERROR
        assert parse_formula("3*(1/0)") == DIV_ERROR

    def test_division_by_zero_propagates_through_comparison(self):
        """1/0=1 propagates #DIV! rather than returning #PARSE!."""
        from gridcalc.formula import DIV_ERROR
        assert parse_formula("1/0=1") == DIV_ERROR


# ---------------------------------------------------------------------------
# 13. Workbook integration: formula cells evaluate via get()
# ---------------------------------------------------------------------------

class TestWorkbookFormulaIntegration:
    def test_set_formula_and_get_result(self):
        """Setting a cell to '=1+2' and getting it back yields 3."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=1+2")
        assert wb.sheet("S1").get("A1") == 3

    def test_set_formula_and_get_arithmetic(self):
        """Setting a cell to '=3*4' and getting it back yields 12."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=3*4")
        assert wb.sheet("S1").get("A1") == 12

    def test_set_formula_and_get_comparison(self):
        """Setting a cell to '=1=1' and getting it back yields 1."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=1=1")
        assert wb.sheet("S1").get("A1") == 1

    def test_set_formula_and_get_negative(self):
        """Setting a cell to '=-5' and getting it back yields -5."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=-5")
        assert wb.sheet("S1").get("A1") == -5

    def test_set_formula_and_get_parens(self):
        """Setting a cell to '=(2+3)*4' and getting it back yields 20."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=(2+3)*4")
        assert wb.sheet("S1").get("A1") == 20

    def test_set_formula_malformed_returns_parse_error(self):
        """Setting a malformed formula cell returns #PARSE! from get()."""
        from gridcalc.workbook import Workbook
        from gridcalc.formula import PARSE_ERROR
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "=1+")
        assert wb.sheet("S1").get("A1") == PARSE_ERROR

    def test_set_plain_string_returns_as_is(self):
        """A plain string (no leading '=') is returned unchanged."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", "hello")
        assert wb.sheet("S1").get("A1") == "hello"

    def test_set_plain_int_returns_as_is(self):
        """A plain int is returned unchanged."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S1")
        sh.set("A1", 42)
        assert wb.sheet("S1").get("A1") == 42


# ---------------------------------------------------------------------------
# 14. Single-quoted strings are not in Phase 2 grammar → #PARSE!
# ---------------------------------------------------------------------------

class TestSingleQuotedStringsRejected:
    def test_single_quoted_string_returns_parse_error(self):
        """'x' is not in the Phase 2 grammar → #PARSE! (R3, R13 double-quote only)."""
        assert parse_formula("'x'") == PARSE_ERROR

    def test_single_quoted_string_in_expression(self):
        """'a'+'b' is not in the Phase 2 grammar → #PARSE!."""
        assert parse_formula("'a'+'b'") == PARSE_ERROR

    def test_single_quoted_string_in_comparison(self):
        """'a'='b' is not in the Phase 2 grammar → #PARSE!."""
        assert parse_formula("'a'='b'") == PARSE_ERROR

    def test_unterminated_single_quote(self):
        """Unterminated single quote → #PARSE!."""
        assert parse_formula("'abc") == PARSE_ERROR
