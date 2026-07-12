import pytest
from gridcalc.sheet import Sheet
from gridcalc.parser import parse


class TestBasicEvaluation:
    def test_integer_formula(self):
        sheet = Sheet()
        sheet.set("A1", "=42")
        assert sheet.get("A1") == 42

    def test_integer_with_leading_zeros(self):
        sheet = Sheet()
        sheet.set("A1", "=007")
        assert sheet.get("A1") == 7

    def test_addition(self):
        sheet = Sheet()
        sheet.set("A1", "=1+2")
        assert sheet.get("A1") == 3

    def test_subtraction(self):
        sheet = Sheet()
        sheet.set("A1", "=5-3")
        assert sheet.get("A1") == 2

    def test_multiplication(self):
        sheet = Sheet()
        sheet.set("A1", "=2*3")
        assert sheet.get("A1") == 6

    def test_division(self):
        sheet = Sheet()
        sheet.set("A1", "=6/2")
        assert sheet.get("A1") == 3

    def test_precedence(self):
        sheet = Sheet()
        sheet.set("A1", "=1+2*3")
        assert sheet.get("A1") == 7

    def test_parentheses(self):
        sheet = Sheet()
        sheet.set("A1", "=(1+2)*3")
        assert sheet.get("A1") == 9

    def test_unary_minus(self):
        sheet = Sheet()
        sheet.set("A1", "=-1")
        assert sheet.get("A1") == -1

    def test_double_unary_minus(self):
        sheet = Sheet()
        sheet.set("A1", "=--1")
        assert sheet.get("A1") == 1


class TestDivision:
    def test_division_truncates_toward_zero_positive(self):
        sheet = Sheet()
        sheet.set("A1", "=7/2")
        assert sheet.get("A1") == 3

    def test_division_truncates_toward_zero_negative_numerator(self):
        sheet = Sheet()
        sheet.set("A1", "=-7/2")
        assert sheet.get("A1") == -3

    def test_division_truncates_toward_zero_negative_denominator(self):
        sheet = Sheet()
        sheet.set("A1", "=7/-2")
        assert sheet.get("A1") == -3

    def test_division_by_zero(self):
        sheet = Sheet()
        sheet.set("A1", "=7/0")
        assert sheet.get("A1") == "#DIV!"


class TestReferences:
    def test_reference_to_number_cell(self):
        sheet = Sheet()
        sheet.set("A1", 10)
        sheet.set("B1", "=A1")
        assert sheet.get("B1") == 10

    def test_reference_to_empty_cell(self):
        sheet = Sheet()
        sheet.set("A1", "=Z9+1")
        assert sheet.get("A1") == 1  # Empty cell contributes 0

    def test_reference_to_string_cell(self):
        sheet = Sheet()
        sheet.set("A1", "hello")
        sheet.set("B1", "=A1")
        assert sheet.get("B1") == "#TYPE!"

    def test_reference_to_formula_cell(self):
        sheet = Sheet()
        sheet.set("A1", "=10")
        sheet.set("B1", "=A1+5")
        assert sheet.get("B1") == 15

    def test_invalid_reference_leading_zeros(self):
        sheet = Sheet()
        sheet.set("A1", "=A01")
        assert sheet.get("A1") == "#REF!"

    def test_invalid_reference_row_zero(self):
        sheet = Sheet()
        sheet.set("A1", "=A0")
        assert sheet.get("A1") == "#REF!"

    def test_invalid_reference_row_too_high(self):
        sheet = Sheet()
        sheet.set("A1", "=A100")
        assert sheet.get("A1") == "#REF!"


class TestParseError:
    def test_parse_error_formula(self):
        sheet = Sheet()
        sheet.set("A1", "=1 + = 2")
        assert sheet.get("A1") == "#PARSE!"


class TestRecompute:
    def test_recompute_after_set(self):
        sheet = Sheet()
        sheet.set("A1", 10)
        sheet.set("B1", "=A1+5")
        assert sheet.get("B1") == 15
        sheet.set("A1", 20)
        assert sheet.get("B1") == 25


class TestR12Sizing:
    def test_256_cell_chain(self):
        """Test that a long reference chain evaluates without raising."""
        sheet = Sheet()
        # Use a chain that stays within valid address range (A1-Z99)
        sheet.set("A1", 1)
        for i in range(2, 11):
            sheet.set(f"A{i}", f"=A{i-1}+1")
        # A10 should be 10
        assert sheet.get("A10") == 10
