"""Task 6.1: Mutation journal foundation — R19 tests."""
import pytest

from gridcalc import Workbook


# ---------------------------------------------------------------------------
# 1. add_sheet journals and is undoable/redoable
# ---------------------------------------------------------------------------

class TestAddSheetJournaling:
    def setup_method(self):
        self.wb = Workbook()

    def test_add_sheet_journals_successful_operation(self):
        """add_sheet must be journaled so undo can revert it."""
        h = self.wb.add_sheet("S1")
        assert h is not None
        # Undo should revert the add_sheet.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

    def test_add_sheet_undo_redo_cycle(self):
        """Full undo/redo cycle for add_sheet."""
        self.wb.add_sheet("S1")
        assert self.wb.sheet_names == ["S1"]
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []
        assert self.wb.redo() is True
        assert self.wb.sheet_names == ["S1"]

    def test_add_sheet_redo_returns_false_when_nothing_to_redo(self):
        """redo returns False when redo stack is empty."""
        wb = Workbook()
        assert wb.redo() is False  # Nothing ever added

    def test_add_sheet_new_journaled_op_clears_redo_stack(self):
        """A new journaled operation clears the redo stack."""
        self.wb.add_sheet("S1")
        self.wb.add_sheet("S2")
        self.wb.undo()  # undoes S2
        self.wb.undo()  # undoes S1
        self.wb.undo()  # False, nothing to undo
        assert self.wb.undo() is False
        # Now redo S1
        self.wb.redo()  # re-applies S1
        assert self.wb.sheet_names == ["S1"]
        # New journaled op should clear redo
        self.wb.add_sheet("S3")
        assert self.wb.sheet_names == ["S1", "S3"]
        # Redo stack should be empty
        assert self.wb.redo() is False


# ---------------------------------------------------------------------------
# 2. set journals and is undoable/redoable
# ---------------------------------------------------------------------------

class TestSetJournaling:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_set_journals_successful_operation(self):
        """set must be journaled so undo can revert it."""
        self.h.set("A1", 1)
        assert self.h.get("A1") == 1
        # Undo should revert the set (restore to never-set).
        assert self.wb.undo() is True
        assert self.h.get("A1") is None

    def test_set_undo_redo_cycle(self):
        """Full undo/redo cycle for set."""
        self.h.set("A1", 1)
        assert self.h.get("A1") == 1
        assert self.wb.undo() is True
        assert self.h.get("A1") is None
        assert self.wb.redo() is True
        assert self.h.get("A1") == 1

    def test_set_redo_returns_false_when_nothing_to_redo(self):
        """redo returns False when redo stack is empty."""
        assert self.wb.redo() is False  # Nothing undone yet

    def test_set_new_journaled_op_clears_redo_stack(self):
        """A new journaled set clears the redo stack."""
        self.h.set("A1", 1)
        self.wb.undo()  # undoes set
        assert self.h.get("A1") is None
        # Redo should work
        assert self.wb.redo() is True
        assert self.h.get("A1") == 1
        # New journaled op clears redo
        self.h.set("A1", 2)
        assert self.h.get("A1") == 2
        assert self.wb.redo() is False

    def test_set_new_journaled_op_clears_nonempty_redo_stack(self):
        """A new journaled set clears a non-empty redo stack (verifier-required case)."""
        self.h.set("A1", 1)
        self.h.set("A2", 2)
        self.wb.undo()  # undoes A2=2, pushes to redo stack
        assert self.h.get("A2") is None
        assert self.h.get("A1") == 1
        # Redo stack is non-empty (contains A2=2)
        assert self.wb.redo() is True
        assert self.h.get("A2") == 2
        # Undo again to put A2=2 back on redo stack
        self.wb.undo()  # undoes A2=2 again
        assert self.h.get("A2") is None
        # Now a new set should clear the redo stack
        self.h.set("A3", 3)
        assert self.h.get("A3") == 3
        # Redo stack should be empty now
        assert self.wb.redo() is False
        # A2 should remain undone
        assert self.h.get("A2") is None

    def test_set_does_not_journal_failed_call(self):
        """Failed set (ValueError) must not be journaled."""
        # Invalid address raises ValueError, should not journal.
        with pytest.raises(ValueError):
            self.h.set("Bad!", 1)
        # Undo should not revert anything related to the failed set.
        # The only journal entry is add_sheet, so undo removes the sheet.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

    def test_set_bool_rejected_and_not_journaled(self):
        """Setting a bool raises ValueError and is not journaled."""
        with pytest.raises(ValueError):
            self.h.set("A1", True)
        # Only add_sheet is journaled, undo removes the sheet.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []


# ---------------------------------------------------------------------------
# 3. Non-journaling operations
# ---------------------------------------------------------------------------

class TestNonJournalingOperations:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_get_does_not_journal(self):
        """get() is an observation, never journals."""
        self.h.set("A1", 1)
        self.h.get("A1")
        # Only add_sheet and set are journaled.
        assert self.wb.undo() is True  # undoes set
        assert self.h.get("A1") is None

    def test_sheet_does_not_journal(self):
        """sheet() is an observation, never journals."""
        self.wb.sheet("S1")
        # Only add_sheet is journaled.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

    def test_sheet_names_does_not_journal(self):
        """sheet_names is an observation, never journals."""
        self.wb.sheet_names
        # Only add_sheet is journaled.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []


# ---------------------------------------------------------------------------
# 4. Undo/redo restore prior cell contents including never-set state
# ---------------------------------------------------------------------------

class TestUndoRedoCellContents:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_undo_restores_never_set_state(self):
        """Undoing a set on a never-set cell restores never-set state."""
        self.h.set("A1", 42)
        assert self.h.get("A1") == 42
        self.wb.undo()
        assert self.h.get("A1") is None

    def test_undo_restores_prior_value(self):
        """Undoing a set restores the previous value."""
        self.h.set("A1", 1)
        self.h.set("A1", 2)
        assert self.h.get("A1") == 2
        self.wb.undo()
        assert self.h.get("A1") == 1

    def test_undo_restores_prior_value_string(self):
        """Undoing a set on a string cell restores the previous string."""
        self.h.set("A1", "hello")
        self.h.set("A1", "world")
        assert self.h.get("A1") == "world"
        self.wb.undo()
        assert self.h.get("A1") == "hello"

    def test_redo_reapplies_set(self):
        """Redo re-applies the most recently undone set."""
        self.h.set("A1", 1)
        self.wb.undo()
        assert self.h.get("A1") is None
        self.wb.redo()
        assert self.h.get("A1") == 1

    def test_redo_reapplies_set_after_overwrite(self):
        """Redo re-applies the set even after the cell was overwritten."""
        self.h.set("A1", 1)
        self.h.set("A1", 2)
        self.wb.undo()  # undoes A1=2
        assert self.h.get("A1") == 1
        self.wb.redo()  # re-applies A1=2
        assert self.h.get("A1") == 2


# ---------------------------------------------------------------------------
# 5. Strict LIFO order
# ---------------------------------------------------------------------------

class TestLIFOOrder:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("Sheet")

    def test_undo_lifo_for_cells(self):
        """Undo reverts in strict LIFO order for cell sets."""
        self.h.set("A1", 1)
        self.h.set("A2", 2)
        self.h.set("A3", 3)
        # Undo should revert A3 first.
        self.wb.undo()
        assert self.h.get("A3") is None
        assert self.h.get("A2") == 2
        assert self.h.get("A1") == 1
        # Then A2.
        self.wb.undo()
        assert self.h.get("A3") is None
        assert self.h.get("A2") is None
        assert self.h.get("A1") == 1
        # Then A1.
        self.wb.undo()
        assert self.h.get("A1") is None

    def test_undo_lifo_for_sheets(self):
        """Undo reverts in strict LIFO order for add_sheet."""
        wb = Workbook()
        wb.add_sheet("S1")
        wb.add_sheet("S2")
        wb.add_sheet("S3")
        # Undo should remove S3 first.
        wb.undo()
        assert wb.sheet_names == ["S1", "S2"]
        # Then S2.
        wb.undo()
        assert wb.sheet_names == ["S1"]
        # Then S1.
        wb.undo()
        assert wb.sheet_names == []

    def test_interleaved_undo_lifo(self):
        """Undo reverts interleaved set/add_sheet in strict LIFO."""
        wb = Workbook()
        h = wb.add_sheet("S1")
        h.set("A1", 1)
        wb.add_sheet("S2")
        # Journal: [add_sheet S1, set A1=1, add_sheet S2]
        # Undo should revert add_sheet S2 first.
        wb.undo()
        assert wb.sheet_names == ["S1"]
        # Then set A1=1.
        wb.undo()
        assert h.get("A1") is None
        # Then add_sheet S1.
        wb.undo()
        assert wb.sheet_names == []

    def test_redo_lifo_for_cells(self):
        """Redo re-applies in strict LIFO order from redo stack."""
        self.h.set("A1", 1)
        self.h.set("A2", 2)
        self.h.set("A3", 3)
        # Undo all (pops from journal, pushes to redo).
        self.wb.undo()  # undoes A3=3
        self.wb.undo()  # undoes A2=2
        self.wb.undo()  # undoes A1=1
        assert self.h.get("A1") is None
        assert self.h.get("A2") is None
        assert self.h.get("A3") is None
        # Redo pops from redo stack in LIFO: A1, A2, A3.
        self.wb.redo()
        assert self.h.get("A1") == 1
        assert self.h.get("A2") is None
        assert self.h.get("A3") is None
        self.wb.redo()
        assert self.h.get("A1") == 1
        assert self.h.get("A2") == 2
        assert self.h.get("A3") is None
        self.wb.redo()
        assert self.h.get("A1") == 1
        assert self.h.get("A2") == 2
        assert self.h.get("A3") == 3


# ---------------------------------------------------------------------------
# 6. Sheet handles bound to name
# ---------------------------------------------------------------------------

class TestSheetHandleBinding:
    def setup_method(self):
        self.wb = Workbook()

    def test_handle_eval_count_raises_when_sheet_removed(self):
        """Accessing eval_count on a handle whose sheet was removed raises ValueError."""
        h = self.wb.add_sheet("S1")
        self.wb.undo()  # removes S1
        with pytest.raises(ValueError):
            h.eval_count

    def test_handle_works_again_after_redo(self):
        """Handle works again after redo restores the sheet name."""
        h = self.wb.add_sheet("S1")
        self.wb.undo()  # removes S1
        self.wb.redo()  # restores S1
        assert h.eval_count == 0

    def test_handle_works_again_after_fresh_add_sheet(self):
        """Handle works again after a fresh add_sheet restores the name."""
        h = self.wb.add_sheet("S1")
        self.wb.undo()  # removes S1
        self.wb.add_sheet("S1")  # fresh add
        assert h.eval_count == 0

    def test_handle_set_raises_when_sheet_removed(self):
        """Calling set on a handle whose sheet was removed raises ValueError."""
        h = self.wb.add_sheet("S1")
        self.wb.undo()  # removes S1
        with pytest.raises(ValueError):
            h.set("A1", 1)

    def test_handle_get_raises_when_sheet_removed(self):
        """Calling get on a handle whose sheet was removed raises ValueError."""
        h = self.wb.add_sheet("S1")
        self.wb.undo()  # removes S1
        with pytest.raises(ValueError):
            h.get("A1")


# ---------------------------------------------------------------------------
# 7. Undo/redo on add_sheet restores sheets
# ---------------------------------------------------------------------------

class TestAddSheetUndoRedo:
    def setup_method(self):
        self.wb = Workbook()

    def test_undo_add_sheet_removes_sheet(self):
        """Undoing add_sheet removes the sheet."""
        self.wb.add_sheet("S1")
        assert self.wb.sheet_names == ["S1"]
        self.wb.undo()
        assert self.wb.sheet_names == []

    def test_redo_add_sheet_recreates_sheet(self):
        """Redoing add_sheet recreates the sheet."""
        self.wb.add_sheet("S1")
        self.wb.undo()
        assert self.wb.sheet_names == []
        self.wb.redo()
        assert self.wb.sheet_names == ["S1"]

    def test_redo_add_sheet_handle_works(self):
        """Handle from before undo works after redo restores the sheet."""
        h = self.wb.add_sheet("S1")
        h.set("A1", 1)
        self.wb.undo()  # removes S1
        self.wb.redo()  # restores S1
        assert h.get("A1") == 1

    def test_redo_add_sheet_handle_is_same_object_as_sheet(self):
        """After redo, the original handle must be the same object as wb.sheet(name)."""
        h = self.wb.add_sheet("S1")
        self.wb.undo()  # removes S1 (undoes the add_sheet itself)
        self.wb.redo()  # restores S1
        # h must be the same object returned by wb.sheet("S1")
        assert h is self.wb.sheet("S1"), f"h is {h!r}, wb.sheet('S1') is {self.wb.sheet('S1')!r}"
        # Writing through h must be visible through wb.sheet("S1")
        h.set("A2", 7)
        assert self.wb.sheet("S1").get("A2") == 7

    def test_undo_add_sheet_with_data_restores_empty_sheet(self):
        """Undoing add_sheet removes the sheet entirely (data lost)."""
        h = self.wb.add_sheet("S1")
        h.set("A1", 42)
        self.wb.undo()  # undoes set A1=42
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []
        # Can't access h anymore since sheet is gone.
        with pytest.raises(ValueError):
            h.get("A1")


# ---------------------------------------------------------------------------
# 8. Failed calls never journal
# ---------------------------------------------------------------------------

class TestFailedCallsNeverJournal:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_failed_add_sheet_does_not_journal(self):
        """Failed add_sheet (duplicate name) must not be journaled."""
        with pytest.raises(ValueError):
            self.wb.add_sheet("S1")
        # Only add_sheet S1 is journaled, undo removes it.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

    def test_failed_get_does_not_journal(self):
        """Failed get (invalid address) must not be journaled."""
        self.h.set("A1", 1)
        with pytest.raises(ValueError):
            self.h.get("Bad!")
        # Only add_sheet and set are journaled.
        assert self.wb.undo() is True  # undoes set
        assert self.h.get("A1") is None

    def test_failed_sheet_does_not_journal(self):
        """Failed sheet (unknown name) must not be journaled."""
        with pytest.raises(ValueError):
            self.wb.sheet("Nope")
        # Only add_sheet is journaled.
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

    def test_failed_add_sheet_then_undo_no_double_remove(self):
        """After failed add_sheet, undo should only remove the original sheet."""
        self.wb.add_sheet("S2")
        with pytest.raises(ValueError):
            self.wb.add_sheet("S1")  # fails, not journaled
        # Journal: [add_sheet S1, add_sheet S2]
        self.wb.undo()  # undoes S2
        assert self.wb.sheet_names == ["S1"]
        self.wb.undo()  # undoes S1
        assert self.wb.sheet_names == []

    def test_failed_set_then_undo_no_double_undo(self):
        """After failed set, undo should only remove the original set."""
        self.h.set("A1", 1)
        with pytest.raises(ValueError):
            self.h.set("Bad!", 2)  # fails, not journaled
        # Journal: [add_sheet S1, set A1=1]
        self.wb.undo()  # undoes set A1=1
        assert self.h.get("A1") is None
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []

    def test_failed_get_then_undo_no_double_undo(self):
        """After failed get, undo should only remove the original set."""
        self.h.set("A1", 1)
        with pytest.raises(ValueError):
            self.h.get("Bad!")  # fails, not journaled
        # Journal: [add_sheet S1, set A1=1]
        self.wb.undo()  # undoes set A1=1
        assert self.h.get("A1") is None
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []

    def test_failed_sheet_then_undo_no_double_undo(self):
        """After failed sheet, undo should only remove the original add_sheet."""
        with pytest.raises(ValueError):
            self.wb.sheet("Nope")  # fails, not journaled
        # Journal: [add_sheet S1]
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []


# ---------------------------------------------------------------------------
# 9. Formula cache invalidation on undo/redo
# ---------------------------------------------------------------------------

class TestFormulaCacheInvalidation:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_undo_set_invalidates_formula_cache(self):
        """Undoing a set that a formula depends on must invalidate the formula cache."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        assert self.h.get("B1") == 2
        self.h.set("A1", 2)
        assert self.h.get("B1") == 3
        self.wb.undo()  # undoes A1=2, restoring A1=1
        assert self.h.get("B1") == 2

    def test_redo_set_invalidates_formula_cache(self):
        """Redoing a set that a formula depends on must invalidate the formula cache."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        assert self.h.get("B1") == 2
        self.h.set("A1", 2)
        assert self.h.get("B1") == 3
        self.wb.undo()  # undoes A1=2, restoring A1=1
        assert self.h.get("B1") == 2
        self.wb.redo()  # re-applies A1=2
        assert self.h.get("B1") == 3
