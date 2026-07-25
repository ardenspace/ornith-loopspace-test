"""Task 9.1: Clock API for persisted state — R19, R20, R26."""
import pytest

from gridcalc import Workbook


# ---------------------------------------------------------------------------
# 1. wb.clock starts at 0 and is read-only
# ---------------------------------------------------------------------------

class TestClockInitialReadOnly:
    def setup_method(self):
        self.wb = Workbook()

    def test_clock_starts_at_zero(self):
        """wb.clock must be 0 on a fresh workbook."""
        assert self.wb.clock == 0

    def test_clock_is_read_only_property(self):
        """wb.clock must be a read-only property (cannot be set)."""
        with pytest.raises(AttributeError):
            self.wb.clock = 5

    def test_clock_property_returns_int(self):
        """wb.clock must return an int."""
        assert isinstance(self.wb.clock, int)


# ---------------------------------------------------------------------------
# 2. advance_clock() increments by exactly 1, returns new value, journals
# ---------------------------------------------------------------------------

class TestAdvanceClock:
    def setup_method(self):
        self.wb = Workbook()

    def test_advance_clock_increments_by_one(self):
        """advance_clock() must increment clock by exactly 1."""
        assert self.wb.clock == 0
        self.wb.advance_clock()
        assert self.wb.clock == 1
        self.wb.advance_clock()
        assert self.wb.clock == 2

    def test_advance_clock_returns_new_value(self):
        """advance_clock() must return the new clock value."""
        assert self.wb.advance_clock() == 1
        assert self.wb.advance_clock() == 2
        assert self.wb.advance_clock() == 3

    def test_advance_clock_journals_successful_operation(self):
        """advance_clock() must be journaled so undo can revert it."""
        self.wb.advance_clock()
        assert self.wb.clock == 1
        assert self.wb.undo() is True
        assert self.wb.clock == 0

    def test_advance_clock_journals_multiple_operations(self):
        """Multiple advance_clock calls each produce a journal entry."""
        self.wb.advance_clock()
        self.wb.advance_clock()
        self.wb.advance_clock()
        assert self.wb.clock == 3
        # Undo in LIFO order.
        assert self.wb.undo() is True
        assert self.wb.clock == 2
        assert self.wb.undo() is True
        assert self.wb.clock == 1
        assert self.wb.undo() is True
        assert self.wb.clock == 0

    def test_advance_clock_redo_reapplies(self):
        """redo() must re-apply the most recently undone advance_clock."""
        self.wb.advance_clock()
        self.wb.advance_clock()
        assert self.wb.clock == 2
        assert self.wb.undo() is True
        assert self.wb.clock == 1
        assert self.wb.redo() is True
        assert self.wb.clock == 2

    def test_advance_clock_redo_returns_false_when_nothing_to_redo(self):
        """redo() returns False when redo stack is empty."""
        assert self.wb.redo() is False

    def test_advance_clock_new_journaled_op_clears_redo(self):
        """A new journaled op clears the redo stack after clock undo."""
        self.wb.advance_clock()
        assert self.wb.clock == 1
        assert self.wb.undo() is True
        assert self.wb.clock == 0
        # Redo works.
        assert self.wb.redo() is True
        assert self.wb.clock == 1
        # New journaled op clears redo.
        self.wb.advance_clock()
        assert self.wb.clock == 2
        assert self.wb.redo() is False

    def test_advance_clock_new_journaled_op_clears_nonempty_redo(self):
        """A new journaled op clears a non-empty redo stack after clock undo."""
        self.wb.advance_clock()
        self.wb.advance_clock()
        self.wb.advance_clock()
        assert self.wb.clock == 3
        # Undo twice to build a non-empty redo stack.
        assert self.wb.undo() is True  # undoes clock=3
        assert self.wb.clock == 2
        assert self.wb.undo() is True  # undoes clock=2
        assert self.wb.clock == 1
        # Redo stack has 2 entries.
        assert self.wb.redo() is True  # re-applies clock=2
        assert self.wb.clock == 2
        # Undo again to put clock=2 back on redo stack.
        assert self.wb.undo() is True
        assert self.wb.clock == 1
        # New journaled op clears redo.
        self.wb.advance_clock()
        assert self.wb.clock == 2
        assert self.wb.redo() is False


# ---------------------------------------------------------------------------
# 3. advance_clock never evaluates formulas and does not change eval_count
# ---------------------------------------------------------------------------

class TestAdvanceClockNoEval:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_advance_clock_does_not_change_eval_count(self):
        """advance_clock() must not change any sheet's eval_count."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        assert self.h.get("B1") == 2
        before = self.h.eval_count
        self.wb.advance_clock()
        assert self.h.eval_count == before

    def test_advance_clock_does_not_evaluate_formulas(self):
        """advance_clock() must not trigger any formula evaluation."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        # Force evaluation.
        self.h.get("B1")
        before = self.h.eval_count
        # advance_clock should not cause any evaluation.
        self.wb.advance_clock()
        assert self.h.eval_count == before

    def test_advance_clock_no_eval_across_sheets(self):
        """advance_clock() must not change eval_count on any sheet."""
        s2 = self.wb.add_sheet("S2")
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        s2.set("A1", 10)
        s2.set("B1", "=A1+5")
        self.h.get("B1")
        s2.get("B1")
        before_s1 = self.h.eval_count
        before_s2 = s2.eval_count
        self.wb.advance_clock()
        assert self.h.eval_count == before_s1
        assert s2.eval_count == before_s2


# ---------------------------------------------------------------------------
# 4. undo/redo of advance_clock restores/reapplies without appending entries
# ---------------------------------------------------------------------------

class TestClockUndoRedoNoExtraEntries:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_undo_advance_clock_does_not_append_journal_entry(self):
        """undo() must not append a new journal entry for advance_clock undo."""
        self.h.set("A1", 1)
        self.wb.advance_clock()
        # Journal: [add_sheet, set A1=1, advance_clock]
        before_len = len(self.wb._journal)
        self.wb.undo()
        # After undo: journal has [add_sheet, set A1=1], redo has [advance_clock]
        assert len(self.wb._journal) == before_len - 1
        assert len(self.wb._redo_stack) == 1
        # undo() itself did not append to journal.
        assert self.wb.undo() is True  # undoes set A1=1
        assert len(self.wb._journal) == 1  # only add_sheet remains
        # redo stack has [advance_clock] still.
        assert self.wb.redo() is True  # re-applies set A1=1
        assert self.wb.redo() is True  # re-applies advance_clock
        assert self.wb.clock == 1

    def test_redo_advance_clock_does_not_append_journal_entry(self):
        """redo() must not append a new journal entry for advance_clock redo."""
        self.h.set("A1", 1)
        self.wb.advance_clock()
        self.wb.undo()  # undoes advance_clock, clock=0
        assert self.wb.clock == 0
        before_journal_len = len(self.wb._journal)
        before_redo_len = len(self.wb._redo_stack)
        self.wb.redo()
        # redo() moved entry from redo to journal (no new entry appended).
        assert self.wb.clock == 1
        assert len(self.wb._journal) == before_journal_len + 1
        assert len(self.wb._redo_stack) == before_redo_len - 1

    def test_undo_redo_cycle_preserves_clock(self):
        """Full undo/redo cycle on advance_clock restores clock correctly."""
        self.wb.advance_clock()
        self.wb.advance_clock()
        self.wb.advance_clock()
        assert self.wb.clock == 3
        self.wb.undo()
        assert self.wb.clock == 2
        self.wb.redo()
        assert self.wb.clock == 3
        self.wb.undo()
        assert self.wb.clock == 2
        self.wb.undo()
        assert self.wb.clock == 1
        self.wb.redo()
        assert self.wb.clock == 2
        self.wb.redo()
        assert self.wb.clock == 3

    def test_undo_redo_does_not_change_eval_count(self):
        """undo/redo of advance_clock must not change eval_count."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        self.h.get("B1")
        before = self.h.eval_count
        self.wb.advance_clock()
        self.wb.undo()
        assert self.h.eval_count == before
        self.wb.redo()
        assert self.h.eval_count == before


# ---------------------------------------------------------------------------
# 5. Clock operations in LIFO order with other journaled ops
# ---------------------------------------------------------------------------

class TestClockLIFOWithOtherOps:
    def setup_method(self):
        self.wb = Workbook()

    def test_clock_undo_in_lifo_with_set(self):
        """Clock undo interleaved with set must follow strict LIFO."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        self.wb.advance_clock()
        s1.set("A2", 2)
        self.wb.advance_clock()
        # Journal: [add_sheet S1, set A1=1, advance_clock, set A2=2, advance_clock]
        # Undo order: advance_clock, set A2=2, advance_clock, set A1=1, add_sheet S1
        assert self.wb.clock == 2
        assert self.wb.undo() is True
        assert self.wb.clock == 1
        assert s1.get("A2") == 2
        assert self.wb.undo() is True
        assert self.wb.clock == 1
        assert s1.get("A2") is None
        assert self.wb.undo() is True
        assert self.wb.clock == 0
        assert s1.get("A1") == 1
        assert self.wb.undo() is True
        assert self.wb.clock == 0
        assert s1.get("A1") is None
        assert self.wb.undo() is True
        assert self.wb.sheet_names == []

    def test_clock_redo_in_lifo_with_set(self):
        """Clock redo interleaved with set must follow strict LIFO."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        self.wb.advance_clock()
        s1.set("A2", 2)
        self.wb.advance_clock()
        # Undo all 5 entries.
        self.wb.undo()  # undoes advance_clock (clock=2->1)
        self.wb.undo()  # undoes set A2=2
        self.wb.undo()  # undoes advance_clock (clock=1->0)
        self.wb.undo()  # undoes set A1=1
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []
        assert self.wb.clock == 0
        # Redo in LIFO: add_sheet S1, set A1=1, advance_clock, set A2=2, advance_clock
        assert self.wb.redo() is True
        assert self.wb.sheet_names == ["S1"]
        s1 = self.wb.sheet("S1")
        assert self.wb.redo() is True
        assert s1.get("A1") == 1
        assert self.wb.redo() is True
        assert self.wb.clock == 1
        assert self.wb.redo() is True
        assert s1.get("A2") == 2
        assert self.wb.redo() is True
        assert self.wb.clock == 2

    def test_clock_new_journaled_op_clears_redo_with_other_ops(self):
        """A new journaled op clears the redo stack when clock is in the mix."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 1)
        self.wb.advance_clock()
        s1.set("A2", 2)
        # Undo advance_clock.
        self.wb.undo()  # undoes set A2=2
        self.wb.undo()  # undoes advance_clock
        # Redo stack has 2 entries: [advance_clock, set A2=2] (top is set A2=2)
        assert self.wb.clock == 0
        assert s1.get("A2") is None
        # New journaled op clears redo.
        s1.set("A3", 3)
        assert self.wb.redo() is False
        assert s1.get("A2") is None
        assert s1.get("A3") == 3

    def test_clock_interleaved_with_define_name_and_copy(self):
        """Clock undo/redo interleaved with define_name and copy in LIFO."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 10)
        self.wb.advance_clock()
        s1.define_name("VAL", "A1")
        s1.copy("A1", "B1")
        self.wb.advance_clock()
        # Journal: [add_sheet S1, set A1=10, advance_clock, define_name VAL=A1,
        #           copy A1->B1, advance_clock]
        # Undo all 6 in LIFO.
        assert self.wb.undo() is True  # undoes advance_clock (clock=2->1)
        assert self.wb.clock == 1
        assert self.wb.undo() is True  # undoes copy A1->B1
        assert s1.get("B1") is None
        assert self.wb.undo() is True  # undoes define_name VAL
        assert "VAL" not in s1._names
        assert self.wb.undo() is True  # undoes advance_clock (clock=1->0)
        assert self.wb.clock == 0
        assert self.wb.undo() is True  # undoes set A1=10
        assert s1.get("A1") is None
        assert self.wb.undo() is True  # undoes add_sheet S1
        assert self.wb.sheet_names == []

    def test_clock_redo_interleaved_with_define_name_and_copy(self):
        """Clock redo interleaved with define_name and copy in LIFO."""
        s1 = self.wb.add_sheet("S1")
        s1.set("A1", 10)
        self.wb.advance_clock()
        s1.define_name("VAL", "A1")
        s1.copy("A1", "B1")
        self.wb.advance_clock()
        # Undo all 6.
        self.wb.undo()  # undoes advance_clock
        self.wb.undo()  # undoes copy
        self.wb.undo()  # undoes define_name
        self.wb.undo()  # undoes advance_clock
        self.wb.undo()  # undoes set A1=10
        self.wb.undo()  # undoes add_sheet S1
        assert self.wb.sheet_names == []
        assert self.wb.clock == 0
        # Redo in LIFO: add_sheet S1, set A1=10, advance_clock, define_name VAL=A1,
        #               copy A1->B1, advance_clock
        assert self.wb.redo() is True
        assert self.wb.sheet_names == ["S1"]
        s1 = self.wb.sheet("S1")
        assert self.wb.redo() is True
        assert s1.get("A1") == 10
        assert self.wb.redo() is True
        assert self.wb.clock == 1
        assert self.wb.redo() is True
        assert "VAL" in s1._names
        assert self.wb.redo() is True
        assert s1.get("B1") == 10
        assert self.wb.redo() is True
        assert self.wb.clock == 2


# ---------------------------------------------------------------------------
# 6. Clock undo/redo with eval_count monotonicity (R20)
# ---------------------------------------------------------------------------

class TestClockEvalCountMonotonic:
    def setup_method(self):
        self.wb = Workbook()
        self.h = self.wb.add_sheet("S1")

    def test_clock_undo_redo_eval_count_monotonic(self):
        """eval_count must be monotonic through clock undo/redo cycles."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        self.h.get("B1")  # eval_count = 1
        before = self.h.eval_count
        self.wb.advance_clock()
        self.wb.undo()
        self.wb.redo()
        assert self.h.eval_count >= before

    def test_clock_undo_redo_no_eval_count_decrease(self):
        """undo/redo of advance_clock must never decrease eval_count."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        self.h.get("B1")
        before = self.h.eval_count
        self.wb.advance_clock()
        self.wb.undo()
        assert self.h.eval_count >= before
        self.wb.redo()
        assert self.h.eval_count >= before

    def test_clock_irrelevant_to_formula_closure_no_eval_delta(self):
        """Clock undo/redo touching nothing in get(X)'s closure leaves get(X) at +0."""
        self.h.set("A1", 1)
        self.h.set("B1", "=A1+1")
        self.h.get("B1")  # eval_count = 1
        before = self.h.eval_count
        self.wb.advance_clock()
        self.wb.undo()
        self.wb.redo()
        # Clock operations don't touch A1 or B1, so B1's eval_count delta should be 0.
        assert self.h.eval_count == before
        assert self.h.get("B1") == 2
