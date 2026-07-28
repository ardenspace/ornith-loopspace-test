from gridcalc import Sheet


def test_all_six_comparisons_yield_ints():
    s = Sheet()
    s.set("A1", "=1<2<3")
    assert s.get("A1") == 1
    s.set("A2", "=1+1=2")
    assert s.get("A2") == 1
    s.set("A3", "=2<>2")
    assert s.get("A3") == 0
    s.set("A4", "=3>2")
    assert s.get("A4") == 1
    s.set("A5", "=3>=3")
    assert s.get("A5") == 1
    s.set("A6", "=2<=1")
    assert s.get("A6") == 0


def test_comparison_with_string_operand_yields_type_error():
    s = Sheet()
    s.set("A1", "hi")
    s.set("B1", "=A1<1")
    assert s.get("B1") == "#TYPE!"


def test_error_strings_are_exact_set():
    s = Sheet()
    s.set("A1", "=a1")
    assert s.get("A1") == "#PARSE!"
    s.set("A2", "=A100")
    assert s.get("A2") == "#REF!"
    s.set("A3", "hello")
    s.set("A4", "=A3")
    assert s.get("A4") == "#TYPE!"
    s.set("A5", "=1/0")
    assert s.get("A5") == "#DIV!"


def test_leftmost_error_wins_among_several_operands():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "hello")  # -> #TYPE! when read numerically
    s.set("C1", "=1/0")  # -> #DIV!
    s.set("D1", "=A1+B1*C1")
    assert s.get("D1") == "#TYPE!"


def test_short_circuit_at_value_level():
    s = Sheet()
    s.set("Y1", "=1+1")
    s.set("X1", "=1/0+Y1")
    assert s.get("X1") == "#DIV!"
