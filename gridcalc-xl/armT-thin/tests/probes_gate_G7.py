"""Gate G7 probes — R19 (journal/undo/redo) and R20 (undo/redo vs counters).

Derived from the frozen spec alone, before reading any project test file.
Each test cites the R-id whose text dictates the expectation.
"""

import pytest

from gridcalc import Workbook


# ---------------------------------------------------------------------------
# Scenario 1 — R19: empty journal
# ---------------------------------------------------------------------------

class TestEmptyJournal:
    def test_undo_redo_on_fresh_workbook_return_false(self):
        # R19: "with nothing to undo it returns False and changes nothing";
        # redo "returns False when nothing is undone".
        wb = Workbook()
        assert wb.undo() is False
        assert wb.redo() is False
        # Still usable afterwards.
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        assert s.get("A1") == 1


# ---------------------------------------------------------------------------
# Scenario 2 — R19: strict-LIFO undo/redo chain through set and add_sheet,
# including restore of the never-set state and name-bound handles.
# ---------------------------------------------------------------------------

class TestUndoRedoChain:
    def test_full_chain_set_and_add_sheet(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert s.get("A1") == 2

        # R19: undo reverts the most recent not-yet-undone entry.
        assert wb.undo() is True
        assert s.get("A1") == 1
        # R19: reverting a set restores "the never-set state".
        assert wb.undo() is True
        assert s.get("A1") is None
        # R19: reverting an add_sheet removes that sheet.
        assert wb.undo() is True
        # R19: "any member access through a handle whose sheet does not
        # currently exist — the eval_count property included — raises
        # ValueError".
        with pytest.raises(ValueError):
            s.get("A1")
        with pytest.raises(ValueError):
            s.set("A1", 1)
        with pytest.raises(ValueError):
            s.eval_count
        # Nothing left to undo.
        assert wb.undo() is False

        # R19: redo re-applies each exactly; "the same handle works again
        # once redo ... restores the sheet".
        assert wb.redo() is True
        assert s.get("A1") is None
        assert wb.redo() is True
        assert s.get("A1") == 1
        assert wb.redo() is True
        assert s.get("A1") == 2
        assert wb.redo() is False


# ---------------------------------------------------------------------------
# Scenario 3 — R19: redo stack cleared only by NEW JOURNALED operations;
# failed (ValueError) calls and get never journal. Cross-cuts G1 (R2 bool).
# ---------------------------------------------------------------------------

class TestRedoStackAndNonJournaling:
    def test_failed_set_does_not_journal_or_clear_redo(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert wb.undo() is True
        assert s.get("A1") == 1
        # R2: bool raw raises ValueError; R19: failed calls never journal,
        # and only "any new journaled operation clears the redo stack".
        with pytest.raises(ValueError):
            s.set("A1", True)
        assert s.get("A1") == 1  # state unchanged by the failed call
        assert wb.redo() is True
        assert s.get("A1") == 2

    def test_successful_set_clears_redo(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert wb.undo() is True
        s.set("A1", 3)  # journaled → clears redo stack (R19)
        assert wb.redo() is False
        assert s.get("A1") == 3

    def test_get_never_journals(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("B1", 4)
        assert s.get("B1") == 4  # R19: get never journals
        assert s.get("A1") == 1
        assert wb.undo() is True  # must revert set B1, not anything else
        assert s.get("B1") is None
        assert s.get("A1") == 1


# ---------------------------------------------------------------------------
# Scenario 4 — R19 × R17 (cross-cut G6): undo/redo of copy restores the
# destination cell's previous content, including never-set; redo re-applies
# the rewritten text exactly.
# ---------------------------------------------------------------------------

class TestCopyUndoRedo:
    def test_copy_undo_restores_previous_content(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 10)
        s.set("B1", 3)
        s.copy("A1", "B1")
        assert s.get("B1") == 10
        assert wb.undo() is True  # R19: reverting a copy restores the target
        assert s.get("B1") == 3
        assert wb.redo() is True
        assert s.get("B1") == 10

    def test_copy_undo_restores_never_set(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 10)
        s.copy("A1", "C1")
        assert s.get("C1") == 10
        assert wb.undo() is True
        assert s.get("C1") is None  # R19: "including the never-set state"

    def test_copy_of_formula_undo_redo(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 10)
        s.set("A2", "=A1*2")
        s.copy("A2", "B2")  # R17: rewrites =A1*2 → =B1*2
        assert s.get("B2") == 0  # B1 empty → 0*2
        assert wb.undo() is True
        assert s.get("B2") is None
        assert wb.redo() is True
        assert s.get("B2") == 0

    def test_failed_copy_does_not_journal_or_clear_redo(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert wb.undo() is True
        # R17: copy from an empty (never-set) cell raises ValueError with
        # "no state change and no journal entry".
        with pytest.raises(ValueError):
            s.copy("Z9", "A1")
        assert s.get("A1") == 1
        assert wb.redo() is True
        assert s.get("A1") == 2


# ---------------------------------------------------------------------------
# Scenario 5 — R19 × R18 (cross-cut G6): undo/redo of define_name restores
# the previous binding, including the undefined state.
# ---------------------------------------------------------------------------

class TestDefineNameUndoRedo:
    def test_binding_history_walks_back_to_undefined(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("B1", 5)
        s.set("C1", 7)
        s.set("A1", "=NM")
        assert s.get("A1") == "#NAME!"  # R18: undefined NAME
        s.define_name("NM", "B1")
        assert s.get("A1") == 5
        s.define_name("NM", "C1")
        assert s.get("A1") == 7

        # R19: reverting a define_name restores the previous binding.
        assert wb.undo() is True
        assert s.get("A1") == 5
        # R19: "including undefined".
        assert wb.undo() is True
        assert s.get("A1") == "#NAME!"
        assert wb.redo() is True
        assert s.get("A1") == 5
        assert wb.redo() is True
        assert s.get("A1") == 7

    def test_failed_define_name_does_not_journal_or_clear_redo(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("B1", 5)
        s.set("C1", 7)
        s.set("A1", "=NM")
        s.define_name("NM", "B1")
        s.define_name("NM", "C1")
        assert wb.undo() is True
        assert s.get("A1") == 5
        # R18: target "A0" fails R1 → ValueError, no journal entry.
        with pytest.raises(ValueError):
            s.define_name("NM", "A0")
        assert s.get("A1") == 5
        assert wb.redo() is True  # redo stack survived the failed call
        assert s.get("A1") == 7


# ---------------------------------------------------------------------------
# Scenario 6 — R19 vs the advance_clock stub. The clock op itself is R26
# (gate G10); at the G7 checkpoint it may be a stub, but R19 requires that
# a call that does not SUCCEED never journals and never clears the redo
# stack. R19's advance_clock undo/redo semantics MUST be re-probed at G10.
# ---------------------------------------------------------------------------

class TestAdvanceClockStubAtomicity:
    def test_raising_advance_clock_does_not_journal_or_clear_redo(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", 1)
        s.set("A1", 2)
        assert wb.undo() is True
        assert s.get("A1") == 1
        assert wb.clock == 0  # R26: clock starts at 0
        # Stub raises — R19: only SUCCESSFUL operations journal; a raising
        # call must leave the journal and redo stack untouched.
        with pytest.raises(Exception):
            wb.advance_clock()
        assert wb.clock == 0
        assert s.get("A1") == 1
        assert wb.redo() is True
        assert s.get("A1") == 2


# ---------------------------------------------------------------------------
# Scenario 7 — R20 × R10 (cross-cut G4): counters. undo/redo never evaluate
# and never decrease counters; an undo/redo IS the edit it performs, with no
# content-comparison short-circuit; irrelevant undo → +0.
# ---------------------------------------------------------------------------

class TestUndoRedoCounters:
    def test_undo_redo_never_evaluate_and_relevant_undo_counts(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=B1+1")
        s.set("B1", 2)
        assert s.eval_count == 0  # R10: mutating ops never evaluate
        assert s.get("A1") == 3
        assert s.eval_count == 1

        # R10/R20: undo itself never evaluates or changes any counter.
        assert wb.undo() is True  # reverts set B1 → never-set
        assert s.eval_count == 1
        # R20: this undo is an edit at B1, inside A1's closure → relevant
        # edit: ≥1; R10 no-full-recompute: ≤ formula cells in closure (=1).
        assert s.get("A1") == 1  # empty B1 contributes 0 (R6)
        assert s.eval_count == 2

        assert wb.redo() is True  # re-applies set B1 = 2
        assert s.eval_count == 2  # redo never evaluates
        assert s.get("A1") == 3
        assert s.eval_count == 3  # relevant edit again, exactly +1

    def test_undo_restoring_identical_content_still_counts(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A9", "=B9")
        s.set("B9", 2)
        s.set("B9", 2)  # same content, journaled again (R10: no comparison)
        assert s.get("A9") == 2
        assert s.eval_count == 1
        # R20: undo restores B9 to 2 — "even when the restored content
        # equals what a still-earlier state held" it is an edit at B9.
        assert wb.undo() is True
        assert s.get("A9") == 2
        assert s.eval_count == 2  # ≥1 relevant, ≤1 closure formula cells

    def test_irrelevant_undo_adds_zero(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A9", "=B9")
        s.set("B9", 2)
        assert s.get("A9") == 2
        assert s.eval_count == 1
        s.set("D5", 99)  # outside A9's closure {A9, B9}
        assert s.get("A9") == 2
        assert s.eval_count == 1  # R10 irrelevant edit
        # R20: an undo whose operation touches nothing in the closure
        # leaves get(X) at +0.
        assert wb.undo() is True  # reverts set D5
        assert s.get("A9") == 2
        assert s.eval_count == 1

    def test_counter_monotonic_across_sheet_removal_and_restore(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=1+1")
        assert s.get("A1") == 2
        ec_before = s.eval_count
        assert ec_before == 1
        assert wb.undo() is True  # revert set A1
        assert wb.undo() is True  # revert add_sheet — S1 gone
        with pytest.raises(ValueError):
            s.eval_count
        assert wb.redo() is True  # S1 back (empty)
        # R20: undo/redo never decrease any counter (monotonic per name).
        assert s.eval_count >= ec_before


# ---------------------------------------------------------------------------
# Scenario 8 — R20 × R9 (cross-cut G3): after undo/redo, values obey R11
# against the RESTORED contents — undo removing one leg of a cycle clears
# the #CYCLE!, redo brings it back.
# ---------------------------------------------------------------------------

class TestUndoRedoVersusCycles:
    def test_undo_clears_cycle_redo_restores_it(self):
        wb = Workbook()
        s = wb.add_sheet("S1")
        s.set("A1", "=B1")
        s.set("B1", "=A1")
        assert s.get("A1") == "#CYCLE!"  # R9
        assert s.get("B1") == "#CYCLE!"
        assert wb.undo() is True  # reverts set B1 → never-set
        # R20/R11: values match naive recomputation of the restored state.
        assert s.get("A1") == 0  # =B1 with B1 empty → 0 (R6)
        assert s.get("B1") is None
        assert wb.redo() is True
        assert s.get("A1") == "#CYCLE!"
        assert s.get("B1") == "#CYCLE!"
