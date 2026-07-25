import random

import pytest

from gridcalc import Workbook
from tests.reference_model import NaiveWorkbook


POOL_SHEETS = ("S1", "S2", "S3")
POOL_ADDRS = ("A1", "A2", "B1", "B2")
POOL = tuple((sheet, addr) for sheet in POOL_SHEETS for addr in POOL_ADDRS)
NAMES = ("AA", "BB", "CC")


def _impl_get(wb, sheet, addr):
    return wb.sheet(sheet).get(addr)


def _snapshot(impl, ref):
    return (
        tuple(impl.sheet_names),
        impl.clock,
        tuple((sheet, addr, _impl_get(impl, sheet, addr)) for sheet, addr in POOL if sheet in impl.sheet_names),
        ref.snapshot(POOL),
    )


def _assert_pool_matches(impl, ref):
    assert tuple(impl.sheet_names) == tuple(ref.sheet_names)
    assert impl.clock == ref.clock
    for sheet, addr in POOL:
        if sheet in impl.sheet_names:
            assert _impl_get(impl, sheet, addr) == ref.get(sheet, addr)


def _call_both(impl_call, ref_call, impl, ref):
    before = _snapshot(impl, ref)
    impl_error = ref_error = None
    try:
        impl_result = impl_call()
    except ValueError as exc:
        impl_error = exc
        impl_result = None
    try:
        ref_result = ref_call()
    except ValueError as exc:
        ref_error = exc
        ref_result = None
    if impl_error is not None or ref_error is not None:
        assert impl_error is not None and ref_error is not None
        assert _snapshot(impl, ref) == before
    else:
        if isinstance(impl_result, (type(None), bool, int, str)):
            assert impl_result == ref_result
    _assert_pool_matches(impl, ref)


def _ensure_pool_sheets(impl, ref):
    for sheet in POOL_SHEETS:
        if sheet not in impl.sheet_names:
            _call_both(lambda sheet=sheet: impl.add_sheet(sheet), lambda sheet=sheet: ref.add_sheet(sheet), impl, ref)


def _ref_to_json(ref):
    return ref._snapshot_state()


def _ref_from_json(state):
    loaded = NaiveWorkbook()
    loaded._restore_state(state)
    return loaded


def _assert_roundtrip_matches(impl, ref):
    loaded = Workbook.from_json(impl.to_json())
    loaded_ref = _ref_from_json(_ref_to_json(ref))
    assert tuple(loaded.sheet_names) == tuple(impl.sheet_names)
    assert loaded.clock == impl.clock
    _assert_pool_matches(loaded, loaded_ref)
    return loaded, loaded_ref


def _cell_arg(rng, default_sheet=None, allow_bad=False):
    sheet, addr = rng.choice(POOL)
    if allow_bad and rng.randrange(9) == 0:
        return rng.choice(("Missing!A1", "S1 ! A1", "S1!A0"))
    if rng.randrange(2) == 0 or sheet == default_sheet:
        return addr
    return f"{sheet}!{addr}"


def _target(rng, allow_bad=False):
    sheet, addr = rng.choice(POOL)
    if allow_bad and rng.randrange(9) == 0:
        return rng.choice(("Missing!A1", "S1 ! A1", "A2:A1"))
    if rng.randrange(2) == 0:
        return addr
    if rng.randrange(2) == 0:
        return f"{sheet}!{addr}"
    return f"{sheet}!A1:B2"


def _formula(rng, host_sheet):
    remote_sheet, remote_addr = rng.choice(POOL)
    local_addr = rng.choice(POOL_ADDRS)
    name = rng.choice(NAMES)
    choices = (
        f"={local_addr}+1",
        f"={remote_sheet}!{remote_addr}+1",
        f"=SUM({remote_sheet}!A1:B2)",
        f"=COUNT({remote_sheet}!A1:B2)+{local_addr}",
        f"={name}+{remote_sheet}!{remote_addr}",
        f"=IF({remote_sheet}!{remote_addr},{local_addr},SUM({host_sheet}!A1:B2))",
        f'=CONCAT({local_addr},"x")',
        f'=LEN(CONCAT({remote_sheet}!{remote_addr},"z"))',
        f'="x"+{remote_sheet}!{remote_addr}',
    )
    return rng.choice(choices)


def _raw_value(rng, sheet):
    pick = rng.randrange(6)
    if pick == 0:
        return rng.randint(-20, 20)
    if pick == 1:
        return rng.choice(("text", "", "7"))
    return _formula(rng, sheet)


def _run_op(rng, impl, ref, forced_op=None):
    op = forced_op or rng.choice(("set", "get", "copy", "define_name", "add_sheet", "undo", "redo", "advance_clock", "roundtrip"))
    if op not in ("add_sheet", "undo", "redo"):
        _ensure_pool_sheets(impl, ref)

    if op == "set":
        sheet, addr = rng.choice(POOL)
        raw = True if rng.randrange(30) == 0 else _raw_value(rng, sheet)
        _call_both(lambda: impl.sheet(sheet).set(addr, raw), lambda: ref.set(sheet, addr, raw), impl, ref)
    elif op == "get":
        sheet, addr = rng.choice(POOL)
        if rng.randrange(25) == 0:
            addr = rng.choice(("A0", "AA1", "A100"))
        _call_both(lambda: impl.sheet(sheet).get(addr), lambda: ref.get(sheet, addr), impl, ref)
    elif op == "copy":
        default_sheet = rng.choice(POOL_SHEETS)
        src = _cell_arg(rng, default_sheet, allow_bad=True)
        dst = _cell_arg(rng, default_sheet, allow_bad=True)
        _call_both(lambda: impl.sheet(default_sheet).copy(src, dst), lambda: ref.copy(default_sheet, src, dst), impl, ref)
    elif op == "define_name":
        sheet = rng.choice(POOL_SHEETS)
        name = rng.choice(NAMES + ("A1", "SUM"))
        target = _target(rng, allow_bad=True)
        _call_both(lambda: impl.sheet(sheet).define_name(name, target), lambda: ref.define_name(sheet, name, target), impl, ref)
    elif op == "add_sheet":
        name = rng.choice(POOL_SHEETS + ("Bad Name", "1Bad"))
        _call_both(lambda: impl.add_sheet(name), lambda: ref.add_sheet(name), impl, ref)
        _ensure_pool_sheets(impl, ref)
    elif op == "undo":
        _call_both(lambda: impl.undo(), lambda: ref.undo(), impl, ref)
        _ensure_pool_sheets(impl, ref)
    elif op == "redo":
        _call_both(lambda: impl.redo(), lambda: ref.redo(), impl, ref)
        _ensure_pool_sheets(impl, ref)
    elif op == "advance_clock":
        _call_both(lambda: impl.advance_clock(), lambda: ref.advance_clock(), impl, ref)
    elif op == "roundtrip":
        impl, ref = _assert_roundtrip_matches(impl, ref)
        ref._journal.clear()
        ref._redo_stack.clear()
    else:
        raise AssertionError(op)
    return impl, ref


@pytest.mark.parametrize("seed", range(1000))
def test_full_feature_differential_floor(seed):
    rng = random.Random(seed)
    impl = Workbook()
    ref = NaiveWorkbook()
    for sheet in POOL_SHEETS:
        _call_both(lambda sheet=sheet: impl.add_sheet(sheet), lambda sheet=sheet: ref.add_sheet(sheet), impl, ref)

    forced = ("set", "get", "copy", "define_name", "add_sheet", "advance_clock", "undo", "redo", "roundtrip")
    for step in range(60):
        impl, ref = _run_op(rng, impl, ref, forced[step] if step < len(forced) else None)
    _assert_roundtrip_matches(impl, ref)
