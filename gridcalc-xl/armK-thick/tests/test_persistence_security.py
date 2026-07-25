import inspect
import json

import pytest

import gridcalc.workbook as workbook_module
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


ADVERSARIAL_FROM_JSON_CASES = [
    123,
    1.5,
    None,
    True,
    [],
    {},
    b'{"version":1,"clock":0,"sheets":[]}',
    "",
    "not json",
    "{",
    "[1,",
    "null",
    "[]",
    "1",
    '"text"',
    "1.0",
    "NaN",
    "Infinity",
    _payload(version=1.0),
    _payload(version=2),
    _payload(clock=1.0),
    _payload(clock=float("nan")),
    _payload(clock=float("inf")),
    _payload(clock=-1),
    _payload(clock=True),
    _payload(sheets={}),
    _payload(sheets=[None]),
    _payload(sheets=[[{"name": "S1", "cells": {}, "names": {}}]]),
    '{"version":1,"clock":0,"sheets":[[[{"name":"S1","cells":{},"names":{}}]]]}',
    _payload(sheets=[{"name": "", "cells": {}, "names": {}}]),
    _payload(sheets=[{"name": "1Bad", "cells": {}, "names": {}}]),
    _payload(sheets=[{"name": "Bad-Name", "cells": {}, "names": {}}]),
    _payload(sheets=[{"name": "S" * 33, "cells": {}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {}}, {"name": "S1", "cells": {}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": [], "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A0": 1}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"AA1": 1}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A100": 1}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"a1": 1}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A1": True}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A1": None}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A1": []}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A1": 1.0}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": []}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {"A1": "A1"}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {"SUM": "A1"}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": "A0"}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": "B1:A1"}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": "Missing!A1"}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": ["A1"]}}]),
    _payload(sheets=[{"name": "S1", "cells": {}, "names": {}, "unknown": 1}]),
    '{"version":1,"clock":0,"sheets":[],"clock":0}',
    '{"version":1,"clock":0,"sheets":[{"name":"S1","cells":{"A1":1},"cells":{},"names":{}}]}',
    _payload(sheets=[{"name": "S1", "cells": {"A1": 1}, "names": {}}]),
    _payload(sheets=[{"name": "S1", "cells": {"A1": "=A1+1"}, "names": {}}]),
]


def _assert_public_invariants(wb):
    assert isinstance(wb, Workbook)
    assert isinstance(wb.clock, int)
    assert wb.clock >= 0
    names = wb.sheet_names
    assert isinstance(names, list)
    assert len(names) == len(set(names))
    for name in names:
        assert type(name) is str
        sheet = wb.sheet(name)
        sheet.get("A1")
        sheet.get("Z99")
        assert isinstance(sheet.eval_count, int)


@pytest.mark.parametrize("raw", ADVERSARIAL_FROM_JSON_CASES)
def test_adversarial_from_json_cases_raise_value_error_or_valid_workbook(raw):
    other = Workbook()
    sheet = other.add_sheet("Safe")
    sheet.set("A1", 41)
    sheet.set("B1", "=A1+1")
    assert sheet.get("B1") == 42
    before_names = other.sheet_names
    before_clock = other.clock
    before_eval_count = sheet.eval_count

    try:
        loaded = Workbook.from_json(raw)
    except ValueError:
        pass
    else:
        _assert_public_invariants(loaded)

    assert other.sheet_names == before_names
    assert other.clock == before_clock
    assert sheet.get("A1") == 41
    assert sheet.get("B1") == 42
    assert sheet.eval_count == before_eval_count


@pytest.mark.parametrize(
    "raw",
    [
        "1.0",
        "NaN",
        "Infinity",
        _payload(version=1.0),
        _payload(clock=1.0),
        _payload(clock=float("nan")),
        _payload(clock=float("inf")),
        _payload(sheets=[{"name": "S1", "cells": {"A1": 1.0}, "names": {}}]),
        _payload(sheets=[{"name": "S1", "cells": {}, "names": {"NM": 1.0}}]),
    ],
)
def test_from_json_rejects_json_floats_in_every_schema_position(raw):
    with pytest.raises(ValueError):
        Workbook.from_json(raw)


def test_from_json_does_not_call_str_subclass_str_method():
    class HostileStr(str):
        def __str__(self):
            raise AssertionError("from_json executed input-controlled __str__")

    wb = Workbook.from_json(HostileStr('{"version":1,"clock":0,"sheets":[]}'))

    _assert_public_invariants(wb)


def test_workbook_runtime_source_contains_no_dynamic_execution_or_import_hooks():
    source = inspect.getsource(workbook_module)
    banned_fragments = ["eval(", "exec(", "compile(", "__import__", "importlib", "pickle"]

    for fragment in banned_fragments:
        assert fragment not in source
