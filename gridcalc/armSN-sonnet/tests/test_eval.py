from gridcalc import Sheet


def ev(formula):
    s = Sheet()
    s.set("A1", "=" + formula)
    return s.get("A1")


def test_arithmetic():
    assert ev("1+2*3") == 7
    assert ev("(1+2)*3") == 9
    assert ev("--1") == 1
    assert ev("2--3") == 5
    assert ev("007") == 7


def test_division_truncates_toward_zero():
    assert ev("7/2") == 3
    assert ev("-7/2") == -3
    assert ev("7/-2") == -3
    assert ev("7/0") == "#DIV!"


def test_reference_reads_numeric_value():
    s = Sheet()
    s.set("A1", 5)
    s.set("B1", "=A1+1")
    assert s.get("B1") == 6


def test_empty_reference_contributes_zero():
    s = Sheet()
    s.set("F1", "=Z9+1")
    assert s.get("F1") == 1


def test_string_reference_yields_type_error():
    s = Sheet()
    s.set("A1", "hi")
    s.set("B1", "=A1")
    assert s.get("B1") == "#TYPE!"


def test_formula_cells_chain():
    s = Sheet()
    s.set("A1", 2)
    s.set("B1", "=A1+1")
    s.set("C1", "=B1*2")
    assert s.get("C1") == 6


def test_ref_outside_grid_bounds_yields_ref_error():
    assert ev("A01") == "#REF!"
    assert ev("A0") == "#REF!"
    assert ev("A100") == "#REF!"


def test_get_on_parse_error_formula():
    s = Sheet()
    s.set("A1", "=a1")
    assert s.get("A1") == "#PARSE!"


def _addr(i):
    # i in [0, 256): spread across columns since rows only go up to 99.
    col = chr(ord("A") + i // 99)
    row = i % 99 + 1
    return f"{col}{row}"


def test_reference_chain_of_256_cells_evaluates():
    s = Sheet()
    s.set(_addr(0), 1)
    for i in range(1, 256):
        s.set(_addr(i), f"={_addr(i - 1)}+1")
    assert s.get(_addr(255)) == 256
