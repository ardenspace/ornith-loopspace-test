import pytest
from gridcalc.sheet import Sheet


class TestComparisons:
    def test_equal(self):
        sheet = Sheet()
        sheet.set("A1", "=1=1")
        assert sheet.get("A1") == 1

    def test_not_equal(self):
        sheet = Sheet()
        sheet.set("A1", "=1<>2")
        assert sheet.get("A1") == 1

    def test_less_than(self):
        sheet = Sheet()
        sheet.set("A1", "=1<2")
        assert sheet.get("A1") == 1

    def test_less_equal(self):
        sheet = Sheet()
        sheet.set("A1", "=1<=2")
        assert sheet.get("A1") == 1

    def test_greater_than(self):
        sheet = Sheet()
        sheet.set("A1", "=2>1")
        assert sheet.get("A1") == 1

    def test_greater_equal(self):
        sheet = Sheet()
        sheet.set("A1", "=2>=1")
        assert sheet.get("A1") == 1

    def test_left_associative_comparisons(self):
        """=1<2<3 is (1<2)<3 = 1<3 = 1"""
        sheet = Sheet()
        sheet.set("A1", "=1<2<3")
        assert sheet.get("A1") == 1

    def test_comparison_with_string_operand(self):
        sheet = Sheet()
        sheet.set("A1", "hello")
        sheet.set("B1", "=A1<2")
        assert sheet.get("B1") == "#TYPE!"


class TestErrorPropagation:
    def test_parse_error_propagates(self):
        sheet = Sheet()
        sheet.set("A1", "=1 + = 2")
        assert sheet.get("A1") == "#PARSE!"

    def test_ref_error_propagates(self):
        sheet = Sheet()
        sheet.set("A1", "=A01+1")
        assert sheet.get("A1") == "#REF!"

    def test_type_error_propagates(self):
        sheet = Sheet()
        sheet.set("A1", "hello")
        sheet.set("B1", "=A1+1")
        assert sheet.get("B1") == "#TYPE!"

    def test_div_error_propagates(self):
        sheet = Sheet()
        sheet.set("A1", "=1/0")
        assert sheet.get("A1") == "#DIV!"

    def test_left_most_error_wins(self):
        """With B1 and C1 both errors, =A1+B1*C1 returns B1's error."""
        sheet = Sheet()
        sheet.set("A1", 1)
        sheet.set("B1", "hello")  # Will cause #TYPE!
        sheet.set("C1", "world")  # Will cause #TYPE!
        sheet.set("D1", "=A1+B1*C1")
        # B1 is textually left of C1 in the formula, so B1's error wins
        assert sheet.get("D1") == "#TYPE!"

    def test_short_circuit_division(self):
        """=1/0+A1 is #DIV! whatever A1 holds."""
        sheet = Sheet()
        sheet.set("A1", "hello")  # Would cause #TYPE! if evaluated
        sheet.set("B1", "=1/0+A1")
        assert sheet.get("B1") == "#DIV!"
