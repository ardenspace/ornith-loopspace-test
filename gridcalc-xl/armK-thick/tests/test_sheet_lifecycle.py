"""Task 8.1: Sheet lifecycle and public surface completion — R21."""
import pytest

from gridcalc import Workbook


# ---------------------------------------------------------------------------
# 1. Hard invalid sheet names (verifier finding 1)
# ---------------------------------------------------------------------------

class TestSheetNameValidationHardInvalid:
    """R21 exact validation: non-ASCII, newlines, edge cases."""

    def setup_method(self):
        self.wb = Workbook()

    def test_rejects_non_ascii_unicode(self):
        """Sheet name with non-ASCII character (e.g. 'Å') must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("Å")

    def test_rejects_name_with_newline(self):
        """Sheet name containing a newline must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A\n")

    def test_rejects_name_with_tab(self):
        """Sheet name containing a tab must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A\tB")

    def test_rejects_name_with_carriage_return(self):
        """Sheet name containing a carriage return must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A\r")

    def test_rejects_name_with_null_byte(self):
        """Sheet name containing a null byte must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A\0")

    def test_rejects_name_with_space(self):
        """Sheet name containing a space must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A B")

    def test_rejects_name_with_hyphen(self):
        """Sheet name containing a hyphen must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A-B")

    def test_rejects_name_with_dot(self):
        """Sheet name containing a dot must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A.B")

    def test_rejects_name_with_at_sign(self):
        """Sheet name containing '@' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A@B")

    def test_rejects_name_with_hash(self):
        """Sheet name containing '#' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A#B")

    def test_rejects_name_with_slash(self):
        """Sheet name containing '/' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A/B")

    def test_rejects_name_with_backslash(self):
        """Sheet name containing '\\' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A\\B")

    def test_rejects_name_with_parentheses(self):
        """Sheet name containing parentheses must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A(B)")

    def test_rejects_name_with_brackets(self):
        """Sheet name containing brackets must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A[B]")

    def test_rejects_name_with_braces(self):
        """Sheet name containing braces must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A{B}")

    def test_rejects_name_with_quotes(self):
        """Sheet name containing quotes must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet('A"B')
        with pytest.raises(ValueError):
            self.wb.add_sheet("A'B")

    def test_rejects_name_with_comma(self):
        """Sheet name containing a comma must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A,B")

    def test_rejects_name_with_semicolon(self):
        """Sheet name containing a semicolon must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A;B")

    def test_rejects_name_with_colon(self):
        """Sheet name containing a colon must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A:B")

    def test_rejects_name_with_equals(self):
        """Sheet name containing '=' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A=B")

    def test_rejects_name_with_plus(self):
        """Sheet name containing '+' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A+B")

    def test_rejects_name_with_star(self):
        """Sheet name containing '*' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A*B")

    def test_rejects_name_with_question(self):
        """Sheet name containing '?' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A?B")

    def test_rejects_name_with_exclamation(self):
        """Sheet name containing '!' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A!B")

    def test_rejects_name_with_pipe(self):
        """Sheet name containing '|' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A|B")

    def test_rejects_name_with_ampersand(self):
        """Sheet name containing '&' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A&B")

    def test_rejects_name_with_underscore_at_start(self):
        """Sheet name starting with '_' must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("_Sheet")

    def test_rejects_name_starting_with_digit(self):
        """Sheet name starting with a digit must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("1Sheet")

    def test_rejects_empty_string(self):
        """Empty sheet name must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("")

    def test_rejects_name_33_chars(self):
        """Sheet name longer than 32 characters must raise ValueError."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("A" * 33)

    def test_accepts_name_exactly_32_chars(self):
        """Sheet name of exactly 32 characters must be accepted."""
        h = self.wb.add_sheet("A" * 32)
        assert h is not None
        assert self.wb.sheet_names == ["A" * 32]

    def test_accepts_single_letter(self):
        """Single-letter sheet name must be accepted."""
        h = self.wb.add_sheet("A")
        assert h is not None
        assert self.wb.sheet_names == ["A"]

    def test_accepts_lowercase_start(self):
        """Sheet name starting with lowercase letter must be accepted."""
        h = self.wb.add_sheet("a")
        assert h is not None
        assert self.wb.sheet_names == ["a"]

    def test_accepts_mixed_case(self):
        """Sheet name with mixed case must be accepted."""
        h = self.wb.add_sheet("MySheet123")
        assert h is not None
        assert self.wb.sheet_names == ["MySheet123"]

    def test_accepts_underscore_in_middle(self):
        """Sheet name with underscore in middle must be accepted."""
        h = self.wb.add_sheet("My_Sheet")
        assert h is not None
        assert self.wb.sheet_names == ["My_Sheet"]

    def test_accepts_digit_in_middle(self):
        """Sheet name with digit in middle must be accepted."""
        h = self.wb.add_sheet("Sheet1")
        assert h is not None
        assert self.wb.sheet_names == ["Sheet1"]


# ---------------------------------------------------------------------------
# 2. eval_count preservation through undo/redo and re-creation
# ---------------------------------------------------------------------------

class TestEvalCountPreservation:
    """eval_count is kept per sheet name for workbook lifetime."""

    def test_eval_count_resumes_after_undo_redo(self):
        """eval_count resumes after undo/redo of add_sheet."""
        wb = Workbook()
        h = wb.add_sheet("S1")
        h.set("A1", 10)
        h.set("B1", "=A1+1")
        h.get("B1")  # trigger formula evaluation
        assert h.eval_count == 1  # one formula evaluation

        # Undo add_sheet S1
        wb.undo()  # undoes set B1
        wb.undo()  # undoes set A1
        wb.undo()  # undoes add_sheet S1
        assert wb.sheet_names == []

        # Redo add_sheet S1
        wb.redo()  # re-applies add_sheet S1 (with set A1)
        wb.redo()  # re-applies set B1 (with formula)
        # After redo, the sheet should have the same eval_count as before
        h = wb.sheet("S1")
        assert h.eval_count == 1

    def test_eval_count_resumes_after_fresh_re_creation(self):
        """eval_count resumes when sheet is re-created with same name."""
        wb = Workbook()
        h = wb.add_sheet("S1")
        h.set("A1", 10)
        h.set("B1", "=A1+1")
        h.get("B1")  # trigger formula evaluation
        assert h.eval_count == 1

        # Remove S1
        wb.undo()  # undoes set B1
        wb.undo()  # undoes set A1
        wb.undo()  # undoes add_sheet S1
        assert wb.sheet_names == []

        # Re-create S1 with fresh add_sheet
        h2 = wb.add_sheet("S1")
        # eval_count should resume from previous value
        assert h2.eval_count == 1

    def test_eval_count_independent_per_name(self):
        """eval_count is tracked independently per sheet name."""
        wb = Workbook()
        h1 = wb.add_sheet("S1")
        h2 = wb.add_sheet("S2")

        h1.set("A1", 10)
        h1.set("B1", "=A1+1")
        h1.get("B1")  # trigger formula evaluation
        assert h1.eval_count == 1

        h2.set("A1", 20)
        h2.set("B1", "=A1+1")
        h2.get("B1")  # trigger formula evaluation
        assert h2.eval_count == 1

        # Remove both
        wb.undo()  # undoes set S2/B1
        wb.undo()  # undoes set S2/A1
        wb.undo()  # undoes add_sheet S2
        wb.undo()  # undoes set S1/B1
        wb.undo()  # undoes set S1/A1
        wb.undo()  # undoes add_sheet S1
        assert wb.sheet_names == []

        # Re-create S1
        h1_new = wb.add_sheet("S1")
        assert h1_new.eval_count == 1  # resumed from S1's previous count

        # Re-create S2
        h2_new = wb.add_sheet("S2")
        assert h2_new.eval_count == 1  # resumed from S2's previous count

    def test_eval_count_monotonic_per_name(self):
        """eval_count is monotonically non-decreasing per name."""
        wb = Workbook()
        h = wb.add_sheet("S1")

        initial = h.eval_count
        h.set("A1", 10)
        h.set("B1", "=A1+1")
        h.get("B1")  # trigger formula evaluation
        assert h.eval_count > initial

        h.set("C1", "=B1+1")
        h.get("C1")  # trigger formula evaluation
        assert h.eval_count > initial

    def test_eval_count_zero_for_new_sheet(self):
        """A brand new sheet (never seen before) has eval_count 0."""
        wb = Workbook()
        h = wb.add_sheet("S1")
        assert h.eval_count == 0

    def test_eval_count_after_multiple_undo_redo_cycles(self):
        """eval_count survives multiple undo/redo cycles."""
        wb = Workbook()
        h = wb.add_sheet("S1")
        h.set("A1", 10)
        h.set("B1", "=A1+1")
        h.get("B1")  # trigger formula evaluation
        assert h.eval_count == 1

        # Undo and redo multiple times
        wb.undo()  # undoes set B1
        wb.undo()  # undoes set A1
        wb.undo()  # undoes add_sheet S1
        assert wb.sheet_names == []

        wb.redo()  # re-applies add_sheet S1
        wb.redo()  # re-applies set A1
        wb.redo()  # re-applies set B1
        h = wb.sheet("S1")
        assert h.eval_count == 1

        # Undo again
        wb.undo()  # undoes set B1
        wb.undo()  # undoes set A1
        wb.undo()  # undoes add_sheet S1
        assert wb.sheet_names == []

        # Redo again
        wb.redo()  # re-applies add_sheet S1
        wb.redo()  # re-applies set A1
        wb.redo()  # re-applies set B1
        h = wb.sheet("S1")
        assert h.eval_count == 1


# ---------------------------------------------------------------------------
# 3. String subclass normalization (verifier finding 2)
# ---------------------------------------------------------------------------

class TestStringSubclassNormalization:
    """Every API string argument accepts str subclasses, normalizes to plain str."""

    def setup_method(self):
        self.wb = Workbook()

    def test_add_sheet_normalizes_str_subclass_name(self):
        """add_sheet normalizes str subclass name to plain str."""
        class MyStr(str):
            pass
        h = self.wb.add_sheet(MyStr("S1"))
        assert h is not None
        assert type(self.wb.sheet_names[0]) is str

    def test_sheet_normalizes_str_subclass_name(self):
        """sheet() normalizes str subclass name to plain str."""
        class MyStr(str):
            pass
        self.wb.add_sheet("S1")
        h = self.wb.sheet(MyStr("S1"))
        assert h is not None

    def test_set_normalizes_str_subclass_address(self):
        """set() normalizes str subclass address to plain str."""
        class MyStr(str):
            pass
        h = self.wb.add_sheet("S1")
        h.set(MyStr("A1"), 10)
        # Verify the cell was stored with plain str key
        assert "A1" in h._cells
        assert type(list(h._cells.keys())[0]) is str

    def test_get_normalizes_str_subclass_address(self):
        """get() normalizes str subclass address to plain str."""
        class MyStr(str):
            pass
        h = self.wb.add_sheet("S1")
        h.set("A1", 10)
        result = h.get(MyStr("A1"))
        assert result == 10

    def test_copy_normalizes_str_subclass_addresses(self):
        """copy() normalizes str subclass src/dst addresses to plain str."""
        class MyStr(str):
            pass
        h = self.wb.add_sheet("S1")
        h.set("A1", 10)
        h.copy(MyStr("A1"), MyStr("B1"))
        # Verify cells stored with plain str keys
        assert "A1" in h._cells
        assert "B1" in h._cells
        assert type(list(h._cells.keys())[0]) is str
        assert type(list(h._cells.keys())[1]) is str

    def test_define_name_normalizes_str_subclass_name_and_target(self):
        """define_name() normalizes str subclass name and target to plain str."""
        class MyStr(str):
            pass
        h = self.wb.add_sheet("S1")
        h.define_name(MyStr("MYNAME"), MyStr("A1"))
        # Verify name and target stored as plain str
        assert "MYNAME" in h._names
        assert type(list(h._names.keys())[0]) is str
        assert type(h._names["MYNAME"]) is str

    def test_set_normalizes_str_subclass_raw_value(self):
        """set() normalizes str subclass raw value to plain str."""
        class MyStr(str):
            pass
        h = self.wb.add_sheet("S1")
        h.set("A1", MyStr("hello"))
        result = h.get("A1")
        assert result == "hello"
        assert type(result) is str

    def test_sheet_names_returns_plain_str_after_subclass_operations(self):
        """sheet_names returns plain str after str subclass operations."""
        class MyStr(str):
            pass
        self.wb.add_sheet(MyStr("S1"))
        h = self.wb.add_sheet("S2")
        h.set(MyStr("A1"), 10)
        h.copy(MyStr("A1"), MyStr("B1"))
        h.define_name(MyStr("MYNAME"), MyStr("A1"))

        # All sheet names should be plain str
        for name in self.wb.sheet_names:
            assert type(name) is str

    def test_from_json_accepts_str_subclass(self):
        """from_json() accepts str subclass input."""
        class MyStr(str):
            pass
        wb = Workbook.from_json(MyStr('{"version":1,"clock":0,"sheets":[]}'))
        assert isinstance(wb, Workbook)
