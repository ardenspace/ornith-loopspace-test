from gridcalc.sheet import Sheet


class TestEvalCountBasics:
    def test_starts_at_zero(self):
        assert Sheet().eval_count == 0

    def test_set_does_not_change_eval_count(self):
        s = Sheet()
        s.set("A1", "=1+2")
        assert s.eval_count == 0

    def test_get_on_formula_increments_by_one(self):
        s = Sheet()
        s.set("A1", "=1+2")
        s.get("A1")
        assert s.eval_count == 1

    def test_repeat_get_does_not_increment(self):
        s = Sheet()
        s.set("A1", "=1+2")
        s.get("A1")
        s.get("A1")
        assert s.eval_count == 1

    def test_get_on_literal_does_not_increment(self):
        s = Sheet()
        s.set("A1", 42)
        s.get("A1")
        assert s.eval_count == 0

    def test_get_on_empty_does_not_increment(self):
        s = Sheet()
        s.get("Z9")
        assert s.eval_count == 0


class TestErrorCaching:
    def test_div_error_is_cached(self):
        s = Sheet()
        s.set("A1", "=1/0")
        assert s.get("A1") == "#DIV!"
        assert s.get("A1") == "#DIV!"
        assert s.eval_count == 1

    def test_cycle_error_is_cached(self):
        s = Sheet()
        s.set("A1", "=B1")
        s.set("B1", "=A1")
        s.get("A1")
        assert s.eval_count == 2
        s.get("A1")
        assert s.eval_count == 2

    def test_parse_error_is_cached(self):
        s = Sheet()
        s.set("A1", "=1 + = 2")
        assert s.get("A1") == "#PARSE!"
        assert s.get("A1") == "#PARSE!"
        assert s.eval_count == 1


class TestSetInvalidatesCache:
    def test_set_clears_cache(self):
        s = Sheet()
        s.set("A1", 10)
        s.set("B1", "=A1+5")
        s.get("B1")
        assert s.eval_count == 1
        s.set("A1", 20)
        s.get("B1")
        assert s.eval_count == 2
        assert s.get("B1") == 25

    def test_set_formula_clears_cache(self):
        s = Sheet()
        s.set("A1", "=1+2")
        s.get("A1")
        assert s.eval_count == 1
        s.set("A1", "=3+4")
        s.get("A1")
        assert s.eval_count == 2
        assert s.get("A1") == 7


class TestShortCircuitArithmetic:
    def test_div_by_zero_short_circuits_right_operand(self):
        s = Sheet()
        s.set("Y1", "=99")
        s.set("A1", "=1/0+Y1")
        s.get("A1")
        assert s.get("A1") == "#DIV!"
        assert s.eval_count == 1

    def test_left_error_short_circuits_right_operand(self):
        s = Sheet()
        s.set("Y1", "=99")
        s.set("A1", "=1/0+Y1")
        s.get("A1")
        assert s.eval_count == 1


class TestShortCircuitRange:
    def test_sum_short_circuits_on_first_error(self):
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "hello")
        s.set("C1", "=100")
        s.set("D1", "=200")
        s.set("E1", "=SUM(A1:D1)")
        s.get("E1")
        assert s.get("E1") == "#TYPE!"
        assert s.eval_count == 1

    def test_count_does_not_increment_for_range_members(self):
        s = Sheet()
        s.set("A1", "=1")
        s.set("B1", "=2")
        s.set("C1", "=3")
        s.set("D1", "=COUNT(A1:C1)")
        s.get("D1")
        assert s.get("D1") == 3
        assert s.eval_count == 1

    def test_count_with_formula_cells(self):
        s = Sheet()
        s.set("A1", "=10")
        s.set("B1", "=20")
        s.set("C1", "=COUNT(A1:B1)")
        s.get("C1")
        assert s.get("C1") == 2
        assert s.eval_count == 1
