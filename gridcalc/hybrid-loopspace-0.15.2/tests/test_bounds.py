from gridcalc import Sheet


def test_32_deep_parens_within_bounds():
    """32-deep nested parentheses should evaluate without raising."""
    sheet = Sheet()
    formula = "(" * 32 + "1" + ")" * 32
    sheet.set("A1", f"={formula}")
    result = sheet.get("A1")
    assert result == 1


def test_33_deep_parens_exceeds_depth_bound():
    """33-deep nested parentheses exceeds the depth bound."""
    sheet = Sheet()
    formula = "(" * 33 + "1" + ")" * 33
    sheet.set("A1", f"={formula}")
    result = sheet.get("A1")
    assert result == "#PARSE!"


def test_510_deep_unary_minus_tower_within_bounds():
    """~510-deep unary-minus tower inside 512 chars should evaluate without raising."""
    sheet = Sheet()
    minus_tower = "-" * 509 + "1"
    assert len(minus_tower) <= 512
    sheet.set("A1", f"={minus_tower}")
    result = sheet.get("A1")
    assert result == -1


def test_511_deep_unary_minus_exceeds_source_len():
    """513-char formula (after stripping =) exceeds the source length bound."""
    sheet = Sheet()
    minus_tower = "-" * 512 + "1"
    assert len(minus_tower) > 512
    sheet.set("A1", f"={minus_tower}")
    result = sheet.get("A1")
    assert result == "#PARSE!"


def test_256_formula_cell_chain_evaluates():
    """256-formula-cell reference chain should evaluate without raising."""
    sheet = Sheet()
    sheet.set("A1", "=1")
    prev_addr = "A1"
    for i in range(2, 257):
        col_idx = (i - 1) // 99
        row = (i - 1) % 99 + 1
        col = chr(ord("A") + col_idx)
        addr = f"{col}{row}"
        sheet.set(addr, f"={prev_addr}+1")
        prev_addr = addr
    col_idx = 255 // 99
    row = 255 % 99 + 1
    last_addr = f"{chr(ord('A') + col_idx)}{row}"
    result = sheet.get(last_addr)
    assert result == 256


def test_257_formula_cell_chain_exceeds_chain_limit():
    """257-formula-cell reference chain exceeds the chain limit."""
    sheet = Sheet()
    sheet.set("A1", "=1")
    prev_addr = "A1"
    for i in range(2, 258):
        col_idx = (i - 1) // 99
        row = (i - 1) % 99 + 1
        col = chr(ord("A") + col_idx)
        addr = f"{col}{row}"
        sheet.set(addr, f"={prev_addr}+1")
        prev_addr = addr
    col_idx = 256 // 99
    row = 256 % 99 + 1
    last_addr = f"{chr(ord('A') + col_idx)}{row}"
    result = sheet.get(last_addr)
    assert result == "#CHAIN!"


def test_magnitude_bound_within_limit():
    """Within-bounds arithmetic with intermediates/results at or below |2**63 - 1| completes without raising."""
    sheet = Sheet()
    max_val = 2**63 - 1
    sheet.set("A1", max_val - 1)
    sheet.set("B1", "=1")
    sheet.set("C1", "=A1+B1")
    result = sheet.get("C1")
    assert result == max_val


def test_magnitude_bound_exceeds_limit():
    """Arithmetic that exceeds the magnitude bound should return #OVF!."""
    sheet = Sheet()
    max_val = 2**63 - 1
    sheet.set("A1", max_val)
    sheet.set("B1", max_val)
    sheet.set("C1", "=A1+B1")
    result = sheet.get("C1")
    assert result == "#OVF!"


def test_confinement_set_succeeds_with_large_formula():
    """>512-char formula in unrelated cell should not prevent set from succeeding."""
    sheet = Sheet()
    large_formula = "=" + "1+" * 300
    sheet.set("Z1", large_formula)
    sheet.set("A1", "=1+2")
    result = sheet.get("A1")
    assert result == 3


def test_confinement_within_bounds_keeps_guarantees():
    """Within-bounds evaluation keeps all guarantees even when out-of-bounds formulas exist elsewhere."""
    sheet = Sheet()
    large_formula = "=" + "1+" * 300
    sheet.set("Z1", large_formula)
    sheet.set("A1", "=1")
    sheet.set("B1", "=A1+1")
    result = sheet.get("B1")
    assert result == 2


def test_magnitude_bound_multiplication_chain():
    """Within-bounds multiplication chain peaking near |2**63 - 1| completes without raising."""
    sheet = Sheet()
    sheet.set("A1", 3037000499)
    sheet.set("B1", "=A1*3037000499")
    sheet.set("C1", "=B1*1")
    result = sheet.get("C1")
    assert result == 9223372030926249001


def test_confinement_unary_minus_tower_with_large_formula():
    """~510-deep unary-minus tower evaluates correctly even when >512-char formula sits in unrelated cell."""
    sheet = Sheet()
    large_formula = "=" + "1+" * 300
    sheet.set("Z1", large_formula)
    minus_tower = "-" * 509 + "1"
    assert len(minus_tower) <= 512
    sheet.set("A1", f"={minus_tower}")
    result = sheet.get("A1")
    assert result == -1


def test_confinement_256_chain_with_large_formula():
    """256-formula-cell chain evaluates correctly even when >512-char formula sits in unrelated cell."""
    sheet = Sheet()
    large_formula = "=" + "1+" * 300
    sheet.set("Z1", large_formula)
    sheet.set("A1", "=1")
    prev_addr = "A1"
    for i in range(2, 257):
        col_idx = (i - 1) // 99
        row = (i - 1) % 99 + 1
        col = chr(ord("A") + col_idx)
        addr = f"{col}{row}"
        sheet.set(addr, f"={prev_addr}+1")
        prev_addr = addr
    col_idx = 255 // 99
    row = 255 % 99 + 1
    last_addr = f"{chr(ord('A') + col_idx)}{row}"
    result = sheet.get(last_addr)
    assert result == 256


def test_confinement_32_deep_parens_with_large_formula():
    """32-deep nested parentheses evaluates correctly even when >512-char formula sits in unrelated cell."""
    sheet = Sheet()
    large_formula = "=" + "1+" * 300
    sheet.set("Z1", large_formula)
    formula = "(" * 32 + "1" + ")" * 32
    sheet.set("A1", f"={formula}")
    result = sheet.get("A1")
    assert result == 1


def test_confinement_magnitude_arithmetic_with_large_formula():
    """Near-bound magnitude arithmetic completes without raising even when >512-char formula sits in unrelated cell."""
    sheet = Sheet()
    large_formula = "=" + "1+" * 300
    sheet.set("Z1", large_formula)
    max_val = 2**63 - 1
    sheet.set("A1", max_val - 1)
    sheet.set("B1", "=1")
    sheet.set("C1", "=A1+B1")
    result = sheet.get("C1")
    assert result == max_val
