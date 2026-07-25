import pytest

from gridcalc import Workbook


def test_probe_name_redefinition_undo_redo_invalidates_cached_formula():
    # R18 lines 491-519: names are per-sheet, redefinitions journal, and touch mentioning formulas.
    # R19 lines 527-535: undo/redo restore prior name bindings including undefined.
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("B1", 2)
    sh.set("C1", 5)
    sh.set("A1", "=BOX+1")

    assert sh.get("A1") == "#NAME!"

    sh.define_name("BOX", "B1")
    assert sh.get("A1") == 3

    sh.define_name("BOX", "C1")
    assert sh.get("A1") == 6

    assert wb.undo() is True
    assert sh.get("A1") == 3

    assert wb.undo() is True
    assert sh.get("A1") == "#NAME!"

    assert wb.redo() is True
    assert sh.get("A1") == 3

    assert wb.redo() is True
    assert sh.get("A1") == 6


def test_probe_copy_rewrite_ref_token_and_undo_redo_never_set_state():
    # R16 lines 449-455: dollar-marked components evaluate normally and only affect copy.
    # R17 lines 456-490: copy rewrites unmarked refs, converts shifted out-of-grid refs to #REF!, journals.
    # R19 lines 532-533: undoing copy restores previous target content, including never-set state.
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", 10)
    sh.set("Z99", "=A1+$A$1+SUM(Y99:Z99)")
    sh.set("Y98", 1)

    sh.copy("Z99", "Z98")

    assert sh.get("Z98") == "#REF!"
    assert wb.undo() is True
    assert sh.get("Z98") is None
    assert wb.redo() is True
    assert sh.get("Z98") == "#REF!"


def test_probe_add_sheet_undo_redo_handle_lifecycle_and_redo_clearing():
    # R19 lines 530-542: new journaled operations clear redo; add_sheet undo removes sheet;
    # stale handles raise ValueError on every member access and revive when the sheet name exists again.
    wb = Workbook()
    sh = wb.add_sheet("S")
    sh.set("A1", 7)
    assert sh.get("A1") == 7

    assert wb.undo() is True
    assert sh.get("A1") is None
    assert wb.undo() is True

    with pytest.raises(ValueError):
        sh.get("A1")
    with pytest.raises(ValueError):
        sh.set("A1", 1)
    with pytest.raises(ValueError):
        sh.copy("A1", "A2")
    with pytest.raises(ValueError):
        sh.define_name("BOX", "A1")
    with pytest.raises(ValueError):
        _ = sh.eval_count

    revived = wb.add_sheet("S")
    assert wb.redo() is False
    assert sh.get("A1") is None
    assert revived.get("A1") is None
