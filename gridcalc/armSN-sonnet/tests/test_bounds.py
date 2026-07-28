from gridcalc import Sheet


def test_deeply_nested_parens_do_not_raise():
    s = Sheet()
    depth = 32
    s.set("A1", "=" + "(" * depth + "1" + ")" * depth)
    assert s.get("A1") == 1


def test_unary_minus_tower_within_512_chars_does_not_raise():
    s = Sheet()
    minus_count = 510  # even -> negations cancel out
    text = "-" * minus_count + "1"
    assert len(text) <= 512
    s.set("A1", "=" + text)
    assert s.get("A1") == 1


def test_256_formula_cell_chain_does_not_raise():
    s = Sheet()

    def addr(i):
        col = chr(ord("A") + i // 99)
        row = i % 99 + 1
        return f"{col}{row}"

    s.set(addr(0), 1)
    for i in range(1, 256):
        s.set(addr(i), f"={addr(i - 1)}+1")
    assert s.get(addr(255)) == 256


def test_magnitude_bound_multiplication_chain_completes():
    s = Sheet()
    # 2**62 stays within the |2**63 - 1| bound.
    formula = "*".join(["2"] * 62)
    s.set("A1", "=" + formula)
    assert s.get("A1") == 2 ** 62


def test_out_of_bounds_formula_elsewhere_does_not_break_confined_gets():
    s = Sheet()
    huge = "=" + "1+" * 1000 + "1"  # far over 512 chars; set must still succeed
    s.set("A1", huge)
    s.set("B1", 1)
    s.set("C1", "=B1+1")
    assert s.get("C1") == 2
