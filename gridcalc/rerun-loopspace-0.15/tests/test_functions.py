"""Task 3.1: Function grammar + SUM/MIN/MAX/COUNT."""
import pytest
from gridcalc import Sheet
from gridcalc.parser import parse, ParseError


class TestFunctionGrammar:
    """Tests for function grammar per R3 and Task 3.1 acceptance criteria."""

    def test_sum_with_range(self):
        """'=SUM(A1:B2)' parses."""
        # Just verify it parses (doesn't raise ParseError)
        try:
            parse("SUM(A1:B2)")
        except ParseError:
            pytest.fail("SUM(A1:B2) should parse")

    def test_sum_composes_with_arithmetic(self):
        """'=SUM(A1:B2)+1' parses."""
        try:
            parse("SUM(A1:B2)+1")
        except ParseError:
            pytest.fail("SUM(A1:B2)+1 should parse")

    def test_max_composes_with_unary_minus(self):
        """'=-MAX(A1:A2)*2' parses."""
        try:
            parse("-MAX(A1:A2)*2")
        except ParseError:
            pytest.fail("-MAX(A1:A2)*2 should parse")

    def test_whitespace_around_colon(self):
        """'=SUM(A1 : B2)' parses (whitespace around ':' is legal)."""
        try:
            parse("SUM(A1 : B2)")
        except ParseError:
            pytest.fail("SUM(A1 : B2) should parse")

    def test_unknown_function_name_parses_to_error(self):
        """'=AVG(A1:A2)' yields #PARSE!."""
        with pytest.raises(ParseError):
            parse("AVG(A1:A2)")

    def test_lowercase_function_parses_to_error(self):
        """'=sum(A1:B2)' yields #PARSE!."""
        with pytest.raises(ParseError):
            parse("sum(A1:B2)")

    def test_sum_without_colon_parses_to_error(self):
        """'=SUM(A1)' yields #PARSE!."""
        with pytest.raises(ParseError):
            parse("SUM(A1)")

    def test_range_outside_function_parses_to_error(self):
        """'=A1:B2' yields #PARSE!."""
        with pytest.raises(ParseError):
            parse("A1:B2")

    def test_sum_with_nested_parens_parses_to_error(self):
        """'=SUM((A1:B2))' yields #PARSE!."""
        with pytest.raises(ParseError):
            parse("SUM((A1:B2))")


class TestFunctionEvaluation:
    """Tests for function evaluation per R7, R8 and Task 3.1 acceptance criteria."""

    def test_sum_basic(self):
        """SUM adds numeric contributions."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", 2)
        s.set("B1", 3)
        s.set("B2", 4)
        s.set("C1", "=SUM(A1:B2)")
        assert s.get("C1") == 10  # 1+2+3+4

    def test_sum_skips_empty_cells(self):
        """SUM skips empty cells and is 0 on an all-empty range."""
        s = Sheet()
        s.set("A1", 1)
        # A2, B1, B2 are empty
        s.set("C1", "=SUM(A1:B2)")
        assert s.get("C1") == 1

        s2 = Sheet()
        # All empty
        s2.set("C1", "=SUM(A1:B2)")
        assert s2.get("C1") == 0

    def test_min_basic(self):
        """MIN takes the least numeric contribution."""
        s = Sheet()
        s.set("A1", 5)
        s.set("A2", 2)
        s.set("B1", 8)
        s.set("B2", 1)
        s.set("C1", "=MIN(A1:B2)")
        assert s.get("C1") == 1

    def test_max_basic(self):
        """MAX takes the greatest numeric contribution."""
        s = Sheet()
        s.set("A1", 5)
        s.set("A2", 2)
        s.set("B1", 8)
        s.set("B2", 1)
        s.set("C1", "=MAX(A1:B2)")
        assert s.get("C1") == 8

    def test_min_all_empty_range(self):
        """MIN on an all-empty range is '#TYPE!'."""
        s = Sheet()
        s.set("C1", "=MIN(A1:B2)")
        assert s.get("C1") == "#TYPE!"

    def test_max_all_empty_range(self):
        """MAX on an all-empty range is '#TYPE!'."""
        s = Sheet()
        s.set("C1", "=MAX(A1:B2)")
        assert s.get("C1") == "#TYPE!"

    def test_sum_with_string_cell(self):
        """Any string cell makes SUM '#TYPE!'."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "hello")
        s.set("B1", 3)
        s.set("B2", 4)
        s.set("C1", "=SUM(A1:B2)")
        assert s.get("C1") == "#TYPE!"

    def test_min_with_string_cell(self):
        """Any string cell makes MIN '#TYPE!'."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "hello")
        s.set("B1", 3)
        s.set("B2", 4)
        s.set("C1", "=MIN(A1:B2)")
        assert s.get("C1") == "#TYPE!"

    def test_max_with_string_cell(self):
        """Any string cell makes MAX '#TYPE!'."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "hello")
        s.set("B1", 3)
        s.set("B2", 4)
        s.set("C1", "=MAX(A1:B2)")
        assert s.get("C1") == "#TYPE!"

    def test_count_basic(self):
        """COUNT counts non-empty cells."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "hello")
        s.set("B1", "=1+2")
        # B2 is empty
        s.set("C1", "=COUNT(A1:B2)")
        assert s.get("C1") == 3  # A1, A2, B1 are non-empty

    def test_count_with_formula_cell(self):
        """COUNT counts formula cells without evaluating them."""
        s = Sheet()
        s.set("A1", "=1+2")
        s.set("B1", "=3+4")
        s.set("C1", "=COUNT(A1:B1)")
        assert s.get("C1") == 2

    def test_count_self_reference(self):
        """A1 holding '=COUNT(A1:A1)' is 1."""
        s = Sheet()
        s.set("A1", "=COUNT(A1:A1)")
        assert s.get("A1") == 1

    def test_mis_ordered_range_yields_ref(self):
        """'=SUM(B2:A1)' (mis-ordered) yields '#REF!'."""
        s = Sheet()
        s.set("C1", "=SUM(B2:A1)")
        assert s.get("C1") == "#REF!"

    def test_range_with_out_of_grid_endpoint_yields_ref(self):
        """'=SUM(A0:B2)' (out-of-grid) yields '#REF!'."""
        s = Sheet()
        s.set("C1", "=SUM(A0:B2)")
        assert s.get("C1") == "#REF!"

    def test_range_with_out_of_grid_endpoint_yields_ref_row_100(self):
        """'=SUM(A1:A100)' (row > 99) yields '#REF!'."""
        s = Sheet()
        s.set("C1", "=SUM(A1:A100)")
        assert s.get("C1") == "#REF!"

    def test_first_error_in_visit_order_wins(self):
        """First error in visit order wins at the value level."""
        s = Sheet()
        s.set("A1", 1)
        s.set("A2", "hello")  # #TYPE!
        s.set("B1", "=1/0")  # #DIV!
        s.set("B2", 4)
        s.set("C1", "=SUM(A1:B2)")
        # Visit order: A1, B1, A2, B2 — B1's #DIV! is first error
        assert s.get("C1") == "#DIV!"
