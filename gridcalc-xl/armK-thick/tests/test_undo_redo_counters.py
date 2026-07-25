import pytest

from gridcalc import Workbook
from tests.reference_model import NaiveSheet


CHECK_ADDRS = ("A1", "B1", "C1", "D1")


class UndoRedoReference:
    def __init__(self):
        self.sheets = {}
        self.order = []
        self.clock = 0
        self.journal = []
        self.redo_stack = []

    def add_sheet(self, name):
        self.sheets[name] = NaiveSheet()
        self.order.append(name)
        self.journal.append(("add_sheet", name))
        self.redo_stack.clear()

    @property
    def sheet_names(self):
        return list(self.order)

    def advance_clock(self):
        old = self.clock
        self.clock += 1
        self.journal.append(("advance_clock", old, self.clock))
        self.redo_stack.clear()
        return self.clock

    def set(self, sheet, addr, raw):
        model = self.sheets[sheet]
        old = model._cells.get(addr)
        model.set(addr, raw)
        self.journal.append(("set", sheet, addr, old, raw))
        self.redo_stack.clear()

    def define_name(self, sheet, name, target):
        model = self.sheets[sheet]
        old = model._names.get(name)
        model.define_name(name, target)
        self.journal.append(("define_name", sheet, name, old, target))
        self.redo_stack.clear()

    def copy(self, sheet, src, dst):
        model = self.sheets[sheet]
        old = model._cells.get(dst)
        model.copy(src, dst)
        self.journal.append(("copy", sheet, dst, old, model._cells.get(dst)))
        self.redo_stack.clear()

    def undo(self):
        if not self.journal:
            return False
        entry = self.journal.pop()
        self.redo_stack.append(entry)
        self._restore(entry, redo=False)
        return True

    def redo(self):
        if not self.redo_stack:
            return False
        entry = self.redo_stack.pop()
        self.journal.append(entry)
        self._restore(entry, redo=True)
        return True

    def _restore(self, entry, redo):
        op = entry[0]
        if op == "add_sheet":
            name = entry[1]
            if redo:
                self.sheets[name] = NaiveSheet()
                self.order.append(name)
            else:
                del self.sheets[name]
                self.order.remove(name)
        elif op in ("set", "copy"):
            _, sheet, addr, old, new = entry
            cells = self.sheets[sheet]._cells
            value = new if redo else old
            if value is None:
                cells.pop(addr, None)
            else:
                cells[addr] = value
        elif op == "define_name":
            _, sheet, name, old, new = entry
            names = self.sheets[sheet]._names
            value = new if redo else old
            if value is None:
                names.pop(name, None)
            else:
                names[name] = value
        elif op == "advance_clock":
            _, old, new = entry
            self.clock = new if redo else old

    def get(self, sheet, addr):
        return self.sheets[sheet].get(addr)


def _values(sheet):
    return tuple((addr, sheet.get(addr)) for addr in CHECK_ADDRS)


def test_eval_count_monotonic_and_values_match_naive_after_undo_redo_sequence():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    ref = UndoRedoReference()
    ref.add_sheet("S")

    for addr, raw in (("A1", 1), ("B1", "=A1+1"), ("C1", "=B1+1")):
        sheet.set(addr, raw)
        ref.set("S", addr, raw)

    assert sheet.get("C1") == ref.get("S", "C1") == 3
    counts = [sheet.eval_count]

    sheet.set("A1", 10)
    ref.set("S", "A1", 10)
    assert sheet.get("C1") == ref.get("S", "C1") == 12
    counts.append(sheet.eval_count)

    assert wb.undo() is ref.undo() is True
    assert sheet.get("C1") == ref.get("S", "C1") == 3
    counts.append(sheet.eval_count)

    assert wb.redo() is ref.redo() is True
    assert sheet.get("C1") == ref.get("S", "C1") == 12
    counts.append(sheet.eval_count)

    assert counts == sorted(counts)


def test_undo_redo_set_invalidation_respects_relevant_and_irrelevant_bounds():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", 1)
    sheet.set("B1", "=A1+1")
    assert sheet.get("B1") == 2
    before = sheet.eval_count

    sheet.set("C1", 9)
    assert wb.undo() is True
    assert wb.redo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count == before

    sheet.set("A1", 5)
    assert sheet.get("B1") == 6
    after_edit = sheet.eval_count
    assert wb.undo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count == after_edit + 1
    assert wb.redo() is True
    assert sheet.get("B1") == 6
    assert sheet.eval_count == after_edit + 2


def test_undo_redo_copy_invalidation_respects_relevant_and_irrelevant_bounds():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", 1)
    sheet.set("B1", "=A1+1")
    sheet.set("C1", 8)
    assert sheet.get("B1") == 2
    before = sheet.eval_count

    sheet.copy("C1", "D1")
    assert wb.undo() is True
    assert wb.redo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count == before

    sheet.copy("C1", "A1")
    assert sheet.get("B1") == 9
    after_copy = sheet.eval_count
    assert wb.undo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count == after_copy + 1
    assert wb.redo() is True
    assert sheet.get("B1") == 9
    assert sheet.eval_count == after_copy + 2


def test_undo_redo_define_name_invalidation_respects_relevant_and_irrelevant_bounds():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    sheet.set("A1", 1)
    sheet.set("C1", 10)
    sheet.define_name("VALUE", "A1")
    sheet.set("B1", "=VALUE+1")
    assert sheet.get("B1") == 2
    before = sheet.eval_count

    sheet.define_name("OTHER", "C1")
    assert wb.undo() is True
    assert wb.redo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count == before

    sheet.define_name("VALUE", "C1")
    assert sheet.get("B1") == 11
    after_define = sheet.eval_count
    assert wb.undo() is True
    assert sheet.get("B1") == 2
    assert sheet.eval_count == after_define + 1
    assert wb.redo() is True
    assert sheet.get("B1") == 11
    assert sheet.eval_count == after_define + 2


def test_removed_sheet_handle_raises_for_all_members_and_rebinds_to_fresh_add():
    wb = Workbook()
    old = wb.add_sheet("S")
    old.set("A1", 1)
    wb.undo()
    wb.undo()

    for access in (
        lambda: old.eval_count,
        lambda: old.get("A1"),
        lambda: old.set("A1", 2),
        lambda: old.copy("A1", "B1"),
        lambda: old.define_name("VALUE", "A1"),
    ):
        with pytest.raises(ValueError):
            access()

    fresh = wb.add_sheet("S")
    fresh.set("A1", 99)
    assert old.get("A1") == 99
    old.set("B1", "=A1+1")
    assert fresh.get("B1") == 100
    assert old.eval_count == fresh.eval_count


def test_removed_sheet_handle_works_again_after_redo_restores_name():
    wb = Workbook()
    old = wb.add_sheet("S")
    assert wb.undo() is True
    with pytest.raises(ValueError):
        old.eval_count
    assert wb.redo() is True
    old.set("A1", 7)
    assert old.get("A1") == 7


def test_naive_undo_redo_journal_restoration_and_redo_clearing():
    wb = Workbook()
    sheet = wb.add_sheet("S")
    ref = UndoRedoReference()
    ref.add_sheet("S")

    for addr, raw in (("A1", 2), ("B1", "=A1+3")):
        sheet.set(addr, raw)
        ref.set("S", addr, raw)
    sheet.define_name("VALUE", "B1")
    ref.define_name("S", "VALUE", "B1")
    sheet.set("C1", "=VALUE+1")
    ref.set("S", "C1", "=VALUE+1")
    sheet.copy("C1", "D1")
    ref.copy("S", "C1", "D1")
    assert _values(sheet) == tuple((addr, ref.get("S", addr)) for addr in CHECK_ADDRS)

    for _ in range(4):
        assert wb.undo() is ref.undo() is True
        assert _values(sheet) == tuple((addr, ref.get("S", addr)) for addr in CHECK_ADDRS)

    for _ in range(3):
        assert wb.redo() is ref.redo() is True
        assert _values(sheet) == tuple((addr, ref.get("S", addr)) for addr in CHECK_ADDRS)

    sheet.set("D1", 4)
    ref.set("S", "D1", 4)
    assert wb.redo() is ref.redo() is False
    assert _values(sheet) == tuple((addr, ref.get("S", addr)) for addr in CHECK_ADDRS)


def test_naive_undo_redo_restores_sheet_set_and_missing_sheet_get_behavior():
    wb = Workbook()
    ref = UndoRedoReference()
    s = wb.add_sheet("S")
    ref.add_sheet("S")
    s.set("A1", 5)
    ref.set("S", "A1", 5)
    t = wb.add_sheet("T")
    ref.add_sheet("T")
    t.set("A1", "=A1+1")
    ref.set("T", "A1", "=A1+1")

    assert wb.sheet_names == ref.sheet_names == ["S", "T"]
    assert t.get("A1") == ref.get("T", "A1")
    assert wb.undo() is ref.undo() is True
    assert wb.undo() is ref.undo() is True
    assert wb.sheet_names == ref.sheet_names == ["S"]
    with pytest.raises(ValueError):
        wb.sheet("T").get("A1")
    with pytest.raises(KeyError):
        ref.get("T", "A1")

    assert wb.redo() is ref.redo() is True
    assert wb.redo() is ref.redo() is True
    assert wb.sheet_names == ref.sheet_names == ["S", "T"]
    assert wb.sheet("T").get("A1") == ref.get("T", "A1")


def test_naive_undo_redo_restores_current_clock_and_clears_redo():
    wb = Workbook()
    ref = UndoRedoReference()
    assert wb.clock == ref.clock == 0

    assert wb.advance_clock() == ref.advance_clock() == 1
    assert wb.advance_clock() == ref.advance_clock() == 2
    assert wb.undo() is ref.undo() is True
    assert wb.clock == ref.clock == 1
    assert wb.redo() is ref.redo() is True
    assert wb.clock == ref.clock == 2
    assert wb.undo() is ref.undo() is True
    assert wb.advance_clock() == ref.advance_clock() == 2
    assert wb.redo() is ref.redo() is False
    assert wb.clock == ref.clock == 2
