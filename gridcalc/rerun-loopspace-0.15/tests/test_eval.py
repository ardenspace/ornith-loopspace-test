"""Task 2.2: Evaluator — arithmetic, references, division."""
import pytest
from gridcalc import Sheet
from gridcalc.parser import parse, ParseError


class TestEvaluatorArithmetic:
    """Tests for arithmetic evaluation per R4 and Task 2.2 acceptance criteria."""

    def test_simple_addition(self):
        """'=1+2*3' is 7."""
        s = Sheet()
        s.set("A1", "=1+2*3")
        assert s.get("A1") == 7

    def test_parenthesized_expression(self):
        """'=(1+2)*3' is 9."""
        s = Sheet()
        s.set("A1", "=(1+2)*3")
        assert s.get("A1") == 9

    def test_double_negation(self):
        """'=--1' is 1."""
        s = Sheet()
        s.set("A1", "=--1")
        assert s.get("A1") == 1

    def test_subtraction_with_negation(self):
        """'=2--3' is 5."""
        s = Sheet()
        s.set("A1", "=2--3")
        assert s.get("A1") == 5

    def test_leading_zeros(self):
        """'=007' is 7."""
        s = Sheet()
        s.set("A1", "=007")
        assert s.get("A1") == 7

    def test_division_truncates_toward_zero_positive(self):
        """'=7/2' is 3."""
        s = Sheet()
        s.set("A1", "=7/2")
        assert s.get("A1") == 3

    def test_division_truncates_toward_zero_negative_numerator(self):
        """'=-7/2' is -3."""
        s = Sheet()
        s.set("A1", "=-7/2")
        assert s.get("A1") == -3

    def test_division_truncates_toward_zero_negative_denominator(self):
        """'=7/-2' is -3."""
        s = Sheet()
        s.set("A1", "=7/-2")
        assert s.get("A1") == -3

    def test_division_by_zero(self):
        """'=7/0' is '#DIV!'."""
        s = Sheet()
        s.set("A1", "=7/0")
        assert s.get("A1") == "#DIV!"


class TestEvaluatorReferences:
    """Tests for reference evaluation per R6 and Task 2.2 acceptance criteria."""

    def test_reference_to_number_cell(self):
        """Reference to number cell contributes its value."""
        s = Sheet()
        s.set("A1", 10)
        s.set("B1", "=A1")
        assert s.get("B1") == 10

    def test_reference_to_empty_cell(self):
        """Reference to empty cell contributes 0."""
        s = Sheet()
        s.set("B1", "=A1+1")
        # A1 is empty, so it contributes 0
        assert s.get("B1") == 1

    def test_reference_to_string_cell(self):
        """Reference to string cell yields '#TYPE!'."""
        s = Sheet()
        s.set("A1", "hello")
        s.set("B1", "=A1")
        assert s.get("B1") == "#TYPE!"

    def test_reference_to_formula_cell(self):
        """Reference to formula cell chains evaluation."""
        s = Sheet()
        s.set("A1", "=1+2")
        s.set("B1", "=A1*3")
        assert s.get("B1") == 9  # (1+2)*3 = 9

    def test_invalid_reference_a01(self):
        """'=A01' (leading zero in REF) yields '#REF!'."""
        s = Sheet()
        s.set("A1", "=A01")
        assert s.get("A1") == "#REF!"

    def test_invalid_reference_a0(self):
        """'=A0' (row 0) yields '#REF!'."""
        s = Sheet()
        s.set("A1", "=A0")
        assert s.get("A1") == "#REF!"

    def test_invalid_reference_a100(self):
        """'=A100' (row > 99) yields '#REF!'."""
        s = Sheet()
        s.set("A1", "=A100")
        assert s.get("A1") == "#REF!"


class TestEvaluatorEdgeCases:
    """Edge cases for Task 2.2."""

    def test_get_on_parse_error_formula(self):
        """get on a #PARSE! formula returns '#PARSE!'."""
        s = Sheet()
        # "=1 < = 2" is #PARSE! per task 2.1
        s.set("A1", "=1 < = 2")
        assert s.get("A1") == "#PARSE!"

    def test_set_reflects_in_subsequent_get(self):
        """After any set, subsequent gets reflect the current sheet."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "=A1")
        assert s.get("B1") == 1
        s.set("A1", 10)
        assert s.get("B1") == 10

    def test_eval_count_stays_zero_for_literals(self):
        """eval_count stays 0 across literal set/get (no formulas evaluated)."""
        s = Sheet()
        s.set("A1", 1)
        s.get("A1")
        assert s.eval_count == 0

    def test_eval_count_increments_for_formula(self):
        """eval_count increments when formula is evaluated."""
        s = Sheet()
        s.set("A1", "=1+2")
        s.get("A1")
        assert s.eval_count == 1
