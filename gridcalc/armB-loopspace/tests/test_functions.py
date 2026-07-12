import pytest
from gridcalc.sheet import Sheet
from gridcalc.parser import parse


class TestFunctionGrammar:
    def test_sum_basic(self):
        """=SUM(A1:B2) with A1=1, A2=2, B1=3, B2=4 should be 10."""
        sheet = Sheet()
        sheet.set("A1", 1)
        sheet.set("A2", 2)
        sheet.set("B1", 3)
        sheet.set("B2", 4)
        sheet.set("C1", "=SUM(A1:B2)")
        assert sheet.get("C1") == 10

    def test_sum_with_whitespace(self):
        """=SUM(A1 : B2) should work (whitespace around : is legal)."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", 10)
        sheet.set("C1", "=SUM(A1 : B1)")
        assert sheet.get("C1") == 15

    def test_sum_composes(self):
        """=SUM(A1:B2)+1 should evaluate."""
        sheet = Sheet()
        sheet.set("A1", 1)
        sheet.set("B1", 2)
        sheet.set("C1", "=SUM(A1:B1)+1")
        assert sheet.get("C1") == 4

    def test_unary_minus_max_composes(self):
        """=-MAX(A1:A2)*2 should evaluate to -20."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("A2", 10)
        sheet.set("B1", "=-MAX(A1:A2)*2")
        assert sheet.get("B1") == -20

    def test_sum_multiply_composes(self):
        """=SUM(A1:B1)*2 should evaluate."""
        sheet = Sheet()
        sheet.set("A1", 3)
        sheet.set("B1", 4)
        sheet.set("C1", "=SUM(A1:B1)*2")
        assert sheet.get("C1") == 14

    def test_max_basic(self):
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", 10)
        sheet.set("C1", "=MAX(A1:B1)")
        assert sheet.get("C1") == 10

    def test_min_basic(self):
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", 10)
        sheet.set("C1", "=MIN(A1:B1)")
        assert sheet.get("C1") == 5

    def test_count_basic(self):
        """COUNT counts non-empty cells without evaluating them."""
        sheet = Sheet()
        sheet.set("A1", 1)
        sheet.set("B1", "hello")
        sheet.set("C1", "=COUNT(A1:B1)")
        assert sheet.get("C1") == 2

    def test_count_with_formula(self):
        """A1 holding =COUNT(A1:A1) is 1."""
        sheet = Sheet()
        sheet.set("A1", "=COUNT(A1:A1)")
        assert sheet.get("A1") == 1


class TestFunctionErrors:
    def test_unknown_function(self):
        assert parse("AVG(A1:A2)") == "#PARSE!"

    def test_lowercase_function(self):
        assert parse("sum(A1:B2)") == "#PARSE!"

    def test_sum_without_colon(self):
        """=SUM(A1) is #PARSE! (no colon in argument)."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", "=SUM(A1)")
        assert sheet.get("B1") == "#PARSE!"

    def test_range_outside_function(self):
        """=A1:B2 outside a function is #PARSE!."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", 10)
        sheet.set("C1", "=A1:B1")
        assert sheet.get("C1") == "#PARSE!"

    def test_sum_double_parens(self):
        """=SUM((A1:B2)) is #PARSE!."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", 10)
        sheet.set("C1", "=SUM((A1:B1))")
        assert sheet.get("C1") == "#PARSE!"

    def test_misordered_range(self):
        """=SUM(B2:A1) is #REF! (B2 is below/right of A1)."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B2", 10)
        sheet.set("C1", "=SUM(B2:A1)")
        assert sheet.get("C1") == "#REF!"

    def test_out_of_grid_range(self):
        """=SUM(A0:B2) is #REF! (A0 is invalid)."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", 10)
        sheet.set("C1", "=SUM(A0:B1)")
        assert sheet.get("C1") == "#REF!"

    def test_out_of_grid_range_row_too_high(self):
        """=SUM(A1:A100) is #REF! (row 100 is invalid)."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", "=SUM(A1:A100)")
        assert sheet.get("B1") == "#REF!"


class TestFunctionSemantics:
    def test_sum_skips_empty(self):
        """SUM skips empty cells and is 0 on all-empty range."""
        sheet = Sheet()
        sheet.set("A1", 5)
        # B1 is empty (not set), C1 references A1:B1
        sheet.set("C1", "=SUM(A1:B1)")
        assert sheet.get("C1") == 5

    def test_sum_all_empty(self):
        """SUM on all-empty range is 0."""
        sheet = Sheet()
        # C1 references A1:B1, both empty
        sheet.set("C1", "=SUM(A1:B1)")
        assert sheet.get("C1") == 0

    def test_min_max_all_empty(self):
        """MIN/MAX on all-empty range is #TYPE!."""
        sheet = Sheet()
        # C1 references A1:B1, both empty
        sheet.set("C1", "=MIN(A1:B1)")
        assert sheet.get("C1") == "#TYPE!"
        sheet.set("D1", "=MAX(A1:B1)")
        assert sheet.get("D1") == "#TYPE!"

    def test_string_makes_sum_type_error(self):
        """Any string cell makes SUM #TYPE!."""
        sheet = Sheet()
        sheet.set("A1", 5)
        sheet.set("B1", "hello")
        sheet.set("C1", "=SUM(A1:B1)")
        assert sheet.get("C1") == "#TYPE!"

    def test_row_major_visit_order(self):
        """Visit order is row-major: A1, B1, A2, B2 for A1:B2."""
        sheet = Sheet()
        sheet.set("A1", 1)
        sheet.set("B1", "error")  # #TYPE! should appear first
        sheet.set("A2", 3)
        sheet.set("B2", 4)
        sheet.set("C1", "=SUM(A1:B2)")
        # B1 is row-major second (after A1), so its #TYPE! should win
        assert sheet.get("C1") == "#TYPE!"
