import json
import random

import pytest

from gridcalc import Workbook


def build_workbook():
    wb = Workbook()
    s1 = wb.add_sheet("S1")
    s2 = wb.add_sheet("S2")
    s1.set("A1", 3)
    s1.set("A2", "hello")
    s2.set("A1", 4)
    s1.define_name("REMOTE", "S2!A1")
    s1.set("B1", '=CONCAT(A2, "-", REMOTE)')
    s1.set("B2", "=SUM(S2!A1:A1)")
    return wb


def test_round_trip_preserves_values_and_resets_counters_and_journal():
    wb = build_workbook()
    s1 = wb.sheet("S1")
    assert s1.get("B1") == "hello-4"
    assert s1.eval_count > 0

    loaded = Workbook.from_json(wb.to_json())
    loaded_s1 = loaded.sheet("S1")
    assert loaded.sheet_names == ["S1", "S2"]
    assert loaded_s1.eval_count == 0
    assert loaded_s1.get("B1") == "hello-4"
    assert loaded_s1.get("B2") == 4
    assert loaded.undo() is False


def test_to_json_is_pure_observation_and_copy_after_round_trip_rewrites_same_text():
    wb = build_workbook()
    s1 = wb.sheet("S1")
    before = s1.eval_count
    payload = wb.to_json()
    assert s1.eval_count == before

    loaded = Workbook.from_json(payload)
    loaded.sheet("S1").copy("B1", "C2")
    wb.sheet("S1").copy("B1", "C2")
    assert loaded.sheet("S1").get("C2") == wb.sheet("S1").get("C2")


def test_from_json_rejects_invalid_inputs_and_wrong_shapes():
    valid = json.loads(build_workbook().to_json())
    bad_cases = [
        None,
        1,
        True,
        b"{}",
        [],
        "not json",
        "null",
        "[]",
        "1",
        '"bare"',
        "NaN",
        "Infinity",
        json.dumps({"version": 1, "clock": 0, "sheets": [], "extra": 1}),
        json.dumps({"version": 1, "clock": 0.0, "sheets": []}),
        json.dumps({"version": 1, "clock": True, "sheets": []}),
        json.dumps({"version": 1.0, "clock": 0, "sheets": []}),
        json.dumps({"version": True, "clock": 0, "sheets": []}),
        json.dumps({"version": 2, "clock": 0, "sheets": []}),
        json.dumps({"version": 1, "clock": 0, "sheets": {}}),
    ]
    duplicate = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {}, "names": {}}, {"name": "S", "cells": {}, "names": {}}]}
    bad_addr = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {"A0": {"type": "int", "value": 1}}, "names": {}}]}
    bad_float = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {"A1": {"type": "int", "value": 1.0}}, "names": {}}]}
    bad_name_target = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {}, "names": {"AA": ["addr", "Ghost", "A1"]}}]}
    bad_sheet_name = {"version": 1, "clock": 0, "sheets": [{"name": "1bad", "cells": {}, "names": {}}]}
    bad_cell_shape = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {"A1": {"type": "int"}}, "names": {}}]}
    bad_cell_bool = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {"A1": {"type": "int", "value": True}}, "names": {}}]}
    bad_cell_type = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {"A1": {"type": "float", "value": 1}}, "names": {}}]}
    bad_name_key = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {}, "names": {"A1": ["addr", "S", "A1"]}}]}
    bad_range_order = {"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {}, "names": {"AA": ["range", "S", "B2", "A1"]}}]}
    deep = "[" * 40 + "]" * 40
    bad_cases.extend(
        json.dumps(case)
        for case in [
            duplicate,
            bad_addr,
            bad_float,
            bad_name_target,
            bad_sheet_name,
            bad_cell_shape,
            bad_cell_bool,
            bad_cell_type,
            bad_name_key,
            bad_range_order,
        ]
    )
    bad_cases.extend([deep, json.dumps({"version": 1, "clock": 0, "sheets": [{"name": "S", "cells": {"AA1": {"type": "int", "value": 1}}, "names": {}}]})])

    for bad in bad_cases:
        with pytest.raises(ValueError):
            Workbook.from_json(bad)

    assert Workbook.from_json(json.dumps(valid)).sheet_names == ["S1", "S2"]


def test_seeded_round_trip_differential_floor_1000_sequences():
    sheets = ["S1", "S2", "S3"]
    addrs = ["A1", "A2", "B1", "B2"]
    formulas = ["=C1+1", "=C1+D1", "=SUM(C1:D2)", '=CONCAT("x", C1)', "=IF(C1, D1, D2)", "=NOW()+C1"]

    class Naive:
        def __init__(self):
            self.sheets = {name: {} for name in sheets}
            self.names = {name: {} for name in sheets}
            self.undo_stack = []
            self.redo_stack = []
            self.clock = 0

        def clone(self):
            other = Naive()
            other.sheets = {k: dict(v) for k, v in self.sheets.items()}
            other.names = {k: dict(v) for k, v in self.names.items()}
            other.undo_stack = list(self.undo_stack)
            other.redo_stack = list(self.redo_stack)
            other.clock = self.clock
            return other

        def set(self, sheet, addr, raw):
            old = self.sheets[sheet].get(addr, None)
            had = addr in self.sheets[sheet]
            self.sheets[sheet][addr] = raw
            self.undo_stack.append(("cell", sheet, addr, had, old, True, raw))
            self.redo_stack.clear()

        def copy(self, sheet, src, dst):
            if src not in self.sheets[sheet]:
                raise ValueError
            self.set(sheet, dst, self.sheets[sheet][src])

        def define_name(self, sheet, name, target):
            old = self.names[sheet].get(name)
            had = name in self.names[sheet]
            self.names[sheet][name] = target
            self.undo_stack.append(("name", sheet, name, had, old, True, target))
            self.redo_stack.clear()

        def undo(self):
            if not self.undo_stack:
                return False
            entry = self.undo_stack.pop()
            self._apply(entry, undo=True)
            self.redo_stack.append(entry)
            return True

        def redo(self):
            if not self.redo_stack:
                return False
            entry = self.redo_stack.pop()
            self._apply(entry, undo=False)
            self.undo_stack.append(entry)
            return True

        def advance_clock(self):
            old = self.clock
            self.clock += 1
            self.undo_stack.append(("clock", None, None, old, None, self.clock, None))
            self.redo_stack.clear()
            return self.clock

        def _apply(self, entry, undo):
            kind, sheet, key, old_had, old, new_had, new = entry
            if kind == "clock":
                self.clock = old_had if undo else new_had
                return
            table = self.sheets[sheet] if kind == "cell" else self.names[sheet]
            had, value = (old_had, old) if undo else (new_had, new)
            if had:
                table[key] = value
            else:
                table.pop(key, None)

        def get(self, sheet, addr):
            return self._value(sheet, addr, set())

        def _value(self, sheet, addr, visiting):
            raw = self.sheets[sheet].get(addr)
            if not (isinstance(raw, str) and raw.startswith("=")):
                return raw
            key = (sheet, addr)
            if key in visiting:
                return "#CYCLE!"
            visiting.add(key)
            try:
                return self._formula(sheet, raw, visiting)
            finally:
                visiting.remove(key)

        def _ref(self, sheet, addr, visiting):
            value = self._value(sheet, addr, visiting)
            return 0 if value is None else value

        def _formula(self, sheet, raw, visiting):
            if raw == "=C1+1":
                v = self._ref(sheet, "C1", visiting)
                return v if v in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"} else (v + 1 if isinstance(v, int) else "#TYPE!")
            if raw == "=C1+D1":
                a = self._ref(sheet, "C1", visiting)
                if a in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}:
                    return a
                b = self._ref(sheet, "D1", visiting)
                if b in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}:
                    return b
                return a + b if isinstance(a, int) and isinstance(b, int) else "#TYPE!"
            if raw == "=SUM(C1:D2)":
                total = 0
                for addr in ["C1", "D1", "C2", "D2"]:
                    if addr not in self.sheets[sheet]:
                        continue
                    v = self._value(sheet, addr, visiting)
                    if v in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}:
                        return v
                    if not isinstance(v, int):
                        return "#TYPE!"
                    total += v
                return total
            if raw == '=CONCAT("x", C1)':
                v = self._ref(sheet, "C1", visiting)
                if v in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}:
                    return v
                return "x" + (str(v) if isinstance(v, int) else v)
            if raw == "=IF(C1, D1, D2)":
                c = self._ref(sheet, "C1", visiting)
                if c in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}:
                    return c
                if not isinstance(c, int):
                    return "#TYPE!"
                return self._ref(sheet, "D1" if c else "D2", visiting)
            if raw == "=NOW()+C1":
                v = self._ref(sheet, "C1", visiting)
                if v in {"#PARSE!", "#REF!", "#TYPE!", "#DIV!", "#CYCLE!", "#NAME!"}:
                    return v
                return self.clock + v if isinstance(v, int) else "#TYPE!"
            if raw == "=NAME":
                target = self.names[sheet].get("NAME")
                if target is None:
                    return "#NAME!"
                if ":" in target:
                    return "#REF!"
                return self._ref(sheet, target, visiting)
            return "#PARSE!"

    def snapshot_values(wb):
        result = []
        for sheet_name in sheets:
            sh = wb.sheet(sheet_name)
            for addr in addrs:
                result.append((sheet_name, addr, sh.get(addr)))
        return result

    for seed in range(1000):
        rng = random.Random(seed)
        wb = Workbook.from_json(json.dumps({"version": 1, "clock": 0, "sheets": [{"name": name, "cells": {}, "names": {}} for name in sheets]}))
        naive = Naive()
        for _ in range(50):
            sheet_name = rng.choice(sheets)
            sh = wb.sheet(sheet_name)
            op = rng.randrange(12)
            addr = rng.choice(addrs)
            if op < 3:
                raw = rng.randrange(-5, 6)
                sh.set(addr, raw)
                naive.set(sheet_name, addr, raw)
            elif op < 5:
                raw = rng.choice(["txt", "", "#DIV!"])
                sh.set(addr, raw)
                naive.set(sheet_name, addr, raw)
            elif op == 5:
                raw = rng.choice(formulas + ["=NAME"])
                sh.set(addr, raw)
                naive.set(sheet_name, addr, raw)
            elif op == 6:
                src = rng.choice(addrs)
                try:
                    if isinstance(naive.sheets[sheet_name].get(src), str) and naive.sheets[sheet_name][src].startswith("="):
                        continue
                    sh.copy(src, addr)
                    naive.copy(sheet_name, src, addr)
                except ValueError:
                    pass
            elif op == 7:
                assert wb.undo() == naive.undo()
            elif op == 8:
                assert wb.redo() == naive.redo()
            elif op == 9:
                assert sh.get(addr) == naive.get(sheet_name, addr), seed
            elif op == 10:
                assert wb.advance_clock() == naive.advance_clock()
            else:
                target = rng.choice(["A1", "A1:B2"])
                sh.define_name("NAME", target)
                naive.define_name(sheet_name, "NAME", target)
            if rng.randrange(10) == 0:
                wb = Workbook.from_json(wb.to_json())
                naive.undo_stack.clear()
                naive.redo_stack.clear()
        round_tripped = Workbook.from_json(wb.to_json())
        expected = [(sheet_name, addr, naive.get(sheet_name, addr)) for sheet_name in sheets for addr in addrs]
        assert snapshot_values(wb) == expected, seed
        assert snapshot_values(round_tripped) == expected, seed
