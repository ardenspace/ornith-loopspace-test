import pytest

from gridcalc import Sheet
from gridcalc.parser import parse


def is_perr(node):
    return node == ("perr",)


def test_function_calls_compose_as_primaries():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", 2)
    s.set("A2", 3)
    s.set("B2", 4)
    s.set("C1", "=SUM(A1:B2)+1")
    assert s.get("C1") == 11
    s.set("D1", "=-MAX(A1:A2)*2")
    assert s.get("D1") == -6


def test_whitespace_around_colon_is_legal():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", 2)
    s.set("C1", "=SUM(A1 : B1)")
    assert s.get("C1") == 3


@pytest.mark.parametrize(
    "formula",
    [
        "=AVG(A1:A2)",
        "=sum(A1:B2)",
        "=SUM(A1)",
        "=A1:B2",
        "=SUM((A1:B2))",
    ],
)
def test_parse_error_cases(formula):
    s = Sheet()
    s.set("A1", "1")
    s.set("Q1", formula)
    result = s.get("Q1")
    assert result == "#PARSE!"


@pytest.mark.parametrize(
    "formula",
    ["=SUM(B2:A1)", "=SUM(A0:B2)", "=SUM(A1:A100)"],
)
def test_ref_error_cases(formula):
    s = Sheet()
    s.set("Q1", formula)
    assert s.get("Q1") == "#REF!"


def test_visit_order_row_major_first_error_wins():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "hello")  # #TYPE! at position 2 in row-major order
    s.set("A2", "=1/0")  # #DIV! at position 3
    s.set("B2", 5)
    s.set("Q1", "=SUM(A1:B2)")
    assert s.get("Q1") == "#TYPE!"


def test_sum_skips_empty_and_zero_on_all_empty():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", 2)
    # A2, B2 left empty
    s.set("Q1", "=SUM(A1:B2)")
    assert s.get("Q1") == 3
    s.set("Q2", "=SUM(A5:B6)")
    assert s.get("Q2") == 0


def test_min_max_type_error_on_all_empty_and_string_taints():
    s = Sheet()
    s.set("Q1", "=MIN(A5:B6)")
    assert s.get("Q1") == "#TYPE!"
    s.set("Q2", "=MAX(A5:B6)")
    assert s.get("Q2") == "#TYPE!"
    s.set("A1", 1)
    s.set("B1", "oops")
    s.set("Q3", "=MIN(A1:B1)")
    assert s.get("Q3") == "#TYPE!"


def test_min_max_use_non_empty_numeric_contributions():
    s = Sheet()
    s.set("A1", 5)
    s.set("B1", 1)
    s.set("A2", 9)
    s.set("Q1", "=MIN(A1:B2)")
    assert s.get("Q1") == 1
    s.set("Q2", "=MAX(A1:B2)")
    assert s.get("Q2") == 9


def test_count_is_structural_and_never_evaluates():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "text")
    s.set("A2", "=1/0")  # counts even though it's an error-producing formula
    # B2 left empty
    s.set("Q1", "=COUNT(A1:B2)")
    assert s.get("Q1") == 3


def test_count_of_count_self_reference_is_one_not_cycle():
    s = Sheet()
    s.set("A1", "=COUNT(A1:A1)")
    assert s.get("A1") == 1
