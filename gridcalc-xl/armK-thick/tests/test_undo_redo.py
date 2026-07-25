"""Task 7.1: Mutation journal mixed-history undo/redo — R19."""
import pytest

from gridcalc import Workbook


def _sheet():
    wb = Workbook()
    return wb, wb.add_sheet("S1")


# ---------------------------------------------------------------------------
# 1. copy undo/redo
# ---------------------------------------------------------------------------

class TestCopyUndoRedo:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_copy_journals_and_undo_restores_prior_value(self):
        """Undoing a copy restores the destination's prior value."""
        self.h.set("A1", 10)
        self.h.set("B1", 99)
        self.h.copy("A1", "B1")
        assert self.h.get("B1") == 10
        assert self.wb.undo() is True
        assert self.h.get("B1") == 99

    def test_copy_undo_restores_never_set_state(self):
        """Undoing a copy to a never-set cell restores never-set state."""
        self.h.set("A1", 10)
        # B1 is never set
        self.h.copy("A1", "B1")
        assert self.h.get("B1") == 10
        assert self.wb.undo() is True
        assert self.h.get("B1") is None

    def test_copy_undo_redo_cycle(self):
        """Full undo/redo cycle for copy."""
        self.h.set("A1", 10)
        self.h.copy("A1", "B1")
        assert self.h.get("B1") == 10
        assert self.wb.undo() is True
        assert self.h.get("B1") is None
        assert self.wb.redo() is True
        assert self.h.get("B1") == 10

    def test_copy_redo_returns_false_when_nothing_to_redo(self):
        """redo returns False when redo stack is empty."""
        self.h.set("A1", 10)
        assert self.wb.redo() is False

    def test_copy_new_journaled_op_clears_redo(self):
        """A new journaled op clears the redo stack after copy undo."""
        self.h.set("A1", 10)
        self.h.copy("A1", "B1")
        assert self.wb.undo() is True
        assert self.h.get("B1") is None
        # Redo works
        assert self.wb.redo() is True
        assert self.h.get("B1") == 10
        # New journaled op clears redo
        self.h.set("B1", 0)
        assert self.h.get("B1") == 0
        assert self.wb.redo() is False

    def test_copy_new_journaled_op_clears_nonempty_redo(self):
        """A new journaled op clears a non-empty redo stack after copy."""
        self.h.set("A1", 10)
        self.h.copy("A1", "B1")
        self.h.copy("A1", "C1")
        assert self.wb.undo() is True  # undoes C1 copy
        assert self.h.get("C1") is None
        assert self.h.get("B1") == 10
        # Redo works
        assert self.wb.redo() is True
        assert self.h.get("C1") == 10
        # Undo again to put C1 copy back on redo stack
        assert self.wb.undo() is True
        assert self.h.get("C1") is None
        # New journaled op clears redo
        self.h.set("D1", 1)
        assert self.wb.redo() is False
        assert self.h.get("B1") == 10
        assert self.h.get("C1") is None

    def test_copy_formula_cell_undo_restores_prior(self):
        """Undoing a copy of a formula cell restores the prior destination value."""
        self.h.set("A1", 10)
        self.h.set("B1", "=A1+1")
        assert self.h.get("B1") == 11
        self.h.copy("A1", "B1")
        assert self.h.get("B1") == 10
        assert self.wb.undo() is True
        assert self.h.get("B1") == 11

    def test_failed_copy_does_not_journal(self):
        """Failed copy (empty source) must not be journaled."""
        # A1 is never set, so copy from A1 fails.
        self.h.set("B1", 99)
        with pytest.raises(Exception):
            self.h.copy("A1", "B1")
        # Only add_sheet and set B1 are journaled.
        assert self.wb.undo() is True  # undoes set B1
        assert self.h.get("B1") is None
        assert self.wb.undo() is True  # undoes add_sheet S1
        assert self.wb.sheet_names == []


# ---------------------------------------------------------------------------
# 2. define_name undo/redo
# ---------------------------------------------------------------------------

class TestDefineNameUndoRedo:
    def setup_method(self):
        self.wb, self.h = _sheet()

    def test_define_name_journals_and_undo_restores_undefined(self):
        """Undoing a define_name on a previously undefined name restores undefined."""
        self.h.set("A1", 42)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 42
        # Undo set B1, then undo define_name MYCELL
        assert self.wb.undo() is True  # undoes set B1==MYCELL
        assert self.wb.undo() is True  # undoes define_name MYCELL=A1
        assert "MYCELL" not in self.h._names
        self.h.set("C1", "=MYCELL")
        from gridcalc.formula import NAME_ERROR
        assert self.h.get("C1") == NAME_ERROR

    def test_define_name_undo_restores_prior_binding(self):
        """Undoing a redefine restores the previous binding."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.define_name("MYCELL", "B1")
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 20
        # Undo set C1, then undo define_name MYCELL=B1
        assert self.wb.undo() is True  # undoes set C1==MYCELL
        assert self.wb.undo() is True  # undoes define_name MYCELL=B1
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 10

    def test_define_name_undo_redo_cycle(self):
        """Full undo/redo cycle for define_name."""
        self.h.set("A1", 42)
        self.h.define_name("MYCELL", "A1")
        self.h.set("B1", "=MYCELL")
        assert self.h.get("B1") == 42
        # Undo set B1, then undo define_name MYCELL
        assert self.wb.undo() is True  # undoes set B1==MYCELL
        assert self.wb.undo() is True  # undoes define_name MYCELL=A1
        assert "MYCELL" not in self.h._names
        # Redo define_name MYCELL
        assert self.wb.redo() is True
        self.h.set("C1", "=MYCELL")
        assert self.h.get("C1") == 42

    def test_define_name_redo_returns_false_when_nothing_to_redo(self):
        """redo returns False when redo stack is empty."""
        assert self.wb.redo() is False

    def test_define_name_new_journaled_op_clears_redo(self):
        """A new journaled op clears the redo stack after define_name undo."""
        self.h.set("A1", 42)
        self.h.define_name("MYCELL", "A1")
        assert self.wb.undo() is True
        assert "MYCELL" not in self.h._names
        # Redo works
        assert self.wb.redo() is True
        # New journaled op clears redo
        self.h.define_name("MYCELL", "B1")
        assert self.wb.redo() is False

    def test_define_name_new_journaled_op_clears_nonempty_redo(self):
        """A new journaled op clears a non-empty redo stack after define_name."""
        self.h.set("A1", 10)
        self.h.set("B1", 20)
        self.h.define_name("MYCELL", "A1")
        self.h.define_name("MYCELL", "B1")
        assert self.wb.undo() is True  # undoes B1 binding
        assert self.h.get("A1") == 10
        # Redo works
        assert self.wb.redo() is True
        # Undo again to put B1 binding back on redo stack
        assert self.wb.undo() is True
        assert self.h.get("A1") == 10
        # New journaled op clears redo
        self.h.set("C1", 1)
        assert self.wb.redo() is False

    def test_failed_define_name_does_not_journal(self):
        """Failed define_name must not be journaled."""
        self.h.set("A1", 10)
        with pytest.raises(ValueError):
            self.h.define_name("A", "A1")  # too short
        # Only add_sheet and set are journaled.
        assert self.wb.undo() is True  # undoes set A1
        assert self.h.get("A1") is None
        assert self.wb.undo() is True  # undoes add_sheet S1
        assert self.wb.sheet_names == []


# ---------------------------------------------------------------------------
# 3. Mixed-history strict LIFO
# ---------------------------------------------------------------------------

class TestMixedHistoryLIFO:
    def setup_method(self):
        self.wb = Workbook()

    def test_interleaved_set_copy_define_add_sheet_lifo(self):
        """Undo reverts interleaved set/copy/define_name/add_sheet in strict LIFO."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        s2 = self.wb.add_sheet("S2")
        s2.set("A1", 10)
        s1.copy("A1", "B1")
        s1.define_name("XX", "A1")
        # Journal: [add_sheet S1, set A1=1, add_sheet S2, set A1=10, copy A1->B1, define_name XX=A1]
        # Undo order: define_name, copy, set S2/A1=10, add_sheet S2, set S1/A1=1, add_sheet S1

        # 1. Undo define_name XX
        assert self.wb.undo() is True
        assert "XX" not in s1._names

        # 2. Undo copy A1->B1
        assert self.wb.undo() is True
        assert s1.get("B1") is None

        # 3. Undo set S2/A1=10
        assert self.wb.undo() is True
        assert s2.get("A1") is None

        # 4. Undo add_sheet S2
        assert self.wb.undo() is True
        assert "S2" not in self.wb.sheet_names

        # 5. Undo set S1/A1=1
        assert self.wb.undo() is True
        assert s1.get("A1") is None

        # 6. Undo add_sheet S1
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

        # 7. Nothing left to undo
        assert self.wb.undo() is False

    def test_interleaved_with_redefinitions_and_overwrites_lifo(self):
        """Undo reverts redefinitions and overwrites in strict LIFO."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        s1.set("A1", 2)
        s1.define_name("XX", "A1")
        s1.define_name("XX", "B1")
        s1.copy("A1", "C1")
        # Journal: [add_sheet S1, set A1=1, set A1=2, define XX=A1, define XX=B1, copy A1->C1]
        # Undo order: copy, define XX=B1, define XX=A1, set A1=2, set A1=1, add_sheet S1

        # 1. Undo copy
        assert self.wb.undo() is True
        assert s1.get("C1") is None

        # 2. Undo define XX=B1
        assert self.wb.undo() is True
        assert s1._names["XX"] == "A1"

        # 3. Undo define XX=A1
        assert self.wb.undo() is True
        assert "XX" not in s1._names

        # 4. Undo set A1=2
        assert self.wb.undo() is True
        assert s1.get("A1") == 1

        # 5. Undo set A1=1
        assert self.wb.undo() is True
        assert s1.get("A1") is None

        # 6. Undo add_sheet S1
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

        # 7. Nothing left to undo
        assert self.wb.undo() is False

    def test_redo_lifo_for_mixed_history(self):
        """Redo re-applies mixed history in strict LIFO order."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        s2 = self.wb.add_sheet("S2")
        s2.set("A1", 10)
        s1.copy("A1", "B1")
        s1.define_name("XX", "A1")
        # Undo all (6 entries)
        self.wb.undo()  # undoes define_name XX
        self.wb.undo()  # undoes copy A1->B1
        self.wb.undo()  # undoes set S2/A1=10
        self.wb.undo()  # undoes add_sheet S2
        self.wb.undo()  # undoes set S1/A1=1
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []

        # Redo pops from redo stack in LIFO: add_sheet S1, set S1/A1=1,
        # add_sheet S2, set S2/A1=10, copy A1->B1, define_name XX=A1
        assert self.wb.redo() is True
        assert self.wb.sheet_names == ["S1"]
        s1 = self.wb.sheet("S1")

        assert self.wb.redo() is True
        assert s1.get("A1") == 1

        assert self.wb.redo() is True
        assert "S2" in self.wb.sheet_names
        s2 = self.wb.sheet("S2")

        assert self.wb.redo() is True
        assert s2.get("A1") == 10

        assert self.wb.redo() is True
        assert s1.get("B1") == 1

        assert self.wb.redo() is True
        assert s1._names["XX"] == "A1"

        # Nothing left to redo
        assert self.wb.redo() is False

    def test_new_journaled_op_clears_redo_mixed(self):
        """A new journaled op clears the redo stack in mixed history."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        # Journal: [add_sheet S1, set S1/A1=1]
        # Undo the set
        self.wb.undo()  # undoes set S1/A1=1
        assert s1.get("A1") is None
        # Redo stack has 1 entry: set S1/A1=1
        assert self.wb.redo() is True
        # New journaled op clears redo
        s1.set("A1", 99)
        assert s1.get("A1") == 99
        assert self.wb.redo() is False


# ---------------------------------------------------------------------------
# 4. Handle lifecycle through mixed undo/redo
# ---------------------------------------------------------------------------

class TestHandleLifecycleMixed:
    def setup_method(self):
        self.wb = Workbook()

    def test_handle_invalid_after_undo_add_sheet_in_mixed_sequence(self):
        """Handle raised ValueError after its sheet is undone in mixed sequence."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        s2 = self.wb.add_sheet("S2")
        # Undo S2
        self.wb.undo()
        # s2 handle should be invalid
        with pytest.raises(ValueError):
            s2.get("A1")
        # s1 should still work
        assert s1.get("A1") == 1

    def test_handle_works_after_redo_restores_sheet_in_mixed_sequence(self):
        """Handle works again after redo restores the sheet in mixed sequence."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        s2 = self.wb.add_sheet("S2")
        s2.set("A1", 10)
        # Undo add_sheet S2 (need to undo set S2/A1=10 first, then add_sheet S2)
        self.wb.undo()  # undoes set S2/A1=10
        self.wb.undo()  # undoes add_sheet S2
        # s2 handle should be invalid
        with pytest.raises(ValueError):
            s2.get("A1")
        # Redo add_sheet S2
        self.wb.redo()  # re-applies add_sheet S2
        # s2 handle should work again
        assert s2.get("A1") is None  # set was also undone, so A1 is None

    def test_handle_is_same_object_after_redo_add_sheet(self):
        """After redo, the original handle is the same object as wb.sheet(name)."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        s2 = self.wb.add_sheet("S2")
        s2.set("A1", 10)
        # Undo S2
        self.wb.undo()
        # Redo S2
        self.wb.redo()
        assert s2 is self.wb.sheet("S2")
