"""Task 2.2: Scalar evaluation — double-quoted strings, refs, errors, ordering.

Covers R4/R5/R6/R13: integer arithmetic with truncation toward zero,
#DIV!, double-quoted STRING primary, references to typed cells, #REF!
for leading-zero/out-of-grid refs, #TYPE! for string arithmetic/orderings,
#NAME! vocabulary, in-band string errors, depth-first left-to-right
short-circuit with eval_count evidence.
"""
import pytest

from gridcalc.formula import (
    PARSE_ERROR, DIV_ERROR, TYPE_ERROR, REF_ERROR, NAME_ERROR,
    parse_formula,
)
from gridcalc.workbook import Workbook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wb_with(cells):
    """Create a workbook with one sheet and set the given cells."""
    wb = Workbook()
    sh = wb.add_sheet("S1")
    for addr, value in cells.items():
        sh.set(addr, value)
    return wb, sh


# ---------------------------------------------------------------------------
# 1. Double-quoted STRING primary (R13)
# ---------------------------------------------------------------------------

class TestStringPrimary:
    def test_empty_string(self):
        '"" evaluates to "".'
        assert parse_formula('""') == ""

    def test_simple_string(self):
        '"hello" evaluates to "hello".'
        assert parse_formula('"hello"') == "hello"

    def test_string_with_spaces(self):
        '"hello world" evaluates to "hello world".'
        assert parse_formula('"hello world"') == "hello world"

    def test_string_with_special_chars(self):
        '"a!@#$%^&*()" evaluates correctly.'
        assert parse_formula('"a!@#$%^&*()"') == "a!@#$%^&*()"

    def test_string_in_addition(self):
        '"x"+1 -> #TYPE!.'
        assert parse_formula('"x"+1') == TYPE_ERROR

    def test_string_in_subtraction(self):
        '"x"-1 -> #TYPE!.'
        assert parse_formula('"x"-1') == TYPE_ERROR

    def test_string_in_multiplication(self):
        '"x"*2 -> #TYPE!.'
        assert parse_formula('"x"*2') == TYPE_ERROR

    def test_string_in_division(self):
        '"x"/2 -> #TYPE!.'
        assert parse_formula('"x"/2') == TYPE_ERROR

    def test_unary_minus_on_string(self):
        '-"x" -> #TYPE!.'
        assert parse_formula('-"x"') == TYPE_ERROR

    def test_string_equal_string_true(self):
        '"x"="x" -> 1.'
        assert parse_formula('"x"="x"') == 1

    def test_string_equal_string_false(self):
        '"x"="y" -> 0.'
        assert parse_formula('"x"="y"') == 0

    def test_string_not_equal_true(self):
        '"x"<>"y" -> 1.'
        assert parse_formula('"x"<>"y"') == 1

    def test_string_not_equal_false(self):
        '"x"<>"x" -> 0.'
        assert parse_formula('"x"<>"x"') == 0

    def test_string_less_than(self):
        '"x" < "y" -> #TYPE! (R13: string orderings not permitted).'
        assert parse_formula('"x" < "y"') == TYPE_ERROR

    def test_string_greater_than(self):
        '"y" > "x" -> #TYPE!.'
        assert parse_formula('"y" > "x"') == TYPE_ERROR

    def test_string_leq(self):
        '"x" <= "y" -> #TYPE!.'
        assert parse_formula('"x" <= "y"') == TYPE_ERROR

    def test_string_geq(self):
        '"y" >= "x" -> #TYPE!.'
        assert parse_formula('"y" >= "x"') == TYPE_ERROR

    def test_mixed_int_string_equal(self):
        '1="x" -> #TYPE!.'
        assert parse_formula('1="x"') == TYPE_ERROR

    def test_mixed_string_int_equal(self):
        '"x"=1 -> #TYPE!.'
        assert parse_formula('"x"=1') == TYPE_ERROR

    def test_mixed_int_string_less_than(self):
        '1 < "x" -> #TYPE!.'
        assert parse_formula('1 < "x"') == TYPE_ERROR

    def test_string_in_parens(self):
        '("hello") evaluates to "hello".'
        assert parse_formula('("hello")') == "hello"


# ---------------------------------------------------------------------------
# 2. References: leading-zero and out-of-grid -> #REF!
# ---------------------------------------------------------------------------

class TestRefErrors:
    def test_leading_zero_ref(self):
        """=A01 -> #REF! (leading zero)."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A01")
        assert sh.get("C1") == REF_ERROR

    def test_zero_row_ref(self):
        """=A0 -> #REF! (row 0)."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A0")
        assert sh.get("C1") == REF_ERROR

    def test_out_of_grid_ref(self):
        """=A100 -> #REF! (beyond 99)."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A100")
        assert sh.get("C1") == REF_ERROR

    def test_empty_ref_is_zero(self):
        """=A1 where A1 is unset -> 0."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A1")
        assert sh.get("C1") == 0

    def test_int_ref(self):
        """A1=5, =A1 -> 5."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=A1")
        assert sh.get("C1") == 5

    def test_string_ref(self):
        """A1="hi", =A1 -> "hi"."""
        wb, sh = _wb_with({"A1": "hi"})
        sh.set("C1", "=A1")
        assert sh.get("C1") == "hi"

    def test_formula_ref(self):
        """A1=1, B1="=A1+1", =B1 -> 2."""
        wb, sh = _wb_with({"A1": 1})
        sh.set("B1", "=A1+1")
        sh.set("C1", "=B1")
        assert sh.get("C1") == 2


# ---------------------------------------------------------------------------
# 3. Error values are in-band strings (no exceptions for within-bounds)
# ---------------------------------------------------------------------------

class TestErrorValues:
    def test_div_error_is_string(self):
        """=1/0 returns the string "#DIV!", not an exception."""
        wb, sh = _wb_with({})
        sh.set("A1", "=1/0")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == "#DIV!"

    def test_type_error_is_string(self):
        """="x"+1 returns the string "#TYPE!", not an exception."""
        wb, sh = _wb_with({})
        sh.set("A1", '="x"+1')
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == TYPE_ERROR

    def test_ref_error_is_string(self):
        """=A01 returns the string "#REF!", not an exception."""
        wb, sh = _wb_with({})
        sh.set("A1", "=A01")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == REF_ERROR

    def test_parse_error_is_string(self):
        """=1+ returns the string "#PARSE!", not an exception."""
        wb, sh = _wb_with({})
        sh.set("A1", "=1+")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == PARSE_ERROR

    def test_cycle_error_is_string(self):
        """=A1+1 where A1="=A1+1" returns "#CYCLE!" as string."""
        wb, sh = _wb_with({})
        sh.set("A1", "=A1+1")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == "#CYCLE!"


# ---------------------------------------------------------------------------
# 4. Division semantics (R4)
# ---------------------------------------------------------------------------

class TestDivisionR4:
    def test_truncation_toward_zero_positive(self):
        """7/2 -> 3."""
        assert parse_formula("7/2") == 3

    def test_truncation_toward_zero_negative(self):
        """-7/2 -> -3 (not -4)."""
        assert parse_formula("-7/2") == -3

    def test_truncation_toward_zero_negative_dividend(self):
        """7/-2 -> -3."""
        assert parse_formula("7/-2") == -3

    def test_truncation_toward_zero_both_negative(self):
        """-7/-2 -> 3."""
        assert parse_formula("-7/-2") == 3

    def test_division_by_zero(self):
        """1/0 -> #DIV!."""
        assert parse_formula("1/0") == DIV_ERROR

    def test_division_via_ref_by_zero(self):
        """A1=0, =1/A1 -> #DIV!."""
        wb, sh = _wb_with({"A1": 0})
        sh.set("B1", "=1/A1")
        assert sh.get("B1") == DIV_ERROR


# ---------------------------------------------------------------------------
# 5. Left-to-right short-circuit with eval_count (R5)
# ---------------------------------------------------------------------------

class TestShortCircuitEvalCount:
    def test_string_left_short_circuits_right(self):
        """="x" < B1 where B1="=1/0" -> #TYPE! and B1 not evaluated."""
        wb, sh = _wb_with({"B1": "=1/0"})
        sh.set("C1", '="x" < B1')
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_div_error_left_short_circuits_right(self):
        """=A1+B1 where A1="=1/0" -> #DIV! and B1 not evaluated."""
        wb, sh = _wb_with({"B1": 999})
        sh.set("A1", "=1/0")
        sh.set("C1", "=A1+B1")
        assert sh.get("C1") == DIV_ERROR
        assert sh.eval_count == 2  # C1 and A1 started; B1 skipped

    def test_ref_error_left_short_circuits_right(self):
        """=A0+B1 where A0 invalid -> #REF! and B1 not evaluated."""
        wb, sh = _wb_with({"B1": 999})
        sh.set("C1", "=A0+B1")
        assert sh.get("C1") == REF_ERROR
        assert sh.eval_count == 1

    def test_type_error_string_left_in_add(self):
        """="x"+B1 where B1="=1/0" -> #TYPE! and B1 not evaluated."""
        wb, sh = _wb_with({"B1": "=1/0"})
        sh.set("C1", '="x"+B1')
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_no_short_circuit_both_valid(self):
        """=A1+B1 where both valid -> eval_count reflects both formula cells."""
        wb, sh = _wb_with({"A1": "=1+0", "B1": "=2+0"})
        sh.set("C1", "=A1+B1")
        assert sh.get("C1") == 3
        assert sh.eval_count == 3  # A1, B1, C1

    def test_string_equal_evaluates_both(self):
        """="x"="y" evaluates both sides (eval_count=1, no right formula cell)."""
        wb, sh = _wb_with({})
        sh.set("C1", '="x"="y"')
        assert sh.get("C1") == 0
        assert sh.eval_count == 1

    def test_string_not_equal_evaluates_both(self):
        """="x"<>"y" evaluates both sides."""
        wb, sh = _wb_with({})
        sh.set("C1", '="x"<>"y"')
        assert sh.get("C1") == 1
        assert sh.eval_count == 1


# ---------------------------------------------------------------------------
# 6. R13: string primary with formula cells containing strings
# ---------------------------------------------------------------------------

class TestR13StringRules:
    def test_string_ref_arithmetic(self):
        """A1="hi", =A1+1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hi"})
        sh.set("B1", "=A1+1")
        assert sh.get("B1") == TYPE_ERROR

    def test_string_ref_unary_minus(self):
        """A1="hi", =-A1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hi"})
        sh.set("B1", "=-A1")
        assert sh.get("B1") == TYPE_ERROR

    def test_string_ref_ordering(self):
        """A1="abc", B1="def", =A1<B1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "abc", "B1": "def"})
        sh.set("C1", "=A1<B1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_equal(self):
        """A1="x", B1="x", =A1=B1 -> 1."""
        wb, sh = _wb_with({"A1": "x", "B1": "x"})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == 1

    def test_string_ref_not_equal(self):
        """A1="x", B1="y", =A1<>B1 -> 1."""
        wb, sh = _wb_with({"A1": "x", "B1": "y"})
        sh.set("C1", "=A1<>B1")
        assert sh.get("C1") == 1

    def test_mixed_int_string_comparison(self):
        """A1=1, B1="x", =A1=B1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": 1, "B1": "x"})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == TYPE_ERROR

    def test_error_string_literal_preserved(self):
        """A1="#DIV!" (literal), =A1 -> "#DIV!" (string, not error)."""
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1")
        assert sh.get("B1") == "#DIV!"

    def test_error_string_literal_in_arithmetic(self):
        """A1="#DIV!" (literal), =A1+1 -> #TYPE! (string + int)."""
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1+1")
        assert sh.get("B1") == TYPE_ERROR

    def test_error_string_literal_preserved_through_cache(self):
        """A1="#DIV!", B1="=A1" (cached), C1="=B1+1" -> #TYPE! (not #DIV!).

        Verifies that the cache preserves string provenance: B1's cached
        result is the string "#DIV!" (not an error sentinel), so C1 sees
        a string operand and returns #TYPE! for string + int.
        """
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1")
        sh.set("C1", "=B1+1")
        # Evaluate B1 first to populate the cache.
        assert sh.get("B1") == "#DIV!"
        assert sh.get("C1") == TYPE_ERROR

    def test_error_string_literal_chain_preserved_through_cache(self):
        """A1="#DIV!", B1="=A1", C1="=B1", D1="=C1+1" -> #TYPE! (cached chain)."""
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1")
        sh.set("C1", "=B1")
        sh.set("D1", "=C1+1")
        # Evaluate B1 and C1 first to populate the cache.
        assert sh.get("B1") == "#DIV!"
        assert sh.get("C1") == "#DIV!"
        assert sh.get("D1") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 7. NAME tokens and #NAME! error (R3/R5)
# ---------------------------------------------------------------------------

class TestNameTokens:
    def test_multi_letter_uppercase_is_name(self):
        """FOO is a NAME token, not #PARSE!."""
        assert parse_formula("FOO") == NAME_ERROR

    def test_multi_letter_with_digits_is_name(self):
        """AA1 is a NAME token, not #PARSE!."""
        assert parse_formula("AA1") == NAME_ERROR

    def test_single_letter_no_digits_is_parse_error(self):
        """F (single uppercase letter, no digits) is #PARSE!."""
        assert parse_formula("F") == PARSE_ERROR

    def test_name_in_workbook_returns_name_error(self):
        """=FOO in a workbook cell returns "#NAME!" as string."""
        wb, sh = _wb_with({})
        sh.set("A1", "=FOO")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == "#NAME!"

    def test_name_aa1_in_workbook_returns_name_error(self):
        """=AA1 in a workbook cell returns "#NAME!" as string."""
        wb, sh = _wb_with({})
        sh.set("A1", "=AA1")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == "#NAME!"

    def test_name_error_is_string_not_exception(self):
        """#NAME! is returned as a string, not raised as an exception."""
        wb, sh = _wb_with({})
        sh.set("A1", "=FOO")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == "#NAME!"

    def test_name_in_arithmetic_returns_name_error(self):
        """=FOO+1 returns "#NAME!" (NAME propagates through arithmetic)."""
        wb, sh = _wb_with({})
        sh.set("A1", "=FOO+1")
        result = sh.get("A1")
        assert isinstance(result, str)
        assert result == "#NAME!"

    def test_name_short_circuits_right_operand(self):
        """=FOO+B1 where B1="=1/0" -> #NAME! and B1 not evaluated."""
        wb, sh = _wb_with({"B1": "=1/0"})
        sh.set("C1", "=FOO+B1")
        assert sh.get("C1") == NAME_ERROR
        assert sh.eval_count == 1  # only C1 evaluated, B1 skipped
