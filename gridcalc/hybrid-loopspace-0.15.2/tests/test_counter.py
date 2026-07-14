from gridcalc import Sheet


def test_eval_count_increments_for_formula_get():
    sheet = Sheet()
    sheet.set("A1", "=1+2")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 1


def test_eval_count_no_increment_for_literal_get():
    sheet = Sheet()
    sheet.set("A1", 42)
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0


def test_eval_count_no_increment_for_empty_get():
    sheet = Sheet()
    before = sheet.eval_count
    sheet.get("Z99")
    assert sheet.eval_count - before == 0


def test_eval_count_no_increment_for_string_get():
    sheet = Sheet()
    sheet.set("A1", "hello")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0


def test_eval_count_repeat_read_adds_zero():
    sheet = Sheet()
    sheet.set("A1", "=1+2")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0


def test_eval_count_cached_parse_error():
    sheet = Sheet()
    sheet.set("A1", "=1 $ 2")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0
    assert sheet.get("A1") == "#PARSE!"


def test_eval_count_cached_cycle_error():
    sheet = Sheet()
    sheet.set("A1", "=A1")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0
    assert sheet.get("A1") == "#CYCLE!"


def test_eval_count_cached_div_error():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0
    assert sheet.get("A1") == "#DIV!"


def test_eval_count_cached_type_error():
    sheet = Sheet()
    sheet.set("A1", "text")
    sheet.set("B1", "=A1")
    sheet.get("B1")
    before = sheet.eval_count
    sheet.get("B1")
    assert sheet.eval_count - before == 0
    assert sheet.get("B1") == "#TYPE!"


def test_eval_count_ref_chain_counts_both():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 2


def test_eval_count_ref_chain_cached_subsequent():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=1")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("B1")
    assert sheet.eval_count - before == 0
    assert sheet.get("B1") == 1


def test_eval_count_ref_chain_deep():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=C1")
    sheet.set("C1", "=42")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 3
    assert sheet.get("A1") == 42


def test_eval_count_ref_chain_cached_middle():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=C1")
    sheet.set("C1", "=42")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("B1")
    assert sheet.eval_count - before == 0
    assert sheet.get("B1") == 42


def test_eval_count_invalidated_on_formula_set():
    sheet = Sheet()
    sheet.set("A1", "=1")
    sheet.get("A1")
    sheet.set("A1", "=2")
    result = sheet.get("A1")
    assert result == 2


def test_eval_count_invalidated_on_literal_set():
    sheet = Sheet()
    sheet.set("A1", "=1")
    sheet.get("A1")
    sheet.set("A1", 100)
    result = sheet.get("A1")
    assert result == 100


def test_eval_count_short_circuit_div_zero_first():
    sheet = Sheet()
    sheet.set("Y1", "=99")
    sheet.set("X1", "=1/0+Y1")
    before = sheet.eval_count
    sheet.get("X1")
    assert sheet.eval_count - before == 1
    assert sheet.get("X1") == "#DIV!"


def test_eval_count_short_circuit_div_zero_first_cached():
    sheet = Sheet()
    sheet.set("Y1", "=99")
    sheet.set("X1", "=1/0+Y1")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.get("X1")
    assert sheet.eval_count - before == 0


def test_eval_count_short_circuit_ref_after_error():
    sheet = Sheet()
    sheet.set("Z1", "=100")
    sheet.set("X1", "=1/0+Z1")
    before = sheet.eval_count
    sheet.get("X1")
    assert sheet.eval_count - before == 1
    assert sheet.get("Z1") == 100


def test_eval_count_range_short_circuit_sum():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=99")
    sheet.set("D1", "=SUM(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 2
    assert sheet.get("D1") == "#DIV!"


def test_eval_count_range_short_circuit_min():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=99")
    sheet.set("D1", "=MIN(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 2
    assert sheet.get("D1") == "#DIV!"


def test_eval_count_range_short_circuit_max():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=99")
    sheet.set("D1", "=MAX(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 2
    assert sheet.get("D1") == "#DIV!"


def test_eval_count_range_short_circuit_type_error():
    sheet = Sheet()
    sheet.set("A1", 5)
    sheet.set("B1", "text")
    sheet.set("C1", "=99")
    sheet.set("D1", "=SUM(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 1
    assert sheet.get("D1") == "#TYPE!"


def test_eval_count_count_does_not_evaluate_range_members():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=99")
    sheet.set("C1", "=COUNT(A1:B1)")
    before = sheet.eval_count
    sheet.get("C1")
    assert sheet.eval_count - before == 1
    assert sheet.get("C1") == 2


def test_eval_count_count_does_not_evaluate_any_members():
    sheet = Sheet()
    sheet.set("A1", "=1/0")
    sheet.set("B1", "=99")
    sheet.set("C1", "=COUNT(A1:B1)")
    sheet.get("C1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 1
    assert sheet.get("A1") == "#DIV!"


def test_eval_count_formula_set_clears_cache():
    sheet = Sheet()
    sheet.set("A1", "=1")
    sheet.get("A1")
    assert sheet.eval_count == 1
    sheet.set("A1", "=2")
    sheet.get("A1")
    assert sheet.eval_count == 2
    assert sheet.get("A1") == 2


def test_eval_count_multiple_formula_reads():
    sheet = Sheet()
    sheet.set("A1", "=1")
    sheet.set("B1", "=2")
    sheet.set("C1", "=3")
    before = sheet.eval_count
    sheet.get("A1")
    sheet.get("B1")
    sheet.get("C1")
    assert sheet.eval_count - before == 3


def test_eval_count_mixed_literal_and_formula():
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("B1", "=20")
    sheet.set("C1", "hello")
    sheet.set("D1", "=40")
    before = sheet.eval_count
    sheet.get("A1")
    sheet.get("B1")
    sheet.get("C1")
    sheet.get("D1")
    assert sheet.eval_count - before == 2


def test_eval_count_self_referential_formula():
    sheet = Sheet()
    sheet.set("A1", "=A1+1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 1
    assert sheet.get("A1") == "#CYCLE!"


def test_eval_count_short_circuit_in_nested_expression():
    sheet = Sheet()
    sheet.set("Y1", "=99")
    sheet.set("X1", "=(1/0)*Y1")
    before = sheet.eval_count
    sheet.get("X1")
    assert sheet.eval_count - before == 1
    assert sheet.get("X1") == "#DIV!"


def test_eval_count_short_circuit_in_comparison():
    sheet = Sheet()
    sheet.set("Y1", "=99")
    sheet.set("X1", "=(1/0)=Y1")
    before = sheet.eval_count
    sheet.get("X1")
    assert sheet.eval_count - before == 1
    assert sheet.get("X1") == "#DIV!"


def test_eval_count_range_with_formula_members():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("C1", "=3")
    sheet.set("D1", "=SUM(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 2
    assert sheet.get("D1") == 6


def test_eval_count_range_all_formulas():
    sheet = Sheet()
    sheet.set("A1", "=1")
    sheet.set("B1", "=2")
    sheet.set("C1", "=3")
    sheet.set("D1", "=SUM(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 4
    assert sheet.get("D1") == 6


def test_eval_count_range_empty_cells_skipped():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("C1", 3)
    sheet.set("D1", "=SUM(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 1
    assert sheet.get("D1") == 4


def test_eval_count_ref_to_literal():
    sheet = Sheet()
    sheet.set("B1", 42)
    sheet.set("A1", "=B1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 1
    assert sheet.get("A1") == 42


def test_eval_count_ref_to_literal_cached():
    sheet = Sheet()
    sheet.set("B1", 42)
    sheet.set("A1", "=B1")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0


def test_eval_count_error_in_range_short_circuits_later_formulas():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=1/0")
    sheet.set("C1", "=99")
    sheet.set("D1", "=E1")
    sheet.set("E1", "=100")
    sheet.set("F1", "=SUM(A1:E1)")
    before = sheet.eval_count
    sheet.get("F1")
    assert sheet.eval_count - before == 2
    assert sheet.get("F1") == "#DIV!"


def test_eval_count_cycle_in_range():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=SUM(A1:B1)")
    before = sheet.eval_count
    sheet.get("B1")
    assert sheet.eval_count - before == 2
    assert sheet.get("B1") == "#CYCLE!"


def test_eval_count_parse_error_in_range():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=1 $ 2")
    sheet.set("C1", "=99")
    sheet.set("D1", "=SUM(A1:C1)")
    before = sheet.eval_count
    sheet.get("D1")
    assert sheet.eval_count - before == 2
    assert sheet.get("D1") == "#PARSE!"


def test_eval_count_ref_chain_with_error():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=1/0")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 2
    assert sheet.get("A1") == "#DIV!"


def test_eval_count_ref_chain_with_error_cached():
    sheet = Sheet()
    sheet.set("A1", "=B1")
    sheet.set("B1", "=1/0")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0
    assert sheet.get("A1") == "#DIV!"


def test_eval_count_non_formula_set_no_increment():
    sheet = Sheet()
    sheet.set("A1", "=1")
    sheet.get("A1")
    before = sheet.eval_count
    sheet.set("B1", 100)
    assert sheet.eval_count == before
    sheet.set("C1", "text")
    assert sheet.eval_count == before


def test_eval_count_eval_count_property():
    sheet = Sheet()
    assert sheet.eval_count == 0
    sheet.set("A1", "=1")
    assert sheet.eval_count == 0
    sheet.get("A1")
    assert sheet.eval_count == 1
    sheet.get("A1")
    assert sheet.eval_count == 1
    sheet.set("A1", "=2")
    sheet.get("A1")
    assert sheet.eval_count == 2


def test_cache_does_not_pollute_empty_cell():
    sheet = Sheet()
    sheet.set("A1", "=Z9+1")
    sheet.get("A1")
    assert sheet.get("Z9") is None


def test_cache_does_not_pollute_string_cell():
    sheet = Sheet()
    sheet.set("A1", "text")
    sheet.set("B1", "=A1")
    sheet.get("B1")
    assert sheet.get("A1") == "text"
