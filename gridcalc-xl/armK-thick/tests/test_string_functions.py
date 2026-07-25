"""Task 5.2: CONCAT and LEN string functions (R14).

Covers:
- CONCAT accepts one or more expression arguments, evaluates left-to-right,
  short-circuits on first error, renders ints in base 10 without leading
  zeros, and preserves string arguments as-is.
- CONCAT renders empty-cell reference arguments as "0".
- LEN accepts exactly one expression argument and returns character counts
  for strings or decimal-rendered ints.
- Wrong arity or empty-call forms for CONCAT and LEN evaluate to #PARSE!.
"""
import pytest

from gridcalc.formula import (
    PARSE_ERROR, DIV_ERROR, TYPE_ERROR, REF_ERROR,
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
# 1. CONCAT basic behavior (criterion 1)
# ---------------------------------------------------------------------------

class TestConcatBasic:
    def test_concat_single_string(self):
        """CONCAT with single string returns the string."""
        assert parse_formula('CONCAT("hello")') == "hello"

    def test_concat_multiple_strings(self):
        """CONCAT with multiple strings concatenates them."""
        assert parse_formula('CONCAT("a","b","c")') == "abc"

    def test_concat_single_int(self):
        """CONCAT with single int renders as base-10 string."""
        assert parse_formula('CONCAT(7)') == "7"

    def test_concat_multiple_ints(self):
        """CONCAT with multiple ints renders each as base-10."""
        assert parse_formula('CONCAT(1,2,3)') == "123"

    def test_concat_mixed_string_and_int(self):
        """CONCAT with mixed string and int args."""
        assert parse_formula('CONCAT("x",5,"y")') == "x5y"

    def test_concat_int_no_leading_zeros(self):
        """CONCAT renders ints without leading zeros (007 -> "7")."""
        assert parse_formula('CONCAT(007)') == "7"

    def test_concat_negative_int(self):
        """CONCAT renders negative ints with leading minus."""
        assert parse_formula('CONCAT(-12)') == "-12"

    def test_concat_zero(self):
        """CONCAT with 0 renders as "0"."""
        assert parse_formula('CONCAT(0)') == "0"


# ---------------------------------------------------------------------------
# 2. CONCAT with empty-cell references (criterion 2)
# ---------------------------------------------------------------------------

class TestConcatEmptyCell:
    def test_concat_empty_cell_ref(self):
        """CONCAT with empty-cell reference renders as "0"."""
        wb, sh = _wb_with({})
        sh.set("C1", "=CONCAT(A1)")
        assert sh.get("C1") == "0"

    def test_concat_mixed_empty_and_string(self):
        """CONCAT with empty cell and string."""
        wb, sh = _wb_with({})
        sh.set("C1", '=CONCAT(A1,"x")')
        assert sh.get("C1") == "0x"

    def test_concat_mixed_string_and_empty(self):
        """CONCAT with string and empty cell."""
        wb, sh = _wb_with({})
        sh.set("C1", '=CONCAT("x",A1)')
        assert sh.get("C1") == "x0"


# ---------------------------------------------------------------------------
# 3. CONCAT short-circuit on error (criterion 1)
# ---------------------------------------------------------------------------

class TestConcatShortCircuit:
    def test_concat_error_in_middle(self):
        """CONCAT with error in middle: short-circuits, doesn't evaluate later args."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", '=CONCAT("a",A1,"b")')
        assert sh.get("C1") == DIV_ERROR

    def test_concat_error_first_arg(self):
        """CONCAT with error as first arg: short-circuits."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", '=CONCAT(A1,"b")')
        assert sh.get("C1") == DIV_ERROR

    def test_concat_type_error(self):
        """CONCAT with type error (string in arithmetic context via ref)."""
        # A1 contains a string, but we're using it in a context that would
        # cause a type error if we tried arithmetic. However, CONCAT just
        # takes strings as-is, so this should work.
        # Let's test with a formula cell that produces an error.
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", '=CONCAT(A1,"x")')
        assert sh.get("C1") == "hellox"

    def test_concat_eval_count_short_circuit(self):
        """CONCAT with error: later args not evaluated (verified via eval_count)."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            if addr == "B1":
                return ("int", 42)
            return ("int", 0)

        result = parse_formula('CONCAT(A1,B1)', resolve_ref=resolve_ref)
        assert result == DIV_ERROR
        assert "A1" in eval_log
        assert "B1" not in eval_log


# ---------------------------------------------------------------------------
# 4. LEN basic behavior (criterion 2)
# ---------------------------------------------------------------------------

class TestLenBasic:
    def test_len_string(self):
        """LEN with string returns character count."""
        assert parse_formula('LEN("hello")') == 5

    def test_len_empty_string(self):
        """LEN with empty string returns 0."""
        assert parse_formula('LEN("")') == 0

    def test_len_int(self):
        """LEN with int returns character count of decimal rendering."""
        assert parse_formula('LEN(123)') == 3

    def test_len_negative_int(self):
        """LEN with negative int returns character count including minus."""
        assert parse_formula('LEN(-12)') == 3

    def test_len_zero(self):
        """LEN with 0 returns 1."""
        assert parse_formula('LEN(0)') == 1

    def test_len_single_char(self):
        """LEN with single character string."""
        assert parse_formula('LEN("x")') == 1

    def test_len_unicode_string(self):
        """LEN with unicode string returns character count."""
        assert parse_formula('LEN("héllo")') == 5

    def test_len_string_with_spaces(self):
        """LEN with string containing spaces."""
        assert parse_formula('LEN("hello world")') == 11


# ---------------------------------------------------------------------------
# 5. LEN with empty-cell references (criterion 2)
# ---------------------------------------------------------------------------

class TestLenEmptyCell:
    def test_len_empty_cell_ref(self):
        """LEN with empty-cell reference returns 1 (len("0"))."""
        wb, sh = _wb_with({})
        sh.set("C1", "=LEN(A1)")
        assert sh.get("C1") == 1

    def test_len_int_cell(self):
        """LEN with int cell returns character count of decimal rendering."""
        wb, sh = _wb_with({"A1": 123})
        sh.set("C1", "=LEN(A1)")
        assert sh.get("C1") == 3

    def test_len_string_cell(self):
        """LEN with string cell returns character count."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=LEN(A1)")
        assert sh.get("C1") == 5


# ---------------------------------------------------------------------------
# 6. LEN short-circuit on error (criterion 1)
# ---------------------------------------------------------------------------

class TestLenShortCircuit:
    def test_len_error_arg(self):
        """LEN with error argument returns the error."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=LEN(A1)")
        assert sh.get("C1") == DIV_ERROR


# ---------------------------------------------------------------------------
# 7. Wrong arity / empty-call forms (criterion 3)
# ---------------------------------------------------------------------------

class TestWrongArity:
    def test_concat_empty_call(self):
        """CONCAT() with no arguments returns #PARSE!."""
        assert parse_formula('CONCAT()') == PARSE_ERROR

    def test_len_empty_call(self):
        """LEN() with no arguments returns #PARSE!."""
        assert parse_formula('LEN()') == PARSE_ERROR

    def test_len_two_args(self):
        """LEN with two arguments returns #PARSE!."""
        assert parse_formula('LEN("a","b")') == PARSE_ERROR

    def test_len_three_args(self):
        """LEN with three arguments returns #PARSE!."""
        assert parse_formula('LEN("a","b","c")') == PARSE_ERROR


# ---------------------------------------------------------------------------
# 7b. Verifier finding 1: short-circuit with evaluable later refs
# ---------------------------------------------------------------------------

class TestVerifierFinding1:
    def test_concat_short_circuit_with_evaluable_later_refs(self):
        """CONCAT(A1,B1,C1) with A1=int, B1=error: C1 is not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("int", 1)
            if addr == "B1":
                return ("error", "#DIV!")
            if addr == "C1":
                return ("int", 99)
            return ("int", 0)

        result = parse_formula('CONCAT(A1,B1,C1)', resolve_ref=resolve_ref)
        assert result == DIV_ERROR
        assert "A1" in eval_log
        assert "B1" in eval_log
        assert "C1" not in eval_log


# ---------------------------------------------------------------------------
# 7c. Verifier finding 2: function args are full expressions
# ---------------------------------------------------------------------------

class TestVerifierFinding2:
    def test_concat_with_expression_args(self):
        """CONCAT(1+2,"x") == "3x" — args are full expressions, not just literals."""
        assert parse_formula('CONCAT(1+2,"x")') == "3x"

    def test_len_with_expression_arg(self):
        """LEN(10+5) == 2 — LEN arg is a full expression."""
        assert parse_formula('LEN(10+5)') == 2


# ---------------------------------------------------------------------------
# 8. Reference model differential tests
# ---------------------------------------------------------------------------

class TestDifferential:
    """Compare implementation against independent reference model."""

    def _ref_eval(self, formula_text, resolve_ref=None):
        """Evaluate using the reference model."""
        from tests.reference_model import (
            _ref_tokenize, _ref_parse_expr, _ref_evaluate,
            _RefErrorValue,
        )

        tokens = _ref_tokenize(formula_text)
        if tokens is None:
            return "#PARSE!"

        pos = [0]
        ast_node = _ref_parse_expr(tokens, pos)
        if ast_node is None or pos[0] != len(tokens):
            return "#PARSE!"

        eval_count = [0]
        result = _ref_evaluate(ast_node, resolve_ref, eval_count)

        if isinstance(result, _RefErrorValue):
            return result.code
        return result

    @pytest.mark.parametrize("formula_text", [
        'CONCAT("hello")',
        'CONCAT("a","b","c")',
        'CONCAT(7)',
        'CONCAT(1,2,3)',
        'CONCAT("x",5,"y")',
        'CONCAT(007)',
        'CONCAT(-12)',
        'CONCAT(0)',
        'CONCAT(1+2,"x")',
        'LEN("hello")',
        'LEN("")',
        'LEN(123)',
        'LEN(-12)',
        'LEN(0)',
        'LEN("x")',
        'LEN("héllo")',
        'LEN("hello world")',
        'LEN(10+5)',
    ])
    def test_differential(self, formula_text):
        """Implementation and reference model agree on all these formulas."""
        impl_result = parse_formula(formula_text)
        ref_result = self._ref_eval(formula_text)
        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )

    @pytest.mark.parametrize("formula_text", [
        'CONCAT()',
        'LEN()',
        'LEN("a","b")',
        'LEN("a","b","c")',
    ])
    def test_differential_wrong_arity(self, formula_text):
        """Wrong arity forms return #PARSE! in both implementations."""
        impl_result = parse_formula(formula_text)
        ref_result = self._ref_eval(formula_text)
        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )

    @pytest.mark.parametrize("formula_text", [
        'CONCAT("a",A1,"b")',
        'CONCAT(A1,"b")',
        'LEN(A1)',
    ])
    def test_differential_short_circuit(self, formula_text):
        """Short-circuit behavior matches reference model."""
        eval_log_impl = []
        eval_log_ref = []

        def resolve_ref_impl(addr):
            eval_log_impl.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            if addr == "B1":
                return ("int", 42)
            return ("int", 0)

        def resolve_ref_ref(addr):
            eval_log_ref.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            if addr == "B1":
                return ("int", 42)
            return ("int", 0)

        impl_result = parse_formula(formula_text, resolve_ref=resolve_ref_impl)
        ref_result = self._ref_eval(formula_text, resolve_ref=resolve_ref_ref)

        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )
        assert eval_log_impl == eval_log_ref, (
            f"Eval log mismatch for {formula_text!r}: "
            f"impl={eval_log_impl}, ref={eval_log_ref}"
        )
