import json

import pytest

from gridcalc import Workbook


def _payload(**overrides):
    data = {
        "version": 1,
        "clock": 0,
        "sheets": [
            {"name": "S1", "cells": {}, "names": {}},
        ],
    }
    data.update(overrides)
    return json.dumps(data)


def test_to_json_is_pure_json_observation():
    wb = Workbook()
    sheet = wb.add_sheet("S1")
    sheet.set("A1", 3)
    sheet.set("B1", "=A1+1")
    before_eval = sheet.eval_count
    before_clock = wb.clock

    text = wb.to_json()

    assert isinstance(text, str)
    assert json.loads(text)["sheets"][0]["cells"] == {"A1": 3, "B1": "=A1+1"}
    assert sheet.eval_count == before_eval
    assert wb.clock == before_clock
    assert wb.undo() is True
    assert sheet.get("B1") is None


def test_round_trip_restores_content_names_order_and_clock_but_resets_runtime_state():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 7)
    s1.set("B1", "literal")
    s1.set("C1", "=$A$1 + S2!A1")
    s1.set("D1", "=#REF! + 1")
    s2.set("A1", 5)
    s2.set("B1", "=S1!A1 + 1")
    s1.define_name("TOTAL", "S2!A1")
    s1.define_name("BLOCK", "S2!A1:B1")
    s2.define_name("LOCAL", "A1")
    wb.advance_clock()
    wb.advance_clock()

    assert s1.get("C1") == 12
    assert s2.get("B1") == 8
    assert s1.eval_count == 1
    assert s2.eval_count == 1

    loaded = Workbook.from_json(wb.to_json())
    loaded_s1 = loaded.sheet("S1")
    loaded_s2 = loaded.sheet("S2")

    assert loaded.sheet_names == ["S1", "S2"]
    assert loaded.clock == 2
    assert loaded_s1._cells == {
        "A1": 7,
        "B1": "literal",
        "C1": "=$A$1 + S2!A1",
        "D1": "=#REF! + 1",
    }
    assert loaded_s2._cells == {"A1": 5, "B1": "=S1!A1 + 1"}
    assert loaded_s1._names == {"TOTAL": "S2!A1", "BLOCK": "S2!A1:B1"}
    assert loaded_s2._names == {"LOCAL": "A1"}
    assert loaded.undo() is False
    assert loaded.redo() is False
    assert loaded_s1.eval_count == 0
    assert loaded_s2.eval_count == 0
    assert loaded_s1._cache == {}
    assert loaded_s2._cache == {}

    assert loaded_s1.get("C1") == 12
    assert loaded_s1.eval_count == 1


def test_from_json_invalid_inputs_do_not_corrupt_unrelated_workbook_or_global_state():
    other = Workbook()
    sheet = other.add_sheet("Safe")
    sheet.set("A1", "=1+1")
    assert sheet.get("A1") == 2
    before_clock = other.clock
    before_eval = sheet.eval_count
    before_names = other.sheet_names

    invalid_inputs = [
        123,
        "not json",
        _payload(clock=-1),
        _payload(sheets=[{"name": "Bad", "cells": {"A0": 1}, "names": {}}]),
        _payload(sheets=[{"name": "Bad", "cells": {}, "names": {"NM": "Missing!A1"}}]),
        '{"version":1,"clock":0,"sheets":[],"clock":0}',
        _payload(extra={"nested": float("nan")}),
    ]

    for raw in invalid_inputs:
        with pytest.raises(ValueError):
            Workbook.from_json(raw)

    assert other.sheet_names == before_names
    assert other.clock == before_clock
    assert sheet.eval_count == before_eval
    assert sheet.get("A1") == 2


@pytest.mark.parametrize(
    "raw",
    [
        "null",
        "[]",
        "1",
        '"text"',
        _payload(version=2),
        _payload(clock=True),
        _payload(clock=1.0),
        _payload(clock=float("nan")),
        _payload(clock=float("inf")),
        _payload(sheets={}),
        _payload(sheets=[{"name": "1Bad", "cells": {}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": {}}, {"name": "S1", "cells": {}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": [], "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {"A1": []}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {"A1": 1.0}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {"A1": True}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {"AA1": 1}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": []}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": {"A1": "A1"}}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": "A0"}}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": ["A1"]}}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": {}, "unknown": 1}]),
        _payload(unknown={"deep": {"float": 1.0}}),
    ],
)
def test_from_json_rejects_invalid_schema_and_float_corpus(raw):
    with pytest.raises(ValueError):
        Workbook.from_json(raw)


def test_from_json_accepts_valid_cross_sheet_name_binding():
    loaded = Workbook.from_json(
        _payload(
            sheets=[
                {"name": "S1", "cells": {}, "names": {"REMOTE": "S2!A1"}},
                {"name": "S2", "cells": {"A1": 9}, "names": {}},
            ]
        )
    )

    assert loaded.sheet("S1")._names == {"REMOTE": "S2!A1"}
    assert loaded.sheet("S1").eval_count == 0
