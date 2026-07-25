"""Task 1.2: Address validation and literal storage — R1, R2 tests."""
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sheet():
    """Create a fresh workbook with one sheet named 'S1'."""
    from gridcalc import Workbook
    wb = Workbook()
    return wb, wb.add_sheet("S1")


# ---------------------------------------------------------------------------
# 1. Address validation — valid addresses (R1)
# ---------------------------------------------------------------------------

class TestValidAddresses:
    def test_single_letter_a_to_z_with_row_1(self):
        """A1 through Z1 must all be accepted."""
        _, h = _make_sheet()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            h.set(f"{letter}1", 0)

    def test_single_letter_a_to_z_with_row_99(self):
        """A99 through Z99 must all be accepted."""
        _, h = _make_sheet()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            h.set(f"{letter}99", 0)

    def test_mid_range_rows(self):
        """Rows 10, 50, 99 are valid."""
        _, h = _make_sheet()
        h.set("M10", 1)
        h.set("Z50", 2)
        h.set("A99", 3)
        assert h.get("M10") == 1
        assert h.get("Z50") == 2
        assert h.get("A99") == 3

    def test_row_1_and_99_boundaries(self):
        """Row 1 and row 99 are the valid extremes."""
        _, h = _make_sheet()
        h.set("A1", 100)
        h.set("Z99", 200)
        assert h.get("A1") == 100
        assert h.get("Z99") == 200


# ---------------------------------------------------------------------------
# 2. Address validation — invalid addresses (R1)
# ---------------------------------------------------------------------------

class TestInvalidAddresses:
    def test_lowercase_rejected(self):
        """Lowercase letters must be rejected."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("a1", 1)
        with pytest.raises(ValueError):
            h.set("z99", 1)
        with pytest.raises(ValueError):
            h.set("m5", 1)

    def test_row_zero_rejected(self):
        """Row 0 is not valid (range is 1-99)."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("A0", 1)
        with pytest.raises(ValueError):
            h.set("Z0", 1)

    def test_leading_zeros_rejected(self):
        """Leading zeros in row are not valid."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("A01", 1)
        with pytest.raises(ValueError):
            h.set("B099", 1)
        with pytest.raises(ValueError):
            h.set("C00", 1)

    def test_row_100_rejected(self):
        """Row 100 exceeds the valid range (max 99)."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("A100", 1)
        with pytest.raises(ValueError):
            h.set("Z100", 1)
        with pytest.raises(ValueError):
            h.set("A999", 1)

    def test_two_letter_columns_rejected(self):
        """Two-letter column references like AA1 are not valid."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("AA1", 1)
        with pytest.raises(ValueError):
            h.set("AB50", 1)
        with pytest.raises(ValueError):
            h.set("ZZ99", 1)

    def test_empty_string_rejected(self):
        """Empty string is not a valid address."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("", 1)

    def test_whitespace_rejected(self):
        """Internal or leading/trailing whitespace is not valid."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set(" A1", 1)
        with pytest.raises(ValueError):
            h.set("A1 ", 1)
        with pytest.raises(ValueError):
            h.set("A 1", 1)
        with pytest.raises(ValueError):
            h.set("\tA1", 1)

    def test_qualified_address_rejected(self):
        """Qualified addresses like S1!A1 must be rejected."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("S1!A1", 1)
        with pytest.raises(ValueError):
            h.set("Sheet1!B5", 1)
        with pytest.raises(ValueError):
            h.set("S2!Z99", 1)

    def test_non_str_address_rejected(self):
        """Non-string address arguments must be rejected."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set(123, 1)
        with pytest.raises(ValueError):
            h.set(None, 1)
        with pytest.raises(ValueError):
            h.set(["A1"], 1)

    def test_invalid_address_leaves_state_unchanged(self):
        """A failed set must not modify the sheet state."""
        _, h = _make_sheet()
        h.set("A1", 42)
        initial_cells = dict(h._cells)
        initial_eval = h.eval_count
        with pytest.raises(ValueError):
            h.set("invalid", 99)
        assert h._cells == initial_cells
        assert h.eval_count == initial_eval

    def test_get_with_invalid_address_raises_valueerror(self):
        """get() with invalid address must raise ValueError."""
        _, h = _make_sheet()
        h.set("A1", 10)
        with pytest.raises(ValueError):
            h.get("invalid")
        with pytest.raises(ValueError):
            h.get("")
        with pytest.raises(ValueError):
            h.get("AA1")
        with pytest.raises(ValueError):
            h.get("A0")

    def test_get_with_invalid_address_leaves_state_unchanged(self):
        """A failed get must not modify contents, caches, or counters."""
        _, h = _make_sheet()
        h.set("A1", 10)
        h.set("B2", 20)
        initial_cells = dict(h._cells)
        initial_eval = h.eval_count
        with pytest.raises(ValueError):
            h.get("invalid")
        assert h._cells == initial_cells
        assert h.eval_count == initial_eval


# ---------------------------------------------------------------------------
# 3. set() — accepted raw types (R2)
# ---------------------------------------------------------------------------

class TestSetAcceptedTypes:
    def test_plain_int_accepted(self):
        """Plain int values must be stored as int."""
        _, h = _make_sheet()
        h.set("A1", 42)
        assert h.get("A1") == 42
        assert type(h.get("A1")) is int

    def test_zero_int_accepted(self):
        """Zero is a valid int value."""
        _, h = _make_sheet()
        h.set("A1", 0)
        assert h.get("A1") == 0
        assert type(h.get("A1")) is int

    def test_negative_int_accepted(self):
        """Negative ints are valid."""
        _, h = _make_sheet()
        h.set("A1", -5)
        assert h.get("A1") == -5
        assert type(h.get("A1")) is int

    def test_bool_rejected(self):
        """bool must be rejected despite being an int subclass."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("A1", True)
        with pytest.raises(ValueError):
            h.set("A1", False)

    def test_bool_rejection_leaves_state_unchanged(self):
        """A failed bool set must not modify state."""
        _, h = _make_sheet()
        h.set("A1", 10)
        initial_cells = dict(h._cells)
        with pytest.raises(ValueError):
            h.set("A1", True)
        assert h._cells == initial_cells

    def test_int_subclass_accepted(self):
        """Other int subclasses (not bool) must be accepted and normalized."""
        class MyInt(int):
            pass
        _, h = _make_sheet()
        h.set("A1", MyInt(42))
        result = h.get("A1")
        assert result == 42
        assert type(result) is int

    def test_plain_str_accepted(self):
        """Plain str values must be stored as str."""
        _, h = _make_sheet()
        h.set("A1", "hello")
        assert h.get("A1") == "hello"
        assert type(h.get("A1")) is str

    def test_empty_str_accepted(self):
        """Empty string is a valid str value."""
        _, h = _make_sheet()
        h.set("A1", "")
        assert h.get("A1") == ""
        assert type(h.get("A1")) is str

    def test_str_subclass_accepted(self):
        """str subclasses must be accepted and normalized to plain str."""
        class MyStr(str):
            pass
        _, h = _make_sheet()
        h.set("A1", MyStr("hello"))
        result = h.get("A1")
        assert result == "hello"
        assert type(result) is str

    def test_other_types_rejected(self):
        """Other types (float, list, dict, etc.) must be rejected."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("A1", 3.14)
        with pytest.raises(ValueError):
            h.set("A1", [1, 2, 3])
        with pytest.raises(ValueError):
            h.set("A1", {"key": "val"})
        with pytest.raises(ValueError):
            h.set("A1", None)
        with pytest.raises(ValueError):
            h.set("A1", b"bytes")

    def test_set_returns_none(self):
        """set() must return None on success."""
        _, h = _make_sheet()
        result = h.set("A1", 42)
        assert result is None


# ---------------------------------------------------------------------------
# 4. get() — behavior on never-set and literal cells (R2)
# ---------------------------------------------------------------------------

class TestGetBehavior:
    def test_get_never_set_returns_none(self):
        """get() on a never-set cell must return None."""
        _, h = _make_sheet()
        assert h.get("A1") is None

    def test_get_literal_int_returns_stored_int(self):
        """get() on a literal int cell must return the stored int unchanged."""
        _, h = _make_sheet()
        h.set("A1", 42)
        assert h.get("A1") == 42
        assert type(h.get("A1")) is int

    def test_get_literal_str_returns_stored_str(self):
        """get() on a literal str cell must return the stored str unchanged."""
        _, h = _make_sheet()
        h.set("A1", "hello")
        assert h.get("A1") == "hello"
        assert type(h.get("A1")) is str

    def test_get_literal_formula_str_evaluates(self):
        """get() on a formula cell (str starting with '=') evaluates and returns
        the numeric result (references to unset cells evaluate to 0 as placeholder)."""
        _, h = _make_sheet()
        h.set("A1", "=B1+C1")
        assert h.get("A1") == 0


# ---------------------------------------------------------------------------
# 5. Replacing occupied cells (acceptance criterion)
# ---------------------------------------------------------------------------

class TestReplaceOccupiedCell:
    def test_replace_int_with_int(self):
        """Replacing an int cell with another int must only change that cell."""
        _, h = _make_sheet()
        h.set("A1", 10)
        h.set("B2", 20)
        h.set("A1", 99)
        assert h.get("A1") == 99
        assert h.get("B2") == 20
        assert h.eval_count == 0

    def test_replace_int_with_str(self):
        """Replacing an int cell with a str must only change that cell."""
        _, h = _make_sheet()
        h.set("A1", 10)
        h.set("A1", "hello")
        assert h.get("A1") == "hello"
        assert type(h.get("A1")) is str

    def test_replace_str_with_int(self):
        """Replacing a str cell with an int must only change that cell."""
        _, h = _make_sheet()
        h.set("A1", "hello")
        h.set("A1", 42)
        assert h.get("A1") == 42
        assert type(h.get("A1")) is int

    def test_replace_does_not_change_eval_count(self):
        """Replacing a cell must not evaluate formulas or change eval_count."""
        _, h = _make_sheet()
        h.set("A1", 10)
        initial_eval = h.eval_count
        h.set("A1", 20)
        assert h.eval_count == initial_eval

    def test_replace_does_not_affect_other_cells(self):
        """Replacing one cell must not affect other cells."""
        _, h = _make_sheet()
        h.set("A1", 1)
        h.set("B2", 2)
        h.set("C3", 3)
        h.set("A1", 100)
        assert h.get("B2") == 2
        assert h.get("C3") == 3


# ---------------------------------------------------------------------------
# 6. Edge cases and state preservation
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_multiple_sets_to_different_cells(self):
        """Setting multiple cells must work independently."""
        _, h = _make_sheet()
        h.set("A1", 1)
        h.set("B2", 2)
        h.set("C3", 3)
        assert h.get("A1") == 1
        assert h.get("B2") == 2
        assert h.get("C3") == 3

    def test_get_after_multiple_sets(self):
        """get() must return the latest value for each cell."""
        _, h = _make_sheet()
        h.set("A1", 10)
        h.set("A1", 20)
        h.set("A1", 30)
        assert h.get("A1") == 30

    def test_invalid_set_then_valid_get(self):
        """A failed set must not prevent subsequent valid operations."""
        _, h = _make_sheet()
        with pytest.raises(ValueError):
            h.set("invalid", 1)
        h.set("A1", 42)
        assert h.get("A1") == 42

    def test_invalid_get_then_valid_get(self):
        """A failed get must not prevent subsequent valid operations."""
        _, h = _make_sheet()
        h.set("A1", 42)
        with pytest.raises(ValueError):
            h.get("invalid")
        assert h.get("A1") == 42

    def test_trailing_newline_rejected(self):
        """Addresses with trailing newlines must be rejected (full-string match)."""
        _, h = _make_sheet()
        h.set("A1", 1)
        initial_cells = dict(h._cells)
        initial_eval = h.eval_count
        with pytest.raises(ValueError):
            h.set("A1\n", 2)
        with pytest.raises(ValueError):
            h.set("Z99\n", 3)
        with pytest.raises(ValueError):
            h.get("A1\n")
        assert h._cells == initial_cells
        assert h.eval_count == initial_eval
        assert h.get("A1") == 1

    def test_trailing_newline_does_not_overwrite(self):
        """A trailing-newline address must not overwrite a valid cell."""
        _, h = _make_sheet()
        h.set("A1", 42)
        with pytest.raises(ValueError):
            h.set("A1\n", 99)
        assert h.get("A1") == 42
        assert type(h.get("A1")) is int
