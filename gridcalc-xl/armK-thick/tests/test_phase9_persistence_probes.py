import json

import pytest

from gridcalc import Workbook


def test_phase9_probe_to_json_is_observation_and_load_resets_runtime_state():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 41)
    s2.set("A1", 1)
    s1.set("B1", "=S2!A1 + A1")

    assert s1.get("B1") == 42
    before_counts = (s1.eval_count, s2.eval_count)
    before_clock = wb.clock

    payload = wb.to_json()
    assert isinstance(payload, str)
    assert isinstance(json.loads(payload), object)
    assert (s1.eval_count, s2.eval_count) == before_counts
    assert wb.clock == before_clock

    assert wb.undo() is True
    assert s1.get("B1") is None
    assert wb.redo() is True
    assert s1.get("B1") == 42

    loaded = Workbook.from_json(payload)
    loaded_s1 = loaded.sheet("S1")
    loaded_s2 = loaded.sheet("S2")

    assert loaded.sheet_names == ["S1", "S2"]
    assert loaded.clock == before_clock
    assert loaded.undo() is False
    assert loaded_s1.eval_count == 0
    assert loaded_s2.eval_count == 0
    assert loaded_s1.get("B1") == 42
    assert loaded_s1.eval_count == 1


def test_phase9_probe_invalid_from_json_inputs_do_not_corrupt_other_workbooks():
    survivor = Workbook()
    sh = survivor.add_sheet("Live")
    sh.set("A1", 7)
    sh.set("B1", "=A1+1")
    assert sh.get("B1") == 8
    count_before = sh.eval_count

    invalid_inputs = [
        5,
        None,
        "not json",
        "null",
        "[]",
        "1.0",
        "NaN",
        '{"sheets": [{"name": "Bad-Name", "cells": {}, "names": {}}], "clock": 0}',
        '{"sheets": [{"name": "S", "cells": {"A0": 1}, "names": {}}], "clock": 0}',
    ]

    for payload in invalid_inputs:
        with pytest.raises(ValueError):
            Workbook.from_json(payload)
        assert survivor.sheet_names == ["Live"]
        assert survivor.clock == 0
        assert sh.get("A1") == 7
        assert sh.get("B1") == 8

    assert sh.eval_count == count_before


def test_phase9_probe_roundtrip_preserves_copy_rewrite_name_and_qualifier_semantics():
    def build_workbook():
        wb = Workbook()
        main = wb.add_sheet("Main")
        aux = wb.add_sheet("Aux")
        main.set("A1", 10)
        main.set("A2", 20)
        aux.set("A1", 100)
        aux.set("A2", 200)
        main.define_name("PAIR", "A1:A2")
        aux.define_name("PAIR", "A1:A2")
        main.set("C3", "=SUM(PAIR)+SUM(Aux!A1:A2)+$A1+A$2")
        return wb

    original = build_workbook()
    loaded = Workbook.from_json(original.to_json())

    original.sheet("Main").copy("C3", "D4")
    loaded.sheet("Main").copy("C3", "D4")

    assert loaded.sheet_names == original.sheet_names
    assert loaded.sheet("Main").get("C3") == original.sheet("Main").get("C3") == 360
    assert loaded.sheet("Main").get("D4") == original.sheet("Main").get("D4") == 50

    original.advance_clock()
    loaded.advance_clock()
    assert Workbook.from_json(loaded.to_json()).sheet("Main").get("D4") == original.sheet("Main").get("D4")
