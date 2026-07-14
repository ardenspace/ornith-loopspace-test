from gridcalc import Sheet


def test_arithmetic_basic_operations():
    sheet = Sheet()
    sheet.set("A1", "=1+2*3")
    assert sheet.get("A1") == 7
    assert sheet.eval_count > 0


def test_arithmetic_parentheses_change_result():
    sheet = Sheet()
    sheet.set("A1", "=(1+2)*3")
    assert sheet.get("A1") == 9


def test_arithmetic_double_unary_minus():
    sheet = Sheet()
    sheet.set("A1", "=--1")
    assert sheet.get("A1") == 1


def test_arithmetic_binary_minus_after_binary_plus():
    sheet = Sheet()
    sheet.set("A1", "=2--3")
    assert sheet.get("A1") == 5


def test_arithmetic_leading_zero_literal():
    sheet = Sheet()
    sheet.set("A1", "=007")
    assert sheet.get("A1") == 7


def test_division_truncates_toward_zero_positive():
    sheet = Sheet()
    sheet.set("A1", "=7/2")
    assert sheet.get("A1") == 3


def test_division_truncates_toward_zero_negative_numerator():
    sheet = Sheet()
    sheet.set("A1", "=-7/2")
    assert sheet.get("A1") == -3


def test_division_truncates_toward_zero_negative_denominator():
    sheet = Sheet()
    sheet.set("A1", "=7/-2")
    assert sheet.get("A1") == -3


def test_division_by_zero_returns_error():
    sheet = Sheet()
    sheet.set("A1", "=7/0")
    assert sheet.get("A1") == "#DIV!"


def test_reference_number_cell_contributes_value():
    sheet = Sheet()
    sheet.set("B1", 42)
    sheet.set("A1", "=B1+1")
    assert sheet.get("A1") == 43


def test_reference_empty_cell_contributes_zero():
    sheet = Sheet()
    sheet.set("A1", "=Z9+1")
    assert sheet.get("A1") == 1


def test_reference_string_cell_yields_type_error():
    sheet = Sheet()
    sheet.set("A1", "hi")
    sheet.set("B1", "=A1")
    assert sheet.get("B1") == "#TYPE!"


def test_reference_formula_cell_chains():
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=A1+5")
    sheet.set("C1", "=B1*2")
    assert sheet.get("C1") == 30


def test_reference_invalid_leading_zero_ref():
    sheet = Sheet()
    sheet.set("A1", "=A01")
    assert sheet.get("A1") == "#REF!"


def test_reference_invalid_zero_row():
    sheet = Sheet()
    sheet.set("A1", "=A0")
    assert sheet.get("A1") == "#REF!"


def test_reference_invalid_row_out_of_range():
    sheet = Sheet()
    sheet.set("A1", "=A100")
    assert sheet.get("A1") == "#REF!"


def test_get_after_set_reflects_current_sheet():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=A1")
    assert sheet.get("B1") == 1
    sheet.set("A1", 100)
    assert sheet.get("B1") == 100


def test_get_on_parse_error_formula_returns_parse_error():
    sheet = Sheet()
    sheet.set("A1", "=1 $ 2")
    assert sheet.get("A1") == "#PARSE!"


def test_256_formula_cell_chain_evaluates():
    sheet = Sheet()
    sheet.set("A1", "=1")
    prev_addr = "A1"
    for i in range(2, 257):
        col_idx = (i - 1) // 99
        row = (i - 1) % 99 + 1
        col = chr(ord("A") + col_idx)
        addr = f"{col}{row}"
        sheet.set(addr, f"={prev_addr}+1")
        prev_addr = addr
    col_idx = 255 // 99
    row = 255 % 99 + 1
    last_addr = f"{chr(ord('A') + col_idx)}{row}"
    assert sheet.get(last_addr) == 256
