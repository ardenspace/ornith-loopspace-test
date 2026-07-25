"""Task 2.2: Arithmetic with typed refs, error propagation, and eval_count.

Covers R4/R5/R6/R13: integer arithmetic, division truncation, #DIV!,
#TYPE! for string operands, #REF! for invalid addresses, string
provenance through formula refs, same-type string comparisons, and
left-to-right short-circuit with eval_count evidence.
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
# 1. Invalid refs -> #REF!
# ---------------------------------------------------------------------------

class TestInvalidRefs:
    def test_a0_returns_ref_error(self):
        """A0 is not a valid cell address -> #REF!."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A0")
        assert sh.get("C1") == REF_ERROR

    def test_a01_returns_ref_error(self):
        """A01 has a leading zero -> #REF!."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A01")
        assert sh.get("C1") == REF_ERROR

    def test_a100_returns_ref_error(self):
        """A100 is beyond the valid range (1-99) -> #REF!."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A100")
        assert sh.get("C1") == REF_ERROR

    def test_z0_returns_ref_error(self):
        """Z0 is not a valid cell address -> #REF!."""
        wb, sh = _wb_with({})
        sh.set("C1", "=Z0")
        assert sh.get("C1") == REF_ERROR

    def test_invalid_ref_in_addition(self):
        """=A0+B1 where A0 is invalid -> #REF!."""
        wb, sh = _wb_with({"B1": 1})
        sh.set("C1", "=A0+B1")
        assert sh.get("C1") == REF_ERROR

    def test_invalid_ref_in_multiplication(self):
        """=A01*2 where A01 is invalid -> #REF!."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A01*2")
        assert sh.get("C1") == REF_ERROR

    def test_invalid_ref_in_comparison(self):
        """=A100>0 where A100 is invalid -> #REF!."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A100>0")
        assert sh.get("C1") == REF_ERROR


# ---------------------------------------------------------------------------
# 2. Empty valid refs -> int 0
# ---------------------------------------------------------------------------

class TestEmptyRefs:
    def test_empty_ref_is_zero(self):
        """An unset valid ref contributes int 0."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A1")
        assert sh.get("C1") == 0

    def test_empty_ref_in_addition(self):
        """=A1+B1 where both are empty -> 0."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A1+B1")
        assert sh.get("C1") == 0

    def test_empty_ref_in_multiplication(self):
        """=A1*B1 where both are empty -> 0."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A1*B1")
        assert sh.get("C1") == 0

    def test_empty_ref_in_division(self):
        """=1/A1 where A1 is empty -> #DIV! (dividing by 0)."""
        wb, sh = _wb_with({})
        sh.set("C1", "=1/A1")
        assert sh.get("C1") == DIV_ERROR

    def test_empty_ref_in_comparison(self):
        """=A1=0 where A1 is empty -> 1 (0==0)."""
        wb, sh = _wb_with({})
        sh.set("C1", "=A1=0")
        assert sh.get("C1") == 1


# ---------------------------------------------------------------------------
# 3. String refs in arithmetic -> #TYPE!
# ---------------------------------------------------------------------------

class TestStringRefsInArithmetic:
    def test_string_ref_plus_int(self):
        """A1 (string) + 1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=A1+1")
        assert sh.get("C1") == TYPE_ERROR

    def test_int_plus_string_ref(self):
        """1 + A1 (string) -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=1+A1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_multiply(self):
        """A1 (string) * 2 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=A1*2")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_subtract(self):
        """A1 (string) - 1 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=A1-1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_divide(self):
        """A1 (string) / 2 -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=A1/2")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_ref_unary_minus(self):
        """-A1 where A1 is a string -> #TYPE!."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("C1", "=-A1")
        assert sh.get("C1") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 4. String comparisons -> 1/0
# ---------------------------------------------------------------------------

class TestStringComparisons:
    def test_string_equal_true(self):
        """A1="hello", B1="hello" -> =A1=B1 is 1."""
        wb, sh = _wb_with({"A1": "hello", "B1": "hello"})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == 1

    def test_string_equal_false(self):
        """A1="hello", B1="world" -> =A1=B1 is 0."""
        wb, sh = _wb_with({"A1": "hello", "B1": "world"})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == 0

    def test_string_not_equal_true(self):
        """A1="hello", B1="world" -> =A1<>B1 is 1."""
        wb, sh = _wb_with({"A1": "hello", "B1": "world"})
        sh.set("C1", "=A1<>B1")
        assert sh.get("C1") == 1

    def test_string_not_equal_false(self):
        """A1="hello", B1="hello" -> =A1<>B1 is 0."""
        wb, sh = _wb_with({"A1": "hello", "B1": "hello"})
        sh.set("C1", "=A1<>B1")
        assert sh.get("C1") == 0

    def test_string_less_than(self):
        """A1="abc", B1="def" -> =A1<B1 is #TYPE! (R13: string orderings not permitted)."""
        wb, sh = _wb_with({"A1": "abc", "B1": "def"})
        sh.set("C1", "=A1<B1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_greater_than(self):
        """A1="def", B1="abc" -> =A1>B1 is #TYPE! (R13: string orderings not permitted)."""
        wb, sh = _wb_with({"A1": "def", "B1": "abc"})
        sh.set("C1", "=A1>B1")
        assert sh.get("C1") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 5. Literal error-shaped strings preserve string provenance
# ---------------------------------------------------------------------------

class TestErrorStringProvenance:
    def test_error_string_through_formula_ref(self):
        """A1="#DIV!", B1="=A1", C1="=B1+1" -> #TYPE! (not #DIV!)."""
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1")
        sh.set("C1", "=B1+1")
        assert sh.get("C1") == TYPE_ERROR

    def test_error_string_through_chain(self):
        """A1="#DIV!", B1="=A1", C1="=B1", D1="=C1+1" -> #TYPE!."""
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1")
        sh.set("C1", "=B1")
        sh.set("D1", "=C1+1")
        assert sh.get("D1") == TYPE_ERROR

    def test_parse_error_string_preserved(self):
        """A1="#PARSE!", B1="=A1" -> B1 is the string "#PARSE!", not error."""
        wb, sh = _wb_with({"A1": "#PARSE!"})
        sh.set("B1", "=A1")
        assert sh.get("B1") == "#PARSE!"

    def test_error_string_multiply(self):
        """A1="#DIV!", B1="=A1" -> =B1*2 is #TYPE!."""
        wb, sh = _wb_with({"A1": "#DIV!"})
        sh.set("B1", "=A1")
        sh.set("C1", "=B1*2")
        assert sh.get("C1") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 6. Division semantics
# ---------------------------------------------------------------------------

class TestDivisionSemantics:
    def test_division_truncates_toward_zero(self):
        """7/2 -> 3."""
        wb, sh = _wb_with({})
        sh.set("A1", "=7/2")
        assert sh.get("A1") == 3

    def test_division_negative_truncates_toward_zero(self):
        """-7/2 -> -3."""
        wb, sh = _wb_with({})
        sh.set("A1", "=-7/2")
        assert sh.get("A1") == -3

    def test_division_by_zero(self):
        """1/0 -> #DIV!."""
        wb, sh = _wb_with({})
        sh.set("A1", "=1/0")
        assert sh.get("A1") == DIV_ERROR

    def test_division_via_ref_div_by_zero(self):
        """A1=0, =1/A1 -> #DIV!."""
        wb, sh = _wb_with({"A1": 0})
        sh.set("B1", "=1/A1")
        assert sh.get("B1") == DIV_ERROR

    def test_division_exact(self):
        """10/2 -> 5."""
        wb, sh = _wb_with({})
        sh.set("A1", "=10/2")
        assert sh.get("A1") == 5


# ---------------------------------------------------------------------------
# 7. Left-to-right short-circuit with eval_count
# ---------------------------------------------------------------------------

class TestShortCircuit:
    def test_div_by_zero_short_circuits_eval_count(self):
        """=A1+B1 where A1=1/0 -> #DIV! and B1 is not evaluated.

        eval_count counts formula computation starts: C1 and A1 both start,
        so eval_count=2. B1 is short-circuited and not evaluated.
        """
        wb, sh = _wb_with({"B1": 999})
        sh.set("A1", "=1/0")
        sh.set("C1", "=A1+B1")
        assert sh.get("C1") == DIV_ERROR
        assert sh.eval_count == 2

    def test_type_error_short_circuits_eval_count(self):
        """=A1+B1 where A1="x" -> #TYPE! and B1 is not evaluated.

        eval_count counts formula computation starts: only C1 is a formula
        cell, so eval_count=1. A1 is a literal string, B1 is short-circuited.
        """
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1+B1")
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_no_short_circuit_both_valid(self):
        """=A1+B1 where both are valid -> eval_count=1.

        eval_count counts formula computation starts: only C1 is a formula
        cell. A1 and B1 are literals, so they don't increment the counter.
        """
        wb, sh = _wb_with({"A1": 1, "B1": 2})
        sh.set("C1", "=A1+B1")
        assert sh.get("C1") == 3
        assert sh.eval_count == 1

    def test_ref_eval_count_accumulates(self):
        """Multiple get() calls: first call evaluates, subsequent calls use cache.

        eval_count counts formula computation starts: first get increments
        to 1, second get uses cache so no increment.
        """
        wb, sh = _wb_with({"A1": 1, "B1": 2})
        sh.set("C1", "=A1+B1")
        sh.get("C1")
        sh.get("C1")
        assert sh.eval_count == 1  # only first get evaluates (second is cached)

    def test_error_in_multiplication_short_circuits(self):
        """=A1*B1 where A1="x" -> #TYPE! and B1 is not evaluated."""
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1*B1")
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_error_in_comparison_short_circuits(self):
        """=A1+B1=0 where A1="x" -> #TYPE! and right side not fully evaluated."""
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1+B1=0")
        assert sh.get("C1") == TYPE_ERROR
        # A1 evaluated (1), then +B1 short-circuits (B1 not evaluated)
        assert sh.eval_count == 1

    def test_invalid_ref_short_circuits(self):
        """=A0+B1 where A0 is invalid -> #REF! and B1 is not evaluated."""
        wb, sh = _wb_with({"B1": 999})
        sh.set("C1", "=A0+B1")
        assert sh.get("C1") == REF_ERROR
        assert sh.eval_count == 1

    def test_string_less_than_short_circuits(self):
        """=A1<B1 where A1="x" -> #TYPE! and B1 is not evaluated (eval_count=1)."""
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1<B1")
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_string_greater_than_short_circuits(self):
        """=A1>B1 where A1="x" -> #TYPE! and B1 is not evaluated (eval_count=1)."""
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1>B1")
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_string_leq_short_circuits(self):
        """=A1<=B1 where A1="x" -> #TYPE! and B1 is not evaluated (eval_count=1)."""
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1<=B1")
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_string_geq_short_circuits(self):
        """=A1>=B1 where A1="x" -> #TYPE! and B1 is not evaluated (eval_count=1)."""
        wb, sh = _wb_with({"A1": "x", "B1": 999})
        sh.set("C1", "=A1>=B1")
        assert sh.get("C1") == TYPE_ERROR
        assert sh.eval_count == 1

    def test_string_equal_does_not_short_circuit(self):
        """=A1=B1 where both are strings -> evaluates both (eval_count=1).

        eval_count counts formula computation starts: only C1 is a formula
        cell. A1 and B1 are literals, so they don't increment the counter.
        """
        wb, sh = _wb_with({"A1": "x", "B1": "y"})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == 0
        assert sh.eval_count == 1

    def test_string_not_equal_does_not_short_circuit(self):
        """=A1<>B1 where both are strings -> evaluates both (eval_count=1).

        eval_count counts formula computation starts: only C1 is a formula
        cell. A1 and B1 are literals, so they don't increment the counter.
        """
        wb, sh = _wb_with({"A1": "x", "B1": "y"})
        sh.set("C1", "=A1<>B1")
        assert sh.get("C1") == 1
        assert sh.eval_count == 1


# ---------------------------------------------------------------------------
# 8. Mixed type comparisons -> #TYPE!
# ---------------------------------------------------------------------------

class TestMixedTypeComparisons:
    def test_int_vs_string_equal(self):
        """A1=1, B1="hello" -> =A1=B1 is #TYPE!."""
        wb, sh = _wb_with({"A1": 1, "B1": "hello"})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == TYPE_ERROR

    def test_string_vs_int_equal(self):
        """A1="hello", B1=1 -> =A1=B1 is #TYPE!."""
        wb, sh = _wb_with({"A1": "hello", "B1": 1})
        sh.set("C1", "=A1=B1")
        assert sh.get("C1") == TYPE_ERROR

    def test_int_vs_string_less_than(self):
        """A1=1, B1="hello" -> =A1<B1 is #TYPE!."""
        wb, sh = _wb_with({"A1": 1, "B1": "hello"})
        sh.set("C1", "=A1<B1")
        assert sh.get("C1") == TYPE_ERROR


# ---------------------------------------------------------------------------
# 9. Formula cells referencing other formula cells
# ---------------------------------------------------------------------------

class TestFormulaChaining:
    def test_formula_referring_to_formula(self):
        """A1=1, B1="=A1+1", C1="=B1*2" -> C1=4."""
        wb, sh = _wb_with({"A1": 1})
        sh.set("B1", "=A1+1")
        sh.set("C1", "=B1*2")
        assert sh.get("C1") == 4

    def test_formula_referring_to_formula_error(self):
        """A1="=1/0", B1="=A1+1" -> B1=#DIV!."""
        wb, sh = _wb_with({})
        sh.set("A1", "=1/0")
        sh.set("B1", "=A1+1")
        assert sh.get("B1") == DIV_ERROR

    def test_formula_referring_to_string(self):
        """A1="hello", B1="=A1" -> B1 is "hello" (string)."""
        wb, sh = _wb_with({"A1": "hello"})
        sh.set("B1", "=A1")
        assert sh.get("B1") == "hello"
