from gridcalc import Sheet


def _is_int(value):
    return type(value) is int


def test_comparison_equals_yields_int_one():
    sheet = Sheet()
    sheet.set("A1", "=1=1")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_equals_yields_int_zero():
    sheet = Sheet()
    sheet.set("A1", "=1=2")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_not_equals_yields_int_one():
    sheet = Sheet()
    sheet.set("A1", "=1<>2")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_not_equals_yields_int_zero():
    sheet = Sheet()
    sheet.set("A1", "=2<>2")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_less_than_yields_int_one():
    sheet = Sheet()
    sheet.set("A1", "=1<2")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_less_than_yields_int_zero():
    sheet = Sheet()
    sheet.set("A1", "=2<1")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_less_equal_yields_int_one():
    sheet = Sheet()
    sheet.set("A1", "=1<=1")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_less_equal_yields_int_zero():
    sheet = Sheet()
    sheet.set("A1", "=2<=1")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_greater_than_yields_int_one():
    sheet = Sheet()
    sheet.set("A1", "=2>1")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_greater_than_yields_int_zero():
    sheet = Sheet()
    sheet.set("A1", "=1>2")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_greater_equal_yields_int_one():
    sheet = Sheet()
    sheet.set("A1", "=2>=2")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_greater_equal_yields_int_zero():
    sheet = Sheet()
    sheet.set("A1", "=1>=2")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_chained_less_than():
    sheet = Sheet()
    sheet.set("A1", "=1<2<3")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_chained_less_than_false():
    sheet = Sheet()
    sheet.set("A1", "=1<2<1")
    result = sheet.get("A1")
    assert result == 0
    assert _is_int(result)


def test_comparison_arithmetic_then_comparison():
    sheet = Sheet()
    sheet.set("A1", "=1+1=2")
    result = sheet.get("A1")
    assert result == 1
    assert _is_int(result)


def test_comparison_with_string_operand_returns_type_error():
    sheet = Sheet()
    sheet.set("A1", "hello")
    sheet.set("B1", "=A1=1")
    result = sheet.get("B1")
    assert result == "#TYPE!"


def test_comparison_with_string_operand_returns_type_error_greater():
    sheet = Sheet()
    sheet.set("A1", "hello")
    sheet.set("B1", "=A1>1")
    result = sheet.get("B1")
    assert result == "#TYPE!"


def test_error_parse_propagation():
    sheet = Sheet()
    sheet.set("A1", "=1 $ 2")
    result = sheet.get("A1")
    assert result == "#PARSE!"


def test_error_ref_propagation():
    sheet = Sheet()
    sheet.set("A1", "=A0")
    result = sheet.get("A1")
    assert result == "#REF!"


def test_error_div_propagation():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    result = sheet.get("A1")
    assert result == "#DIV!"


def test_error_type_propagation():
    sheet = Sheet()
    sheet.set("A1", "text")
    sheet.set("B1", "=A1+1")
    result = sheet.get("B1")
    assert result == "#TYPE!"


def test_leftmost_error_wins_in_addition():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=A0")
    sheet.set("D1", "=A1+B1*C1")
    result = sheet.get("D1")
    assert result == "#DIV!"


def test_leftmost_error_wins_in_multiplication():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=A0")
    sheet.set("C1", "=A1*B1")
    result = sheet.get("C1")
    assert result == "#DIV!"


def test_shortcircuit_div_zero_first():
    sheet = Sheet()
    sheet.set("A1", "=1/0+A1")
    result = sheet.get("A1")
    assert result == "#DIV!"


def test_shortcircuit_div_zero_first_with_valid_second_operand():
    sheet = Sheet()
    sheet.set("B1", 42)
    sheet.set("A1", "=1/0+B1")
    result = sheet.get("A1")
    assert result == "#DIV!"


def test_error_in_comparison_operand_propagates():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=A1=1")
    result = sheet.get("B1")
    assert result == "#DIV!"


def test_parse_error_in_reference_propagates():
    sheet = Sheet()
    sheet.set("A1", "=1 $ 2")
    sheet.set("B1", "=A1+1")
    result = sheet.get("B1")
    assert result == "#PARSE!"


def test_ref_error_in_reference_propagates():
    sheet = Sheet()
    sheet.set("A1", "=A0")
    sheet.set("B1", "=A1+1")
    result = sheet.get("B1")
    assert result == "#REF!"


def test_all_error_types_are_strings():
    sheet = Sheet()

    sheet.set("A1", "=1 $ 2")
    assert sheet.get("A1") == "#PARSE!"
    assert type(sheet.get("A1")) is str

    sheet.set("B1", "=A0")
    assert sheet.get("B1") == "#REF!"
    assert type(sheet.get("B1")) is str

    sheet.set("C1", "text")
    sheet.set("D1", "=C1")
    assert sheet.get("D1") == "#TYPE!"
    assert type(sheet.get("D1")) is str

    sheet.set("E1", "=1/0")
    assert sheet.get("E1") == "#DIV!"
    assert type(sheet.get("E1")) is str
