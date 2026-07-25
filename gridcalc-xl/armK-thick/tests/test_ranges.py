"""Task 3.1: Range validation and SUM/MIN/MAX — R3, R7, R8 tests."""
import os

import pytest

from gridcalc.formula import PARSE_ERROR, parse_formula


_PACKAGE_ROOT = os.path.join(os.path.dirname(__file__), "..", "gridcalc")


# ---------------------------------------------------------------------------
# 1. Parser accepts SUM, MIN, MAX with one range argument
# ---------------------------------------------------------------------------

class TestParserAcceptsRangeFunctions:
    def test_sum_range_basic(self):
        """SUM(A1:B2) with numeric cells returns the sum."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == 10

    def test_min_range_basic(self):
        """MIN(A1:B2) with numeric cells returns the minimum."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", 2)
        sh.set("A2", 8)
        sh.set("B2", 1)
        sh.set("C1", "=MIN(A1:B2)")
        assert sh.get("C1") == 1

    def test_max_range_basic(self):
        """MAX(A1:B2) with numeric cells returns the maximum."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", 2)
        sh.set("A2", 8)
        sh.set("B2", 1)
        sh.set("C1", "=MAX(A1:B2)")
        assert sh.get("C1") == 8

    def test_sum_single_cell_range(self):
        """SUM(A1:A1) with a single cell returns its value."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 42)
        sh.set("B1", "=SUM(A1:A1)")
        assert sh.get("B1") == 42

    def test_sum_single_row_range(self):
        """SUM(A1:C1) with a single row returns the sum."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", 3)
        sh.set("D1", "=SUM(A1:C1)")
        assert sh.get("D1") == 6

    def test_sum_single_column_range(self):
        """SUM(A1:A3) with a single column returns the sum."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("A2", 2)
        sh.set("A3", 3)
        sh.set("B1", "=SUM(A1:A3)")
        assert sh.get("B1") == 6

    def test_sum_with_spaces_around_colon(self):
        """SUM(A1 : B1) with spaces around : is valid."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1 : B1)")
        assert sh.get("C1") == 3

    def test_sum_with_spaces_around_parens(self):
        """SUM ( A1:B2 ) with spaces around parens is valid."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM ( A1:B2 )")
        assert sh.get("C1") == 3

    def test_min_with_tabs(self):
        """MIN(A1\t:\tB1) with tabs around : is valid."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", 20)
        sh.set("C1", "=MIN(A1\t:\tB1)")
        assert sh.get("C1") == 10

    def test_max_with_tabs(self):
        """MAX(\tA1:B1\t) with tabs around parens is valid."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 10)
        sh.set("B1", 20)
        sh.set("C1", "=MAX(\tA1:B1\t)")
        assert sh.get("C1") == 20


# ---------------------------------------------------------------------------
# 2. Parser rejects wrong arity, unknown callees, standalone ranges,
#    parenthesized ranges
# ---------------------------------------------------------------------------

class TestParserRejectsInvalidRangeUsage:
    def test_sum_no_args(self):
        """SUM() with no arguments returns #PARSE!."""
        assert parse_formula("SUM()") == PARSE_ERROR

    def test_sum_two_args(self):
        """SUM(A1:B1, C1) with two arguments returns #PARSE!."""
        assert parse_formula("SUM(A1:B1, C1)") == PARSE_ERROR

    def test_sum_three_args(self):
        """SUM(A1, B1, C1) with three arguments returns #PARSE!."""
        assert parse_formula("SUM(A1, B1, C1)") == PARSE_ERROR

    def test_unknown_callee(self):
        """FOO(A1:B1) with unknown callee returns #PARSE!."""
        assert parse_formula("FOO(A1:B1)") == PARSE_ERROR

    def test_unknown_callee_sum_like(self):
        """SUMMER(A1:B1) with unknown callee returns #PARSE!."""
        assert parse_formula("SUMMER(A1:B1)") == PARSE_ERROR

    def test_standalone_range(self):
        """A1:B1 standalone (not in a function) returns #PARSE!."""
        assert parse_formula("A1:B1") == PARSE_ERROR

    def test_parenthesized_range(self):
        """(A1:B1) parenthesized range returns #PARSE!."""
        assert parse_formula("(A1:B1)") == PARSE_ERROR

    def test_sum_parenthesized_range_arg(self):
        """SUM((A1:B1)) with parenthesized range arg returns #PARSE!."""
        assert parse_formula("SUM((A1:B1))") == PARSE_ERROR

    def test_range_in_addition(self):
        """A1:B1+C1 standalone range in expression returns #PARSE!."""
        assert parse_formula("A1:B1+C1") == PARSE_ERROR


# ---------------------------------------------------------------------------
# 3. Range validation: endpoint grid membership and ordering
# ---------------------------------------------------------------------------

class TestRangeValidation:
    def test_valid_range_a10_to_z99(self):
        """SUM(A10:Z99) with max valid range works (all empty -> 0 for SUM)."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A10", 10)
        sh.set("B10", 20)
        sh.set("Z99", 30)
        sh.set("C1", "=SUM(A10:Z99)")
        assert sh.get("C1") == 60

    def test_misordered_range_column(self):
        """SUM(B1:A1) with TL col > BR col returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(B1:A1)")
        assert sh.get("C1") == "#REF!"

    def test_misordered_range_row(self):
        """SUM(A2:A1) with TL row > BR row returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("A2", 2)
        sh.set("C1", "=SUM(A2:A1)")
        assert sh.get("C1") == "#REF!"

    def test_misordered_range_both(self):
        """SUM(B2:A1) with both misordered returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B2", 2)
        sh.set("C1", "=SUM(B2:A1)")
        assert sh.get("C1") == "#REF!"

    def test_invalid_endpoint_column_aa(self):
        """SUM(A1:AA1) with two-letter column: AA1 is a NAME token, not REF,
        so the range argument shape is wrong → #PARSE! (R3)."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "=SUM(A1:AA1)")
        assert sh.get("B1") == PARSE_ERROR

    def test_invalid_endpoint_row_100(self):
        """SUM(A1:A100) with row > 99 returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "=SUM(A1:A100)")
        assert sh.get("B1") == "#REF!"

    def test_invalid_endpoint_row_0(self):
        """SUM(A0:A1) with row 0 returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "=SUM(A0:A1)")
        assert sh.get("B1") == "#REF!"

    def test_invalid_endpoint_lowercase(self):
        """SUM(a1:b1) with lowercase: a1 is not a valid REF token → #PARSE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "=SUM(a1:b1)")
        assert sh.get("B1") == PARSE_ERROR

    def test_invalid_endpoint_digit_first(self):
        """SUM(1A:1B) with digit-first: 1A is not a valid REF token → #PARSE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "=SUM(1A:1B)")
        assert sh.get("B1") == PARSE_ERROR

    def test_same_cell_range(self):
        """SUM(A1:A1) with same cell range works."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 42)
        sh.set("B1", "=SUM(A1:A1)")
        assert sh.get("B1") == 42

    def test_single_row_range(self):
        """SUM(A1:C1) with single row range works."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", 3)
        sh.set("D1", "=SUM(A1:C1)")
        assert sh.get("D1") == 6

    def test_single_column_range(self):
        """SUM(A1:A3) with single column range works."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("A2", 2)
        sh.set("A3", 3)
        sh.set("B1", "=SUM(A1:A3)")
        assert sh.get("B1") == 6

    def test_min_range_validation(self):
        """MIN with misordered range returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=MIN(B1:A1)")
        assert sh.get("C1") == "#REF!"

    def test_max_range_validation(self):
        """MAX with misordered range returns #REF!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=MAX(B1:A1)")
        assert sh.get("C1") == "#REF!"


# ---------------------------------------------------------------------------
# 4. Row-major visit order and short-circuit on first error/string
# ---------------------------------------------------------------------------

class TestRowMajorVisitOrder:
    def test_sum_short_circuits_on_string_first_cell(self):
        """SUM(A1:B2) with string at A1 (first in row-major) returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "hello")
        sh.set("B1", 2)
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_sum_short_circuits_on_string_second_cell(self):
        """SUM(A1:B2) with string at B1 (second in row-major) returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "hello")
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_sum_short_circuits_on_string_third_cell(self):
        """SUM(A1:B2) with string at A2 (third in row-major) returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("A2", "hello")
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_sum_short_circuits_on_string_fourth_cell(self):
        """SUM(A1:B2) with string at B2 (fourth in row-major) returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("A2", 3)
        sh.set("B2", "hello")
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_min_short_circuits_on_string(self):
        """MIN(A1:B2) with string at B2 returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", 2)
        sh.set("A2", 8)
        sh.set("B2", "x")
        sh.set("C1", "=MIN(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_max_short_circuits_on_string(self):
        """MAX(A1:B2) with string at A2 returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", 2)
        sh.set("A2", "x")
        sh.set("B2", 8)
        sh.set("C1", "=MAX(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_row_major_order_2x3(self):
        """SUM(A1:C2) visits A1,B1,C1,A2,B2,C2 in row-major order."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", 3)
        sh.set("A2", 4)
        sh.set("B2", 5)
        sh.set("C2", 6)
        sh.set("D1", "=SUM(A1:C2)")
        assert sh.get("D1") == 21

    def test_row_major_order_3x2(self):
        """SUM(A1:B3) visits A1,A2,A3,B1,B2,B3 in row-major order."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("A2", 2)
        sh.set("A3", 3)
        sh.set("B1", 4)
        sh.set("B2", 5)
        sh.set("B3", 6)
        sh.set("C1", "=SUM(A1:B3)")
        assert sh.get("C1") == 21


# ---------------------------------------------------------------------------
# 5. Empty cells contribute nothing; all-empty SUM=0, MIN/MAX=#TYPE!
# ---------------------------------------------------------------------------

class TestEmptyCells:
    def test_sum_all_empty(self):
        """SUM(A1:B2) with all empty cells returns 0."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == 0

    def test_min_all_empty(self):
        """MIN(A1:B2) with all empty cells returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("C1", "=MIN(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_max_all_empty(self):
        """MAX(A1:B2) with all empty cells returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("C1", "=MAX(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_sum_partial_empty(self):
        """SUM(A1:B2) with some empty cells ignores them."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("A2", 3)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == 4

    def test_min_partial_empty(self):
        """MIN(A1:B2) with some empty cells ignores them."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("A2", 2)
        sh.set("C1", "=MIN(A1:B2)")
        assert sh.get("C1") == 2

    def test_max_partial_empty(self):
        """MAX(A1:B2) with some empty cells ignores them."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("A2", 8)
        sh.set("C1", "=MAX(A1:B2)")
        assert sh.get("C1") == 8

    def test_sum_single_nonempty(self):
        """SUM(A1:B2) with only A1 set returns its value."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 42)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == 42

    def test_min_single_nonempty(self):
        """MIN(A1:B2) with only A1 set returns its value."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 42)
        sh.set("C1", "=MIN(A1:B2)")
        assert sh.get("C1") == 42

    def test_max_single_nonempty(self):
        """MAX(A1:B2) with only A1 set returns its value."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 42)
        sh.set("C1", "=MAX(A1:B2)")
        assert sh.get("C1") == 42


# ---------------------------------------------------------------------------
# 6. String contributions return #TYPE! at first offending member
# ---------------------------------------------------------------------------

class TestStringContributions:
    def test_sum_string_returns_type_error(self):
        """SUM with a string cell returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "hello")
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1:B1)")
        assert sh.get("C1") == "#TYPE!"

    def test_min_string_returns_type_error(self):
        """MIN with a string cell returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", "hello")
        sh.set("C1", "=MIN(A1:B1)")
        assert sh.get("C1") == "#TYPE!"

    def test_max_string_returns_type_error(self):
        """MAX with a string cell returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", "hello")
        sh.set("C1", "=MAX(A1:B1)")
        assert sh.get("C1") == "#TYPE!"

    def test_empty_string_contribution(self):
        """SUM with empty string literal cell: '' is a str, returns #TYPE!."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "")
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1:B1)")
        assert sh.get("C1") == "#TYPE!"


# ---------------------------------------------------------------------------
# 7. Range functions compose with comparisons
# ---------------------------------------------------------------------------

class TestRangeFunctionComparisons:
    def test_sum_comparison_equal(self):
        """SUM(A1:B1)=3 evaluates to 1."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1:B1)=3")
        assert sh.get("C1") == 1

    def test_sum_comparison_not_equal(self):
        """SUM(A1:B1)=4 evaluates to 0."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1:B1)=4")
        assert sh.get("C1") == 0

    def test_sum_in_addition(self):
        """SUM(A1:B1)+1 evaluates correctly."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1:B1)+1")
        assert sh.get("C1") == 4

    def test_sum_in_multiplication(self):
        """SUM(A1:B1)*2 evaluates correctly."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", 2)
        sh.set("C1", "=SUM(A1:B1)*2")
        assert sh.get("C1") == 6


# ---------------------------------------------------------------------------
# 8. Security: no forbidden runtime patterns
# ---------------------------------------------------------------------------

class TestSecurityNoForbiddenPatterns:
    def test_no_forbidden_patterns_in_formula(self):
        """formula.py must not contain eval/exec/compile/__import__/importlib/pickle."""
        import ast
        src = os.path.join(_PACKAGE_ROOT, "formula.py")
        bad = set()
        tree = ast.parse(open(src).read(), src)
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
        assert bad == set(), f"Forbidden patterns in formula.py: {bad}"


# ---------------------------------------------------------------------------
# 9. parse_formula without resolver still evaluates valid SUM/MIN/MAX
# ---------------------------------------------------------------------------

class TestParseFormulaWithoutResolver:
    def test_sum_without_resolver(self):
        """parse_formula('SUM(A1:A1)') without resolver returns 0 (empty cell)."""
        from gridcalc.formula import parse_formula
        assert parse_formula("SUM(A1:A1)") == 0

    def test_min_without_resolver(self):
        """parse_formula('MIN(A1:A1)') without resolver returns #TYPE! (all empty)."""
        from gridcalc.formula import parse_formula, TYPE_ERROR
        assert parse_formula("MIN(A1:A1)") == TYPE_ERROR

    def test_max_without_resolver(self):
        """parse_formula('MAX(A1:A1)') without resolver returns #TYPE! (all empty)."""
        from gridcalc.formula import parse_formula, TYPE_ERROR
        assert parse_formula("MAX(A1:A1)") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 10. First error in row-major visit order with competing errors
# ---------------------------------------------------------------------------

class TestFirstErrorInVisitOrder:
    def test_sum_first_error_is_type_not_ref(self):
        """SUM(A1:B2) with B1='x' (row-major 2nd) and A2=#DIV! (row-major 3rd)
        returns #TYPE! because B1 is visited first."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 1)
        sh.set("B1", "x")
        sh.set("A2", "=1/0")
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_min_first_error_is_type_not_ref(self):
        """MIN(A1:B2) with B1='x' (row-major 2nd) and A2=#DIV! (row-major 3rd)
        returns #TYPE! because B1 is visited first."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", "x")
        sh.set("A2", "=1/0")
        sh.set("B2", 8)
        sh.set("C1", "=MIN(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_max_first_error_is_type_not_ref(self):
        """MAX(A1:B2) with B1='x' (row-major 2nd) and A2=#DIV! (row-major 3rd)
        returns #TYPE! because B1 is visited first."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", 5)
        sh.set("B1", "x")
        sh.set("A2", "=1/0")
        sh.set("B2", 8)
        sh.set("C1", "=MAX(A1:B2)")
        assert sh.get("C1") == "#TYPE!"

    def test_sum_error_before_string(self):
        """SUM(A1:B2) with A1=#DIV! (row-major 1st) and B1='x' (row-major 2nd)
        returns #DIV! because A1 is visited first."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "=1/0")
        sh.set("B1", "x")
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        assert sh.get("C1") == "#DIV!"


# ---------------------------------------------------------------------------
# 11. Range evaluation short-circuits after first offending member
# ---------------------------------------------------------------------------

class TestRangeShortCircuit:
    def test_sum_short_circuits_after_first_string(self):
        """SUM(A1:B2) with A1='x' (1st) short-circuits; B1 formula never evaluated."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "x")
        sh.set("B1", "=1/0")  # Would error if evaluated
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        # If short-circuit works, B1 is never evaluated, so no #DIV! from it.
        # Result is #TYPE! from A1.
        assert sh.get("C1") == "#TYPE!"
        # Verify B1's formula was not evaluated by checking eval_count.
        # C1's evaluation should only count C1 itself (1 formula cell started).
        assert sh.eval_count == 1

    def test_sum_short_circuits_after_first_error(self):
        """SUM(A1:B2) with A1=#DIV! (1st) short-circuits; B1 formula never evaluated."""
        from gridcalc.workbook import Workbook
        wb = Workbook()
        sh = wb.add_sheet("S")
        sh.set("A1", "=1/0")
        sh.set("B1", "=1/0")  # Would error if evaluated
        sh.set("A2", 3)
        sh.set("B2", 4)
        sh.set("C1", "=SUM(A1:B2)")
        # If short-circuit works, B1 is never evaluated.
        assert sh.get("C1") == "#DIV!"
        # Only A1 and C1 were evaluated (B1 short-circuited).
        assert sh.eval_count == 2
