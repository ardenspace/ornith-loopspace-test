
from gridcalc import Sheet
from gridcalc.parser import FuncCall, Range, Ref, parse


# --- Parser: function calls as primaries ---

def test_parse_sum_function_call():
    ast = parse("=SUM(A1:B2)")
    assert ast == FuncCall(
        name="SUM",
        arg=Range(start=Ref(name="A1"), end=Ref(name="B2")),
    )


def test_parse_min_function_call():
    ast = parse("=MIN(A1:B2)")
    assert ast == FuncCall(
        name="MIN",
        arg=Range(start=Ref(name="A1"), end=Ref(name="B2")),
    )


def test_parse_max_function_call():
    ast = parse("=MAX(A1:B2)")
    assert ast == FuncCall(
        name="MAX",
        arg=Range(start=Ref(name="A1"), end=Ref(name="B2")),
    )


def test_parse_count_function_call():
    ast = parse("=COUNT(A1:B2)")
    assert ast == FuncCall(
        name="COUNT",
        arg=Range(start=Ref(name="A1"), end=Ref(name="B2")),
    )


def test_parse_function_call_with_whitespace_around_colon():
    ast = parse("=SUM(A1 : B2)")
    assert ast == FuncCall(
        name="SUM",
        arg=Range(start=Ref(name="A1"), end=Ref(name="B2")),
    )


def test_parse_function_call_composes_with_arithmetic():
    ast = parse("=SUM(A1:B2)+1")
    from gridcalc.parser import BinaryOp, IntLiteral
    assert ast == BinaryOp(
        op="+",
        left=FuncCall(
            name="SUM",
            arg=Range(start=Ref(name="A1"), end=Ref(name="B2")),
        ),
        right=IntLiteral(text="1", value=1),
    )


def test_parse_function_call_composes_with_unary_minus_and_multiply():
    ast = parse("=-MAX(A1:A2)*2")
    from gridcalc.parser import BinaryOp, IntLiteral, UnaryOp
    assert ast == BinaryOp(
        op="*",
        left=UnaryOp(op="-", operand=FuncCall(
            name="MAX",
            arg=Range(start=Ref(name="A1"), end=Ref(name="A2")),
        )),
        right=IntLiteral(text="2", value=2),
    )


# --- Parser: rejection cases ---

def test_parse_unknown_function_rejected():
    assert parse("=AVG(A1:A2)") == "#PARSE!"


def test_parse_lowercase_function_rejected():
    assert parse("=sum(A1:B2)") == "#PARSE!"


def test_parse_single_ref_inside_function_rejected():
    assert parse("=SUM(A1)") == "#PARSE!"


def test_parse_standalone_range_rejected():
    assert parse("=A1:B2") == "#PARSE!"


def test_parse_nested_parens_around_range_rejected():
    assert parse("=SUM((A1:B2))") == "#PARSE!"


def test_parse_function_with_extra_arg_rejected():
    assert parse("=SUM(A1:B2,C1:D2)") == "#PARSE!"


def test_parse_function_with_no_colon_rejected():
    assert parse("=SUM(A1B2)") == "#PARSE!"


# --- Evaluator: SUM ---

def test_eval_sum_basic():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("A2", 3)
    sheet.set("B2", 4)
    sheet.set("C1", "=SUM(A1:B2)")
    assert sheet.get("C1") == 10


def test_eval_sum_skips_empty_cells():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("C1", "=SUM(A1:B1)")
    assert sheet.get("C1") == 3


def test_eval_sum_all_empty_returns_zero():
    sheet = Sheet()
    sheet.set("C1", "=SUM(A1:B2)")
    assert sheet.get("C1") == 0


def test_eval_sum_with_string_cell_returns_type_error():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "hello")
    sheet.set("A2", 3)
    sheet.set("B2", "=SUM(A1:B2)")
    assert sheet.get("B2") == "#TYPE!"


def test_eval_sum_row_major_first_error_wins():
    """B1 has #TYPE! (string), A2 has #DIV! — row-major visits B1 first."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "text")
    sheet.set("A2", 1)
    sheet.set("B2", 0)
    sheet.set("C1", "=SUM(A1:B2)")
    assert sheet.get("C1") == "#TYPE!"


# --- Evaluator: MIN ---

def test_eval_min_basic():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", 3)
    sheet.set("A2", 8)
    sheet.set("B2", 1)
    sheet.set("C1", "=MIN(A1:B2)")
    assert sheet.get("C1") == 1


def test_eval_min_skips_empty_cells():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", 3)
    sheet.set("C1", "=MIN(A1:B1)")
    assert sheet.get("C1") == 3


def test_eval_min_all_empty_returns_type_error():
    sheet = Sheet()
    sheet.set("C1", "=MIN(A1:B2)")
    assert sheet.get("C1") == "#TYPE!"


def test_eval_min_with_string_cell_returns_type_error():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "hello")
    sheet.set("C1", "=MIN(A1:B1)")
    assert sheet.get("C1") == "#TYPE!"


def test_eval_min_row_major_first_error_wins():
    """B1 has #TYPE! (string), A2 has #DIV! — row-major visits B1 first."""
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "text")
    sheet.set("A2", 1)
    sheet.set("B2", 0)
    sheet.set("C1", "=MIN(A1:B2)")
    assert sheet.get("C1") == "#TYPE!"


# --- Evaluator: MAX ---

def test_eval_max_basic():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", 3)
    sheet.set("A2", 8)
    sheet.set("B2", 1)
    sheet.set("C1", "=MAX(A1:B2)")
    assert sheet.get("C1") == 8


def test_eval_max_skips_empty_cells():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", 3)
    sheet.set("C1", "=MAX(A1:B1)")
    assert sheet.get("C1") == 5


def test_eval_max_all_empty_returns_type_error():
    sheet = Sheet()
    sheet.set("C1", "=MAX(A1:B2)")
    assert sheet.get("C1") == "#TYPE!"


def test_eval_max_with_string_cell_returns_type_error():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "hello")
    sheet.set("C1", "=MAX(A1:B1)")
    assert sheet.get("C1") == "#TYPE!"


def test_eval_max_row_major_first_error_wins():
    """B1 has #TYPE! (string), A2 has #DIV! — row-major visits B1 first."""
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "text")
    sheet.set("A2", 1)
    sheet.set("B2", 0)
    sheet.set("C1", "=MAX(A1:B2)")
    assert sheet.get("C1") == "#TYPE!"


# --- Evaluator: COUNT ---

def test_eval_count_basic():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("A2", 3)
    sheet.set("B2", 4)
    sheet.set("C1", "=COUNT(A1:B2)")
    assert sheet.get("C1") == 4


def test_eval_count_skips_empty_cells():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("C1", "=COUNT(A1:B1)")
    assert sheet.get("C1") == 2


def test_eval_count_all_empty_returns_zero():
    sheet = Sheet()
    sheet.set("A1", "=COUNT(C1:D2)")
    assert sheet.get("A1") == 0


def test_eval_count_counts_string_cells():
    sheet = Sheet()
    sheet.set("A1", "hello")
    sheet.set("B1", "world")
    sheet.set("C1", "=COUNT(A1:B1)")
    assert sheet.get("C1") == 2


def test_eval_count_counts_formula_cells_without_evaluating():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=99")
    sheet.set("C1", "=COUNT(A1:B1)")
    assert sheet.get("C1") == 2


def test_eval_count_self_reference_returns_one():
    """A1 = COUNT(A1:A1) should be 1 (counts itself without evaluating)."""
    sheet = Sheet()
    sheet.set("A1", "=COUNT(A1:A1)")
    assert sheet.get("A1") == 1


def test_eval_count_invalid_range_returns_ref():
    sheet = Sheet()
    sheet.set("A1", "=COUNT(B2:A1)")
    assert sheet.get("A1") == "#REF!"


def test_eval_count_out_of_grid_returns_ref():
    sheet = Sheet()
    sheet.set("A1", "=COUNT(A0:B2)")
    assert sheet.get("A1") == "#REF!"

    sheet2 = Sheet()
    sheet2.set("A1", "=COUNT(A1:A100)")
    assert sheet2.get("A1") == "#REF!"


# --- Evaluator: range validation ---

def test_eval_range_mis_ordered_columns_returns_ref():
    sheet = Sheet()
    sheet.set("A1", "=SUM(B2:A1)")
    assert sheet.get("A1") == "#REF!"


def test_eval_range_mis_ordered_rows_returns_ref():
    sheet = Sheet()
    sheet.set("A1", "=SUM(A2:B1)")
    assert sheet.get("A1") == "#REF!"


def test_eval_range_out_of_grid_row_zero_returns_ref():
    sheet = Sheet()
    sheet.set("A1", "=SUM(A0:B2)")
    assert sheet.get("A1") == "#REF!"


def test_eval_range_out_of_grid_row_100_returns_ref():
    sheet = Sheet()
    sheet.set("A1", "=SUM(A1:A100)")
    assert sheet.get("A1") == "#REF!"


def test_eval_range_single_cell_is_valid():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "=SUM(A1:A1)")
    assert sheet.get("B1") == 5


def test_eval_sum_composes_with_arithmetic():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("C1", "=SUM(A1:B1)+10")
    assert sheet.get("C1") == 13


def test_eval_sum_composes_with_unary_minus_and_multiply():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", 3)
    sheet.set("C1", "=-MAX(A1:B1)*2")
    assert sheet.get("C1") == -10


def test_eval_sum_with_division_error_in_range():
    """A2 has #DIV! — SUM should propagate #DIV! (not #TYPE!)."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("A2", 1)
    sheet.set("B2", 0)
    sheet.set("C1", "=SUM(A1:B2)/0")
    assert sheet.get("C1") == "#DIV!"


def test_eval_min_max_row_major_multi_error_across_columns():
    """
    A1=1, B1=#TYPE! (string), C1=10
    A2=100, B2=#DIV! (0 divisor formula), C2=200
    Row-major visits: A1, B1, C1, A2, B2, C2
    For MIN: B1 (#TYPE!) is first error encountered.
    """
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "text")
    sheet.set("C1", 10)
    sheet.set("A2", 100)
    sheet.set("B2", "=1/0")
    sheet.set("C2", 200)
    sheet.set("D1", "=MIN(A1:C2)")
    assert sheet.get("D1") == "#TYPE!"


def test_eval_sum_row_major_multi_error_across_columns():
    """
    A1=1, B1=#TYPE! (string), C1=10
    A2=100, B2=#DIV!, C2=200
    Row-major visits: A1, B1, C1, A2, B2, C2
    For SUM: B1 (#TYPE!) is first error encountered.
    """
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "text")
    sheet.set("C1", 10)
    sheet.set("A2", 100)
    sheet.set("B2", "=1/0")
    sheet.set("C2", 200)
    sheet.set("D1", "=SUM(A1:C2)")
    assert sheet.get("D1") == "#TYPE!"


def test_eval_min_row_major_multi_error_div_before_type():
    """
    A1=#DIV! (formula), B1=5
    Row-major visits A1 first → #DIV! wins for MIN.
    """
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", 5)
    sheet.set("C1", "=MIN(A1:B1)")
    assert sheet.get("C1") == "#DIV!"


def test_eval_range_inverted_columns_returns_ref():
    """B1:A2 — start col > end col, regardless of row ordering."""
    sheet = Sheet()
    sheet.set("A1", "=SUM(B1:A2)")
    assert sheet.get("A1") == "#REF!"


def test_eval_max_row_major_multi_error_across_columns():
    """
    A1=1, B1=#TYPE! (string), C1=10
    A2=100, B2=#DIV! (0 divisor formula), C2=200
    Row-major visits: A1, B1, C1, A2, B2, C2
    For MAX: B1 (#TYPE!) is first error encountered.
    """
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "text")
    sheet.set("C1", 10)
    sheet.set("A2", 100)
    sheet.set("B2", "=1/0")
    sheet.set("C2", 200)
    sheet.set("D1", "=MAX(A1:C2)")
    assert sheet.get("D1") == "#TYPE!"
