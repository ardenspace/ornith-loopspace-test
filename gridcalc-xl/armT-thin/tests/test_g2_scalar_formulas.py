from gridcalc import Workbook


def make_sheet():
    return Workbook().add_sheet("S1")


def test_integer_arithmetic_precedence_and_division():
    sheet = make_sheet()
    cases = {
        "=1+2*3": 7,
        "=(1+2)*3": 9,
        "=--1": 1,
        "=2--3": 5,
        "=-7/2": -3,
        "=7/-2": -3,
        "=7/2": 3,
        "=1/0": "#DIV!",
    }
    for addr, (formula, expected) in zip(["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"], cases.items()):
        sheet.set(addr, formula)
        assert sheet.get(addr) == expected


def test_comparisons_are_left_associative():
    sheet = make_sheet()
    sheet.set("A1", "=1<2<3")
    sheet.set("A2", "=1=1")
    sheet.set("A3", "=1<>1")
    sheet.set("A4", "=2>=2")

    assert sheet.get("A1") == 1
    assert sheet.get("A2") == 1
    assert sheet.get("A3") == 0
    assert sheet.get("A4") == 1


def test_references_and_empty_cells():
    sheet = make_sheet()
    sheet.set("A1", 5)
    sheet.set("A2", "=A1+B1")
    sheet.set("A3", "=A01")
    sheet.set("A4", "=A100")

    assert sheet.get("A2") == 5
    assert sheet.get("A3") == "#REF!"
    assert sheet.get("A4") == "#REF!"


def test_parse_errors_are_in_band_values():
    sheet = make_sheet()
    for addr, formula in [("A1", "="), ("A2", "=1 < = 2"), ("A3", "=sum(1)"), ("A4", "=A1:B2")]:
        sheet.set(addr, formula)
        assert sheet.get(addr) == "#PARSE!"


def test_multicharacter_uppercase_identifiers_are_undefined_names():
    sheet = make_sheet()
    sheet.set("A1", "=AA1")
    sheet.set("A2", "=FOO")
    sheet.set("A3", "=F")

    assert sheet.get("A1") == "#NAME!"
    assert sheet.get("A2") == "#NAME!"
    assert sheet.get("A3") == "#PARSE!"


def test_errors_short_circuit_left_to_right():
    sheet = make_sheet()
    sheet.set("A1", "=1/0+B1")
    sheet.set("B1", "=1+1")
    before = sheet.eval_count

    assert sheet.get("A1") == "#DIV!"
    assert sheet.get("B1") == 2
    assert sheet.eval_count == before + 2
