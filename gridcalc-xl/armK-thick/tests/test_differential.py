import random

import pytest

from gridcalc import Workbook

from tests.reference_model import NaiveSheet


ADDRS = ("A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2", "E1", "E2", "F1", "F2")
SEEDS = tuple(range(1000))
SEQUENCE_LENGTH = 50


def test_reference_model_recomputes_formula_after_literal_edit():
    ref = NaiveSheet()
    ref.set("A1", 1)
    ref.set("B1", "=A1+1")
    assert ref.get("B1") == 2
    ref.set("A1", 10)
    assert ref.get("B1") == 11


def _capture(sheet):
    return tuple((addr, sheet.get(addr)) for addr in ADDRS)


def _assert_unchanged_after_value_error(call, sheet, ref, seed, step):
    before = _capture(sheet)
    ref_before = ref.snapshot(ADDRS)
    eval_count_before = sheet.eval_count
    with pytest.raises(ValueError):
        call()
    eval_count_after_call = sheet.eval_count
    after = _capture(sheet)
    ref_after = ref.snapshot(ADDRS)
    assert after == before, (seed, step, "workbook state changed after ValueError")
    assert ref_after == ref_before, (seed, step, "reference state changed after ValueError")
    assert eval_count_after_call == eval_count_before, (seed, step, "eval_count changed after ValueError")
    assert sheet.eval_count == eval_count_before, (seed, step, "eval_count changed after post-error reads")


def test_value_errors_leave_values_and_eval_count_unchanged():
    sheet = Workbook().add_sheet("S")
    ref = NaiveSheet()
    sheet.set("A1", 1)
    ref.set("A1", 1)
    sheet.set("B1", "=A1+1")
    ref.set("B1", "=A1+1")
    assert sheet.get("B1") == ref.get("B1") == 2

    _assert_unchanged_after_value_error(lambda: sheet.set("A1", True), sheet, ref, "direct", "set_bad")
    _assert_unchanged_after_value_error(lambda: sheet.get("A0"), sheet, ref, "direct", "get_bad")
    _assert_unchanged_after_value_error(lambda: sheet.set("A0", "=1+1"), sheet, ref, "direct", "formula_bad")


def _literal(rng):
    choices = [rng.randint(-20, 20), "text", "", "#DIV!"]
    return rng.choice(choices)


def _formula(rng):
    a = rng.choice(ADDRS)
    b = rng.choice(ADDRS)
    formulas = [
        f"={a}+{rng.randint(-5, 5)}",
        f"={a}+{b}",
        f"=SUM({a}:{b})",
        f"=MIN({a}:{b})",
        f"=MAX({a}:{b})",
        f"=COUNT({a}:{b})",
        f"={rng.randint(0, 9)}/{rng.randint(0, 3)}",
        f"={a}=\"text\"",
        "=1+2*3",
        "=(1+2)*3",
    ]
    return rng.choice(formulas)


def _sequence(seed):
    rng = random.Random(seed)
    ops = [
        ("set_ok", "A1", _literal(rng)),
        ("set_bad", rng.choice(("A0", "AA1", "a1", "A100", 123)), _literal(rng)),
        ("get_ok", "A1", None),
        ("get_bad", rng.choice(("", "A01", "S!A1", "Z100", None)), None),
        ("formula_ok", "B1", _formula(rng)),
        ("formula_bad", rng.choice(("A0", "AA1", "a1", "A100", 123)), _formula(rng)),
    ]
    rng.shuffle(ops)
    kinds = {addr: "empty" for addr in ADDRS}
    for op, addr, _ in ops:
        if op == "set_ok":
            kinds[addr] = "literal"
        elif op == "formula_ok":
            kinds[addr] = "formula"
    while len(ops) < SEQUENCE_LENGTH:
        op = rng.choice(("set_ok", "set_bad", "get_ok", "get_bad", "formula_ok", "formula_bad"))
        if op == "set_ok":
            addr = rng.choice([addr for addr in ADDRS if kinds[addr] != "formula"])
            ops.append((op, addr, _literal(rng)))
            kinds[addr] = "literal"
        elif op == "formula_ok":
            addr = rng.choice(ADDRS)
            ops.append((op, addr, _formula(rng)))
            kinds[addr] = "formula"
        elif op == "set_bad":
            ops.append((op, rng.choice(("A0", "AA1", "a1", "A100", 123)), _literal(rng)))
        elif op == "get_ok":
            ops.append((op, rng.choice(ADDRS), None))
        elif op == "get_bad":
            ops.append((op, rng.choice(("", "A01", "S!A1", "Z100", None)), None))
        else:
            ops.append((op, rng.choice(("A0", "AA1", "a1", "A100", 123)), _formula(rng)))
    return ops


@pytest.mark.parametrize("seed", SEEDS)
def test_randomized_sequences_match_naive_reference(seed):
    wb = Workbook()
    sheet = wb.add_sheet("S")
    ref = NaiveSheet()
    seen = set()

    for step, (op, addr, raw) in enumerate(_sequence(seed)):
        try:
            if op in ("set_ok", "formula_ok"):
                sheet.set(addr, raw)
                ref.set(addr, raw)
                seen.add(op)
            elif op in ("set_bad", "formula_bad"):
                _assert_unchanged_after_value_error(lambda: sheet.set(addr, raw), sheet, ref, seed, step)
                seen.add(op)
            elif op == "get_ok":
                assert sheet.get(addr) == ref.get(addr), (seed, step, op, addr)
                seen.add(op)
            else:
                _assert_unchanged_after_value_error(lambda: sheet.get(addr), sheet, ref, seed, step)
                seen.add(op)
        except AssertionError:
            raise

        for check_addr in ADDRS:
            assert sheet.get(check_addr) == ref.get(check_addr), (seed, step, op, addr, raw, check_addr)

    assert seen == {"set_ok", "set_bad", "get_ok", "get_bad", "formula_ok", "formula_bad"}
