import pytest
from gridcalc.sheet import Sheet


class TestSheetAddressValidation:
    def test_get_set_valid_addresses(self):
        s = Sheet()
        s.set("A1", 10)
        s.set("Z99", 99)
        s.set("M50", 50)
        assert s.get("A1") == 10
        assert s.get("Z99") == 99
        assert s.get("M50") == 50

    def test_invalid_lowercase(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("a1")
        with pytest.raises(ValueError):
            s.set("a1", 1)

    def test_invalid_A0(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A0")
        with pytest.raises(ValueError):
            s.set("A0", 1)

    def test_invalid_A01(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A01")
        with pytest.raises(ValueError):
            s.set("A01", 1)

    def test_invalid_A100(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A100")
        with pytest.raises(ValueError):
            s.set("A100", 1)

    def test_invalid_AA1(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("AA1")
        with pytest.raises(ValueError):
            s.set("AA1", 1)

    def test_invalid_empty(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("")
        with pytest.raises(ValueError):
            s.set("", 1)

    def test_invalid_leading_whitespace(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get(" A1")
        with pytest.raises(ValueError):
            s.set(" A1", 1)

    def test_invalid_trailing_whitespace(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A1 ")
        with pytest.raises(ValueError):
            s.set("A1 ", 1)

    def test_invalid_internal_whitespace(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A 1")
        with pytest.raises(ValueError):
            s.set("A 1", 1)

    def test_invalid_non_str_get_int(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get(5)

    def test_invalid_non_str_get_none(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.get(None)

    def test_invalid_non_str_set_none(self):
        s = Sheet()
        with pytest.raises(ValueError):
            s.set(None, 1)

    def test_str_subclass_accepted(self):
        class Addr(str):
            pass

        s = Sheet()
        addr = Addr("A1")
        s.set(addr, 42)
        assert s.get(addr) == 42
        assert s.get("A1") == 42

    def test_get_valueerror_no_state_change(self):
        s = Sheet()
        s.set("A1", 10)
        s.get("A1")
        count_before = s.eval_count
        with pytest.raises(ValueError):
            s.get("invalid")
        assert s.eval_count == count_before
        assert s.get("A1") == 10

    def test_eval_count_fresh_sheet(self):
        s = Sheet()
        assert s.eval_count == 0

    def test_eval_count_does_not_increment_on_literal_get(self):
        s = Sheet()
        s.set("A1", 10)
        s.get("A1")
        assert s.eval_count == 0

    def test_eval_count_does_not_increment_on_invalid_get(self):
        s = Sheet()
        s.set("A1", 10)
        with pytest.raises(ValueError):
            s.get("invalid")
        assert s.eval_count == 0
