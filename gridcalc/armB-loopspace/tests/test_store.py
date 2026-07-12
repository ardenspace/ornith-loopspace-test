from gridcalc import Sheet


class _IntSubclass(int):
    pass


class _StrSubclass(str):
    pass


def test_get_never_set_cell_returns_none():
    s = Sheet()
    assert s.get("A1") is None


def test_set_get_int_roundtrip():
    s = Sheet()
    s.set("A1", 42)
    assert s.get("A1") == 42


def test_set_get_str_roundtrip():
    s = Sheet()
    s.set("A1", "hello")
    assert s.get("A1") == "hello"


def test_set_formula_stored_without_error():
    s = Sheet()
    s.set("A1", "=B1+C1")
    # Phase 2: formulas are evaluated on get; B1 and C1 are empty (contribute 0)
    assert s.get("A1") == 0


def test_bool_raises_valueerror():
    s = Sheet()
    try:
        s.set("A1", True)
    except ValueError:
        pass
    else:
        raise AssertionError("set(A1, True) did not raise ValueError")


def test_float_raises_valueerror():
    s = Sheet()
    try:
        s.set("A1", 3.14)
    except ValueError:
        pass
    else:
        raise AssertionError("set(A1, 3.14) did not raise ValueError")


def test_none_raises_valueerror():
    s = Sheet()
    try:
        s.set("A1", None)
    except ValueError:
        pass
    else:
        raise AssertionError("set(A1, None) did not raise ValueError")


def test_list_raises_valueerror():
    s = Sheet()
    try:
        s.set("A1", [1, 2, 3])
    except ValueError:
        pass
    else:
        raise AssertionError("set(A1, [1, 2, 3]) did not raise ValueError")


def test_int_subclass_normalized_to_int():
    s = Sheet()
    s.set("A1", _IntSubclass(42))
    assert type(s.get("A1")) is int


def test_str_subclass_normalized_to_str():
    s = Sheet()
    s.set("A1", _StrSubclass("hello"))
    assert type(s.get("A1")) is str


def test_set_returns_none_on_success():
    s = Sheet()
    result = s.set("A1", 42)
    assert result is None


def test_set_replaces_int_with_str():
    s = Sheet()
    s.set("A1", 42)
    s.set("A1", "hello")
    assert s.get("A1") == "hello"


def test_set_replaces_str_with_int():
    s = Sheet()
    s.set("A1", "hello")
    s.set("A1", 42)
    assert s.get("A1") == 42


def test_set_replaces_int_with_formula():
    s = Sheet()
    s.set("A1", 42)
    s.set("A1", "=B1+C1")
    # Phase 2: formulas are evaluated on get; B1 and C1 are empty (contribute 0)
    assert s.get("A1") == 0


def test_failed_set_preserves_content():
    s = Sheet()
    s.set("A1", 42)
    try:
        s.set("A1", True)
    except ValueError:
        pass
    assert s.get("A1") == 42


def test_failed_set_preserves_eval_count():
    s = Sheet()
    s.set("A1", 42)
    before = s.eval_count
    try:
        s.set("A1", True)
    except ValueError:
        pass
    assert s.eval_count == before


def test_literal_set_get_keeps_eval_count_at_zero():
    s = Sheet()
    s.set("A1", 42)
    s.get("A1")
    assert s.eval_count == 0
    s.set("A1", "hello")
    s.get("A1")
    assert s.eval_count == 0
