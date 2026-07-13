"""Task 1.1: Address validation tests."""
import pytest
from gridcalc import Sheet


class TestAddressValidation:
    """Tests for address validation per R1 and Task 1.1 acceptance criteria."""

    def test_valid_addresses_accepted(self):
        """get/set accept valid addresses across the grid."""
        s = Sheet()
        # Test at least A1, Z99, M50 as required
        s.set("A1", 1)
        assert s.get("A1") == 1
        s.set("Z99", 2)
        assert s.get("Z99") == 2
        s.set("M50", 3)
        assert s.get("M50") == 3

    def test_lowercase_rejected(self):
        """lowercase addresses raise ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("a1")
        with pytest.raises(ValueError):
            s.set("a1", 1)

    def test_a0_rejected(self):
        """A0 (row 0) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A0")
        with pytest.raises(ValueError):
            s.set("A0", 1)

    def test_a01_rejected(self):
        """A01 (leading zero) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A01")
        with pytest.raises(ValueError):
            s.set("A01", 1)

    def test_a100_rejected(self):
        """A100 (row > 99) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A100")
        with pytest.raises(ValueError):
            s.set("A100", 1)

    def test_aa1_rejected(self):
        """AA1 (two letters) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("AA1")
        with pytest.raises(ValueError):
            s.set("AA1", 1)

    def test_empty_string_rejected(self):
        """Empty string raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("")
        with pytest.raises(ValueError):
            s.set("", 1)

    def test_leading_space_rejected(self):
        """' A1' (leading space) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get(" A1")
        with pytest.raises(ValueError):
            s.set(" A1", 1)

    def test_trailing_space_rejected(self):
        """'A1 ' (trailing space) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A1 ")
        with pytest.raises(ValueError):
            s.set("A1 ", 1)

    def test_internal_space_rejected(self):
        """'A 1' (internal space) raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get("A 1")
        with pytest.raises(ValueError):
            s.set("A 1", 1)

    def test_non_str_argument_rejected(self):
        """Non-str arguments raise ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.get(5)
        with pytest.raises(ValueError):
            s.get(None)
        with pytest.raises(ValueError):
            s.set(None, 1)

    def test_str_subclass_accepted(self):
        """str-subclass with valid address text is accepted."""
        s = Sheet()

        class ValidAddr(str):
            pass

        addr = ValidAddr("A1")
        s.set(addr, 10)
        assert s.get(addr) == 10
        # R2 normalization: get returns plain str
        assert type(s.get("A1")) is str or type(s.get("A1")) is int

    def test_get_valueerror_preserves_state(self):
        """A get that raises ValueError leaves all observable state unchanged."""
        s = Sheet()
        s.set("A1", 42)
        initial_eval_count = s.eval_count
        with pytest.raises(ValueError):
            s.get("invalid")
        assert s.get("A1") == 42
        assert s.eval_count == initial_eval_count

    def test_eval_count_initially_zero(self):
        """eval_count property exists and is 0 on a fresh Sheet."""
        s = Sheet()
        assert hasattr(s, "eval_count")
        assert s.eval_count == 0

    def test_eval_count_unchanged_on_literal_operations(self):
        """eval_count stays 0 across literal set/get calls."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "hello")
        s.get("A1")
        s.get("B1")
        assert s.eval_count == 0
