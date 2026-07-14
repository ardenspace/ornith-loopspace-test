import pytest
from gridcalc.sheet import Sheet


class TestSetGetRoundTrip:
    def test_set_get_int(self):
        s = Sheet()
        s.set("A1", 42)
        assert s.get("A1") == 42

    def test_set_get_str(self):
        s = Sheet()
        s.set("A1", "hello")
        assert s.get("A1") == "hello"

    def test_get_never_set_returns_none(self):
        s = Sheet()
        assert s.get("A1") is None

    def test_set_returns_none(self):
        s = Sheet()
        assert s.set("A1", 10) is None


class TestBoolRejected:
    def test_set_bool_raises_valueerror(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", True)

    def test_set_bool_false_raises_valueerror(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", False)


class TestOtherTypesRejected:
    def test_set_float_raises_valueerror(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", 3.14)

    def test_set_none_raises_valueerror(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", None)

    def test_set_list_raises_valueerror(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", [1, 2, 3])

    def test_set_dict_raises_valueerror(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", {"a": 1})


class TestValueErrorLeavesStateUnchanged:
    def test_set_valueerror_preserves_prior_content(self):
        s = Sheet()
        s.set("A1", 10)
        with pytest.raises(ValueError):
            s.set("A1", 3.14)
        assert s.get("A1") == 10

    def test_set_valueerror_preserves_eval_count(self):
        s = Sheet()
        s.set("A1", 10)
        s.get("A1")
        count_before = s.eval_count
        with pytest.raises(ValueError):
            s.set("A1", 3.14)
        assert s.eval_count == count_before


class TestNormalization:
    def test_int_subclass_normalized_to_int(self):
        class MyInt(int):
            pass

        s = Sheet()
        s.set("A1", MyInt(42))
        assert type(s.get("A1")) is int

    def test_str_subclass_normalized_to_str(self):
        class MyStr(str):
            pass

        s = Sheet()
        s.set("A1", MyStr("hello"))
        assert type(s.get("A1")) is str


class TestReplacement:
    def test_int_to_str_replacement(self):
        s = Sheet()
        s.set("A1", 10)
        s.set("A1", "hello")
        assert s.get("A1") == "hello"

    def test_str_to_int_replacement(self):
        s = Sheet()
        s.set("A1", "hello")
        s.set("A1", 10)
        assert s.get("A1") == 10

    def test_str_to_formula_replacement(self):
        s = Sheet()
        s.set("A1", "hello")
        s.set("A1", "=A2")
        assert s.get("A1") == 0

    def test_formula_to_int_replacement(self):
        s = Sheet()
        s.set("A1", "=A2")
        s.set("A1", 10)
        assert s.get("A1") == 10


class TestFormulaAccepted:
    def test_set_formula_string_no_error(self):
        s = Sheet()
        s.set("A1", "=B2+C3")
        assert s.get("A1") == 0

    def test_formula_not_evaluated_at_set_time(self):
        s = Sheet()
        s.set("A1", "=B2+C3")
        assert s.eval_count == 0
        assert s.get("A1") == 0


class TestEvalCount:
    def test_eval_count_stays_zero_across_literal_set_get(self):
        s = Sheet()
        s.set("A1", 10)
        s.get("A1")
        s.set("A2", "hello")
        s.get("A2")
        s.get("A1")
        assert s.eval_count == 0
