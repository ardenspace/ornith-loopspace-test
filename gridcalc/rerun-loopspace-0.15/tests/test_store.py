"""Task 1.2: Literal values — types, normalization, replacement."""
import pytest
from gridcalc import Sheet


class TestLiteralValues:
    """Tests for literal value storage per R2 and Task 1.2 acceptance criteria."""

    def test_int_roundtrip(self):
        """set/get round-trips int values."""
        s = Sheet()
        s.set("A1", 42)
        assert s.get("A1") == 42

    def test_str_roundtrip(self):
        """set/get round-trips str values."""
        s = Sheet()
        s.set("A1", "hello")
        assert s.get("A1") == "hello"

    def test_never_set_returns_none(self):
        """get of a never-set cell is None."""
        s = Sheet()
        assert s.get("A1") is None

    def test_formula_string_accepted(self):
        """set accepts a str starting with '=' without error (stored as formula)."""
        s = Sheet()
        # Phase 2 will evaluate formulas; this phase never calls get on formula cells
        s.set("A1", "=1+2")
        # Just verify it was stored (we can't get it yet — that would trigger evaluation)
        # We verify by setting a different cell and confirming no error
        s.set("B1", 1)
        assert s.get("B1") == 1

    def test_bool_rejected(self):
        """bool raw raises ValueError despite being an int subclass."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", True)
        with pytest.raises(ValueError):
            s.set("A1", False)

    def test_float_rejected(self):
        """float raw raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", 3.14)

    def test_none_rejected(self):
        """None raw raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", None)

    def test_list_rejected(self):
        """list raw raises ValueError."""
        s = Sheet()
        with pytest.raises(ValueError):
            s.set("A1", [1, 2, 3])

    def test_int_subclass_normalized(self):
        """int-subclass instances are normalized to plain int."""
        s = Sheet()

        class MyInt(int):
            pass

        s.set("A1", MyInt(42))
        result = s.get("A1")
        assert result == 42
        assert type(result) is int

    def test_str_subclass_normalized(self):
        """str-subclass instances are normalized to plain str."""
        s = Sheet()

        class MyStr(str):
            pass

        s.set("A1", MyStr("hello"))
        result = s.get("A1")
        assert result == "hello"
        assert type(result) is str

    def test_set_returns_none(self):
        """set returns None on success."""
        s = Sheet()
        result = s.set("A1", 42)
        assert result is None

    def test_set_replaces_content(self):
        """set on an occupied cell replaces content."""
        s = Sheet()
        s.set("A1", 1)
        assert s.get("A1") == 1
        s.set("A1", "hello")
        assert s.get("A1") == "hello"
        s.set("A1", "=formula")
        # Can't get formula cells in this phase, but we verify replacement by setting back
        s.set("A1", 2)
        assert s.get("A1") == 2

    def test_int_to_str_to_formula_transitions(self):
        """int→str→formula transitions all work."""
        s = Sheet()
        s.set("A1", 1)
        assert s.get("A1") == 1
        s.set("A1", "hello")
        assert s.get("A1") == "hello"
        s.set("A1", "=formula")
        # Verify we can still set after formula
        s.set("A1", 2)
        assert s.get("A1") == 2

    def test_valueerror_leaves_prior_content(self):
        """A set that raises ValueError leaves prior content unchanged."""
        s = Sheet()
        s.set("A1", 42)
        with pytest.raises(ValueError):
            s.set("A1", 3.14)  # float rejected
        assert s.get("A1") == 42

    def test_valueerror_leaves_eval_count_unchanged(self):
        """A set that raises ValueError leaves eval_count unchanged."""
        s = Sheet()
        initial = s.eval_count
        with pytest.raises(ValueError):
            s.set("A1", True)  # bool rejected
        assert s.eval_count == initial

    def test_eval_count_stays_zero_for_literals(self):
        """eval_count stays 0 across any sequence of literal set/get calls."""
        s = Sheet()
        s.set("A1", 1)
        s.set("B1", "hello")
        s.get("A1")
        s.get("B1")
        s.set("A1", 2)  # replace
        s.get("A1")
        assert s.eval_count == 0
