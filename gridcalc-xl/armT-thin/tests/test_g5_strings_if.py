from gridcalc import Workbook


def make_sheet():
    return Workbook().add_sheet("S1")


def test_string_literals_and_typing_rules():
    sheet = make_sheet()
    sheet.set("A1", '="x"')
    sheet.set("A2", '="x"="x"')
    sheet.set("A3", '="x"<>"y"')
    sheet.set("A4", '="x"+B1')
    sheet.set("A5", '=1="1"')
    sheet.set("B1", "=1/0")

    assert sheet.get("A1") == "x"
    assert sheet.get("A2") == 1
    assert sheet.get("A3") == 1
    assert sheet.get("A4") == "#TYPE!"
    assert sheet.get("A5") == "#TYPE!"


def test_string_ordering_and_unary_minus_are_type_errors():
    sheet = make_sheet()
    cases = {
        "A1": '="a"<"b"',
        "A2": '="a"<="b"',
        "A3": '="a">"b"',
        "A4": '="a">="b"',
        "A5": '=-"x"',
    }
    for addr, formula in cases.items():
        sheet.set(addr, formula)
        assert sheet.get(addr) == "#TYPE!"


def test_concat_and_len_render_ints_and_short_circuit_errors():
    sheet = make_sheet()
    sheet.set("A1", '=CONCAT("a", 007, -3)')
    sheet.set("A2", '=LEN(CONCAT("a", 12))')
    sheet.set("A3", '=CONCAT(1/0, B1)')
    sheet.set("B1", "=1+1")
    before = sheet.eval_count

    assert sheet.get("A1") == "a7-3"
    assert sheet.get("A2") == 3
    assert sheet.get("A3") == "#DIV!"
    assert sheet.get("B1") == 2
    assert sheet.eval_count == before + 4


def test_if_evaluates_only_selected_branch_but_static_closure_invalidates():
    sheet = make_sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=1/0")
    sheet.set("C1", '=IF(A1, "yes", B1)')

    before = sheet.eval_count
    assert sheet.get("C1") == "yes"
    assert sheet.eval_count - before == 1

    sheet.set("B1", "=2+2")
    before = sheet.eval_count
    assert sheet.get("C1") == "yes"
    assert sheet.eval_count - before == 1


def test_if_condition_errors_and_string_condition_type_error():
    sheet = make_sheet()
    sheet.set("A1", '=IF(1/0, 1, 2)')
    sheet.set("A2", '=IF("x", 1, 2)')
    sheet.set("A3", '=IF(0, 1/0, "ok")')

    assert sheet.get("A1") == "#DIV!"
    assert sheet.get("A2") == "#TYPE!"
    assert sheet.get("A3") == "ok"


def test_wrong_arity_is_parse_error():
    sheet = make_sheet()
    for addr, formula in [("A1", "=CONCAT()"), ("A2", "=LEN(1,2)"), ("A3", "=IF(1,2)"), ("A4", "=NOW(1)")]:
        sheet.set(addr, formula)
        assert sheet.get(addr) == "#PARSE!"
