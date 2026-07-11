"""Held-out acceptance oracle for `kvtx`. Authored independently from the
spec, BEFORE either arm was built. Neither arm (loopspace-B nor solo-A) sees
this file. Run with the target repo root on PYTHONPATH:

    PYTHONPATH=<repo> python3 -m pytest kvtx_oracle.py -q

Grades the Database nested-transaction + count semantics. Embeds an
independent, obviously-correct reference (transactions as overlay layers)
and cross-checks the arm's Database against it over randomized command
sequences, in addition to explicit named cases for the slip-prone
interactions (overwrite/delete count consistency across nested rollback).
"""
import random
import pytest
from kvtx import Database


# ---------- independent reference: transactions as overlay layers ----------
_DEL = object()  # tombstone


class RefDB:
    def __init__(self):
        self.base = {}
        self.stack = []  # list of overlay dicts (key -> value or _DEL)

    def set(self, k, v):
        (self.stack[-1] if self.stack else self.base)[k] = v

    def delete(self, k):
        if self.stack:
            self.stack[-1][k] = _DEL
        else:
            self.base.pop(k, None)

    def _effective(self):
        eff = dict(self.base)
        for layer in self.stack:  # bottom -> top
            for k, val in layer.items():
                if val is _DEL:
                    eff.pop(k, None)
                else:
                    eff[k] = val
        return eff

    def get(self, k):
        for layer in reversed(self.stack):
            if k in layer:
                v = layer[k]
                return None if v is _DEL else v
        return self.base.get(k)

    def count(self, v):
        return sum(1 for val in self._effective().values() if val == v)

    def begin(self):
        self.stack.append({})

    def rollback(self):
        if self.stack:
            self.stack.pop()
            return True
        return False

    def commit(self):
        if not self.stack:
            return False
        eff = self._effective()
        self.base = eff
        self.stack = []
        return True


def fresh():
    return Database()


# ---------- R1: base set/get/delete ----------
def test_set_get():
    d = fresh(); d.set("a", "1"); assert d.get("a") == "1"


def test_get_unset_none():
    assert fresh().get("nope") is None


def test_delete():
    d = fresh(); d.set("a", "1"); d.delete("a"); assert d.get("a") is None


def test_delete_absent_noop():
    d = fresh(); d.delete("ghost"); assert d.get("ghost") is None


def test_overwrite():
    d = fresh(); d.set("a", "1"); d.set("a", "2"); assert d.get("a") == "2"


# ---------- R2: count ----------
def test_count_zero():
    assert fresh().count("x") == 0


def test_count_multi():
    d = fresh(); d.set("a", "x"); d.set("b", "x"); assert d.count("x") == 2


def test_count_overwrite_updates_both():
    d = fresh(); d.set("a", "x"); d.set("b", "x"); d.set("a", "y")
    assert d.count("x") == 1
    assert d.count("y") == 1


def test_count_delete_decrements():
    d = fresh(); d.set("a", "x"); d.set("b", "x"); d.delete("a")
    assert d.count("x") == 1


def test_count_delete_last():
    d = fresh(); d.set("a", "x"); d.delete("a"); assert d.count("x") == 0


def test_types():
    d = fresh(); d.set("a", "x")
    assert isinstance(d.count("x"), int)
    assert isinstance(d.get("a"), str)
    assert d.get("z") is None


# ---------- R3/R8: reads see uncommitted writes ----------
def test_tx_reads_uncommitted():
    d = fresh(); d.begin(); d.set("a", "1")
    assert d.get("a") == "1"
    assert d.count("1") == 1


# ---------- R4/R6: rollback ----------
def test_rollback_undoes_set():
    d = fresh(); d.begin(); d.set("a", "1")
    assert d.rollback() is True
    assert d.get("a") is None


def test_rollback_restores_overwrite():
    d = fresh(); d.set("a", "1"); d.begin(); d.set("a", "2"); d.rollback()
    assert d.get("a") == "1"


def test_rollback_restores_delete():
    d = fresh(); d.set("a", "1"); d.begin(); d.delete("a"); d.rollback()
    assert d.get("a") == "1"


def test_rollback_no_tx_false():
    d = fresh(); d.set("a", "1")
    assert d.rollback() is False
    assert d.get("a") == "1"


def test_nested_rollback_innermost_only():
    d = fresh(); d.set("a", "1")
    d.begin(); d.set("a", "2")
    d.begin(); d.set("a", "3")
    assert d.rollback() is True
    assert d.get("a") == "2"
    assert d.rollback() is True
    assert d.get("a") == "1"


# ---------- R5/R7: commit ----------
def test_commit_applies_all_and_empties():
    d = fresh()
    d.begin(); d.set("a", "1")
    d.begin(); d.set("a", "2")
    assert d.commit() is True
    assert d.get("a") == "2"
    assert d.rollback() is False  # stack empty


def test_commit_no_tx_false():
    d = fresh(); d.set("a", "1")
    assert d.commit() is False
    assert d.get("a") == "1"


# ---------- count / overlay interaction (the slip-prone core) ----------
def test_count_overlay_rollback():
    d = fresh(); d.set("a", "x"); d.begin(); d.set("b", "x")
    assert d.count("x") == 2
    d.rollback()
    assert d.count("x") == 1


def test_count_overlay_commit():
    d = fresh(); d.set("a", "x"); d.begin(); d.set("b", "x"); d.commit()
    assert d.count("x") == 2
    assert d.rollback() is False


def test_count_overwrite_in_tx_then_rollback():
    d = fresh(); d.set("a", "x")
    d.begin(); d.set("a", "y")
    assert d.count("x") == 0
    assert d.count("y") == 1
    d.rollback()
    assert d.count("x") == 1
    assert d.count("y") == 0


def test_count_delete_in_tx_then_rollback():
    d = fresh(); d.set("a", "x"); d.set("b", "x")
    d.begin(); d.delete("a")
    assert d.count("x") == 1
    d.rollback()
    assert d.count("x") == 2


def test_deep_nesting_mixed():
    d = fresh(); d.set("a", "1")
    d.begin(); d.set("a", "2")
    d.begin(); d.delete("a")
    d.begin(); d.set("a", "3")
    assert d.rollback() is True   # undo set a=3
    assert d.get("a") is None     # a deleted at level 2
    assert d.rollback() is True   # undo delete
    assert d.get("a") == "2"
    assert d.commit() is True     # commit remaining -> a=2
    assert d.get("a") == "2"
    assert d.rollback() is False


# ---------- randomized stress vs overlay reference ----------
@pytest.mark.parametrize("seed", range(40))
def test_random_sequence_matches_reference(seed):
    rng = random.Random(seed)
    d = fresh()
    ref = RefDB()
    keys = ["a", "b", "c", "d"]
    vals = ["x", "y", "z"]
    for _ in range(rng.randint(5, 40)):
        op = rng.choices(
            ["set", "delete", "begin", "rollback", "commit", "get", "count"],
            weights=[5, 3, 3, 2, 1, 3, 3],
        )[0]
        if op == "set":
            k = rng.choice(keys); v = rng.choice(vals)
            d.set(k, v); ref.set(k, v)
        elif op == "delete":
            k = rng.choice(keys); d.delete(k); ref.delete(k)
        elif op == "begin":
            d.begin(); ref.begin()
        elif op == "rollback":
            assert d.rollback() == ref.rollback()
        elif op == "commit":
            assert d.commit() == ref.commit()
        elif op == "get":
            k = rng.choice(keys)
            assert d.get(k) == ref.get(k), f"seed={seed} get({k})"
        elif op == "count":
            v = rng.choice(vals)
            assert d.count(v) == ref.count(v), f"seed={seed} count({v})"
    # final full reconciliation
    for k in keys:
        assert d.get(k) == ref.get(k), f"seed={seed} final get({k})"
    for v in vals:
        assert d.count(v) == ref.count(v), f"seed={seed} final count({v})"
