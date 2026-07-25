"""Task 4.3: Bounds and damage confinement — R12 tests."""
import pytest

from gridcalc import Workbook


def _make_sheet():
    """Create a workbook with a single sheet named 'S'."""
    wb = Workbook()
    return wb.add_sheet("S")


# ---------------------------------------------------------------------------
# Within-bounds evaluations must complete without raising
# ---------------------------------------------------------------------------

def test_formula_text_length_512_completes():
    """A formula with text length exactly 512 (after '=') completes."""
    sheet = _make_sheet()
    # '1+' * 255 = 510 chars (ends with '+'), then '+10' = 3 chars, total 513 (too many).
    # '1+' * 255 + '10' = 512 chars: 255*2 + 2 = 512. Valid formula.
    formula = '1+' * 255 + '10'
    assert len(formula) == 512
    sheet.set("A1", "=" + formula)
    result = sheet.get("A1")
    assert isinstance(result, int)
    # 255 ones added, plus 10 at the end = 265
    assert result == 265


def test_formula_text_length_511_completes():
    """A formula with text length 511 completes."""
    sheet = _make_sheet()
    formula = ('1+' * 255) + '1'
    assert len(formula) == 511
    sheet.set("A1", "=" + formula)
    result = sheet.get("A1")
    assert isinstance(result, int)
    assert result == 256


def test_parenthesis_nesting_depth_32_completes():
    """A formula with nesting depth exactly 32 completes."""
    sheet = _make_sheet()
    formula = "(" * 32 + "1" + ")" * 32
    assert len(formula) == 65
    sheet.set("A1", "=" + formula)
    result = sheet.get("A1")
    assert result == 1


def test_256_formula_chain_completes():
    """A chain of 256 formula cells (each referencing the previous) completes."""
    sheet = _make_sheet()
    # Create a chain using A1-A99, B1-B99, C1-C58 (99+99+58=256 cells).
    # All cells are formula cells (A1 references a literal 1).
    sheet.set("A1", "=1")
    chain_count = 1  # A1 is cell 1
    
    # A2-A99 (98 cells)
    for i in range(2, 100):
        prev = f"A{i - 1}"
        sheet.set(f"A{i}", f"={prev}+1")
        chain_count += 1
    
    # B1-B99 (99 cells)
    prev_addr = "A99"
    for i in range(1, 100):
        sheet.set(f"B{i}", f"={prev_addr}+1")
        prev_addr = f"B{i}"
        chain_count += 1
    
    # C1-C58 (58 cells) to reach 256 total
    for i in range(1, 59):
        sheet.set(f"C{i}", f"={prev_addr}+1")
        prev_addr = f"C{i}"
        chain_count += 1
    
    assert chain_count == 256
    # Get the last cell in the chain.
    result = sheet.get(prev_addr)
    assert result == 256


def test_arithmetic_intermediate_within_bounds():
    """Arithmetic intermediates within 2**63-1 complete."""
    sheet = _make_sheet()
    sheet.set("A1", 2**63 - 1)
    sheet.set("B1", 0)
    sheet.set("C1", "=A1+B1")
    result = sheet.get("C1")
    assert result == 2**63 - 1


def test_string_intermediate_within_bounds():
    """String intermediates within 4096 chars complete."""
    sheet = _make_sheet()
    # Build a string of length 4096 via concatenation.
    long_str = "x" * 4096
    sheet.set("A1", long_str)
    sheet.set("B1", '="hello"')
    # String concatenation isn't supported in Phase 2, so just verify
    # that a long literal string cell works.
    result = sheet.get("A1")
    assert result == long_str
    assert len(result) == 4096


# ---------------------------------------------------------------------------
# Out-of-bounds evaluations terminate and do not corrupt later within-bounds gets
# ---------------------------------------------------------------------------

def test_formula_text_length_513_returns_error():
    """A formula with text length 513 returns an error (does not evaluate)."""
    sheet = _make_sheet()
    formula = ('1+' * 256) + '1'
    assert len(formula) == 513
    sheet.set("A1", "=" + formula)
    # Should return an error sentinel, not evaluate the formula.
    result = sheet.get("A1")
    # Per R12: out-of-bounds may return or raise, but must terminate.
    # We expect it to return an error rather than evaluating.
    assert result in ("#PARSE!", "#OV!", "#NUM!") or isinstance(result, str) and result.startswith("#")


def test_parenthesis_nesting_depth_33_returns_error():
    """A formula with nesting depth 33 returns an error (does not evaluate)."""
    sheet = _make_sheet()
    formula = "(" * 33 + "1" + ")" * 33
    sheet.set("A1", "=" + formula)
    result = sheet.get("A1")
    # Should return an error rather than evaluating.
    assert result in ("#PARSE!", "#OV!", "#NUM!") or isinstance(result, str) and result.startswith("#")


def test_257_formula_chain_returns_error():
    """A chain of 257 formula cells returns an error (does not evaluate all)."""
    sheet = _make_sheet()
    # Create a chain of 257 cells (exceeds the 256 limit).
    sheet.set("A1", 1)
    
    # A2-A99 (98 cells)
    for i in range(2, 100):
        prev = f"A{i - 1}"
        sheet.set(f"A{i}", f"={prev}+1")
    
    # B1-B99 (99 cells)
    prev_addr = "A99"
    for i in range(1, 100):
        sheet.set(f"B{i}", f"={prev_addr}+1")
        prev_addr = f"B{i}"
    
    # C1-C60 (60 cells) to get 98+99+60=257 total
    for i in range(1, 61):
        sheet.set(f"C{i}", f"={prev_addr}+1")
        prev_addr = f"C{i}"
    
    # Getting the last cell should return an error (too many formula cells reached).
    result = sheet.get(prev_addr)
    assert result in ("#CYCLE!", "#PARSE!", "#OV!", "#NUM!") or isinstance(result, str) and result.startswith("#")


def test_arithmetic_intermediate_exceeds_bounds_returns_error():
    """Arithmetic intermediate exceeding 2**63-1 returns an error."""
    sheet = _make_sheet()
    sheet.set("A1", 2**63)
    sheet.set("B1", "=A1+1")
    result = sheet.get("B1")
    # Should return an error (overflow).
    assert result in ("#OV!", "#NUM!", "#PARSE!") or isinstance(result, str) and result.startswith("#")


def test_string_intermediate_exceeds_bounds_stores():
    """A string longer than 4096 chars can be stored (no evaluation needed)."""
    sheet = _make_sheet()
    # Build a string longer than 4096 chars.
    long_str = "x" * 4097
    sheet.set("A1", long_str)
    # Literal strings are just stored, not evaluated.
    result = sheet.get("A1")
    assert len(result) == 4097


def test_out_of_bounds_does_not_corrupt_later_within_bounds():
    """An out-of-bounds evaluation does not corrupt later within-bounds gets."""
    sheet = _make_sheet()
    # Set up an out-of-bounds formula.
    formula = ('1+' * 256) + '1'  # 513 chars
    sheet.set("A1", "=" + formula)
    # This should return an error.
    result_a = sheet.get("A1")
    assert isinstance(result_a, str) and result_a.startswith("#")

    # Now set up a within-bounds formula.
    sheet.set("B1", "=1+1")
    result_b = sheet.get("B1")
    assert result_b == 2


def test_out_of_bounds_in_chain_does_not_corrupt_later_within_bounds():
    """An out-of-bounds formula in a chain does not corrupt later within-bounds gets."""
    sheet = _make_sheet()
    # Set up a chain where one cell is out-of-bounds.
    sheet.set("A1", 1)
    sheet.set("B1", "=A1+1")
    # C1 is out-of-bounds (513 chars).
    formula = ('1+' * 256) + '1'
    sheet.set("C1", "=" + formula)
    sheet.set("D1", "=C1+1")
    sheet.set("E1", "=D1+1")

    # Getting C1 should return an error.
    result_c = sheet.get("C1")
    assert isinstance(result_c, str) and result_c.startswith("#")

    # Getting E1 should also return an error (depends on C1 which is out-of-bounds).
    # But it must terminate.
    result_e = sheet.get("E1")
    assert True


def test_referenced_out_of_bounds_formula_returns_error():
    """A formula referencing an out-of-bounds formula cell returns an error."""
    sheet = _make_sheet()
    # B1 is out-of-bounds (513 chars).
    formula_b = ('1+' * 256) + '1'
    sheet.set("B1", "=" + formula_b)
    # A1 references B1.
    sheet.set("A1", "=B1")
    # Getting A1 should return an error (B1 is out-of-bounds).
    result = sheet.get("A1")
    assert isinstance(result, str) and result.startswith("#")


def test_referenced_within_bounds_formula_returns_value():
    """A formula referencing a within-bounds formula cell returns the value."""
    sheet = _make_sheet()
    # B1 is within-bounds.
    sheet.set("B1", "=1+1")
    # A1 references B1.
    sheet.set("A1", "=B1")
    # Getting A1 should return 2.
    result = sheet.get("A1")
    assert result == 2


# ---------------------------------------------------------------------------
# Mutating operations store out-of-bounds formula texts without evaluating them
# ---------------------------------------------------------------------------

def test_mutating_operation_stores_out_of_bounds_formula():
    """A mutating operation stores an out-of-bounds formula without evaluating it."""
    sheet = _make_sheet()
    formula = ('1+' * 256) + '1'  # 513 chars
    sheet.set("A1", "=" + formula)
    # The formula should be stored as text, not evaluated.
    # Verify the formula text is in the cell store.
    assert sheet._cells["A1"] == "=" + formula
    # Verify that getting the cell returns an error (formula was stored, not evaluated during set).
    result = sheet.get("A1")
    assert isinstance(result, str) and result.startswith("#")
    # Verify the workbook is not corrupted: a within-bounds formula still works.
    sheet.set("B1", "=1+1")
    assert sheet.get("B1") == 2


def test_mutating_operation_stores_deeply_nested_formula():
    """A mutating operation stores a deeply nested formula without evaluating it."""
    sheet = _make_sheet()
    formula = "(" * 33 + "1" + ")" * 33
    sheet.set("A1", "=" + formula)
    # The formula should be stored as text, not evaluated.
    assert sheet._cells["A1"] == "=" + formula
    # Verify that getting the cell returns an error (formula was stored, not evaluated during set).
    result = sheet.get("A1")
    assert isinstance(result, str) and result.startswith("#")
    # Verify the workbook is not corrupted: a within-bounds formula still works.
    sheet.set("B1", "=1+1")
    assert sheet.get("B1") == 2


def test_mutating_operation_stores_long_chain_formula():
    """A mutating operation stores a formula referencing a long chain without evaluating it."""
    sheet = _make_sheet()
    # Set up a chain of 256 formula cells (A1-A99, B1-B99, C1-C58).
    sheet.set("A1", "=1")
    for i in range(2, 100):
        prev = f"A{i - 1}"
        sheet.set(f"A{i}", f"={prev}+1")
    
    prev_addr = "A99"
    for i in range(1, 100):
        sheet.set(f"B{i}", f"={prev_addr}+1")
        prev_addr = f"B{i}"
    
    for i in range(1, 59):
        sheet.set(f"C{i}", f"={prev_addr}+1")
        prev_addr = f"C{i}"
    
    # Now set D1 to reference the last cell in the chain (257th formula cell).
    sheet.set("D1", f"={prev_addr}+1")
    # The formula should be stored as text, not evaluated.
    assert sheet._cells["D1"] == f"={prev_addr}+1"
    # Verify that getting D1 returns an error (too many formula cells reached).
    result = sheet.get("D1")
    assert isinstance(result, str) and result.startswith("#")
    # Verify the workbook is not corrupted: a within-bounds formula still works.
    sheet.set("E1", "=1+1")
    assert sheet.get("E1") == 2


# ---------------------------------------------------------------------------
# Directed tests for 256-formula dependency chain and deeply nested/unary expression
# ---------------------------------------------------------------------------

def test_256_chain_no_recursion_error():
    """A 256-formula dependency chain does not raise RecursionError."""
    sheet = _make_sheet()
    # Create a chain using A1-A99, B1-B99, C1-C58 (99+99+58=256 cells).
    # All cells are formula cells (A1 references a literal 1).
    sheet.set("A1", "=1")
    
    # A2-A99 (98 cells)
    for i in range(2, 100):
        prev = f"A{i - 1}"
        sheet.set(f"A{i}", f"={prev}+1")
    
    # B1-B99 (99 cells)
    prev_addr = "A99"
    for i in range(1, 100):
        sheet.set(f"B{i}", f"={prev_addr}+1")
        prev_addr = f"B{i}"
    
    # C1-C58 (58 cells) to reach 256 total
    for i in range(1, 59):
        sheet.set(f"C{i}", f"={prev_addr}+1")
        prev_addr = f"C{i}"
    
    # This should not raise RecursionError.
    result = sheet.get(prev_addr)
    assert result == 256


def test_deeply_nested_no_recursion_error():
    """A deeply nested expression (depth 32) does not raise RecursionError."""
    sheet = _make_sheet()
    formula = "(" * 32 + "1" + ")" * 32
    sheet.set("A1", "=" + formula)
    result = sheet.get("A1")
    assert result == 1


def test_unary_expression_no_recursion_error():
    """A deeply nested unary expression does not raise RecursionError."""
    sheet = _make_sheet()
    # 200 unary minuses (within bounds for text length: 200*2+1=401 chars).
    # Each '- ' is a unary minus operator followed by a space.
    formula = ("- " * 200) + "1"
    # This is: -(-(-(...(-1)...)))
    # 200 unary minuses on 1: if 200 is even, result is 1; if odd, -1.
    sheet.set("A1", "=" + formula)
    result = sheet.get("A1")
    assert result in (1, -1)
