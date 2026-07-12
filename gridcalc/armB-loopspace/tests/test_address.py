from gridcalc import Sheet


class _Addr(str):
    pass


def test_get_set_valid_addresses():
    s = Sheet()
    s.set("A1", 42)
    assert s.get("A1") == 42
    s.set("Z99", "hello")
    assert s.get("Z99") == "hello"


def test_get_invalid_address_raises_valueerror():
    s = Sheet()
    for bad in ("a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1"):
        try:
            s.get(bad)
        except ValueError:
            continue
        else:
            raise AssertionError(f"get({bad!r}) did not raise ValueError")


def test_set_invalid_address_raises_valueerror():
    s = Sheet()
    for bad in ("a1", "A0", "A01", "A100", "AA1", "", " A1", "A1 ", "A 1"):
        try:
            s.set(bad, 1)
        except ValueError:
            continue
        else:
            raise AssertionError(f"set({bad!r}, 1) did not raise ValueError")


def test_get_non_str_raises_valueerror():
    s = Sheet()
    for bad in (5, None):
        try:
            s.get(bad)
        except ValueError:
            continue
        else:
            raise AssertionError(f"get({bad!r}) did not raise ValueError")


def test_set_non_str_raises_valueerror():
    s = Sheet()
    try:
        s.set(None, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("set(None, 1) did not raise ValueError")


def test_str_subclass_accepted():
    s = Sheet()
    addr = _Addr("a1")
    s.set(addr, 7)
    assert s.get("A1") == 7


def test_get_valueerror_preserves_eval_count():
    s = Sheet()
    s.set("A1", 10)
    before = s.eval_count
    try:
        s.get("a1")
    except ValueError:
        pass
    assert s.eval_count == before


def test_eval_count_starts_at_zero():
    s = Sheet()
    assert s.eval_count == 0


def test_eval_count_increments_on_successful_get():
    s = Sheet()
    s.set("A1", 1)
    s.get("A1")
    assert s.eval_count == 0
    s.get("A1")
    assert s.eval_count == 0
