from gridcalc import Sheet


def test_irrelevant_edit_outside_closure_adds_zero_eval_count():
    """Edit outside X's closure should not trigger recomputation of X."""
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("X1", "=A1+1")
    sheet.get("X1")
    assert sheet.get("X1") == 11
    before = sheet.eval_count
    sheet.set("Z1", 99)
    result = sheet.get("X1")
    assert result == 11
    assert sheet.eval_count - before == 0


def test_relevant_edit_inside_closure_recomputes():
    """Edit inside X's closure should trigger recomputation."""
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("X1", "=A1+1")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("A1", 20)
    result = sheet.get("X1")
    assert result == 21
    assert sheet.eval_count - before >= 1


def test_relevant_edit_set_x_recomputes():
    """Setting X itself should trigger recomputation."""
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("X1", "=A1+1")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("X1", "=A1+2")
    result = sheet.get("X1")
    assert result == 12
    assert sheet.eval_count - before >= 1


def test_formula_outside_closure_not_recomputed():
    """Formula Z1 should not be recomputed when editing A1 if Z1 doesn't depend on A1."""
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("X1", "=A1+1")
    sheet.set("Z1", "=99")
    sheet.get("X1")
    sheet.get("Z1")
    before_x = sheet.eval_count
    sheet.set("A1", 20)
    sheet.get("X1")
    after_x = sheet.eval_count
    assert after_x - before_x == 1
    assert sheet.get("Z1") == 99


def test_closure_includes_direct_refs():
    """Closure should include all direct cell references."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", 2)
    sheet.set("X1", "=A1+B1")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("A1", 10)
    result = sheet.get("X1")
    assert result == 12
    assert sheet.eval_count - before >= 1


def test_closure_includes_range_members():
    """Closure should include all members of valid ranges, including empty cells."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("A2", 2)
    sheet.set("A3", 3)
    sheet.set("X1", "=SUM(A1:A3)")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("A2", 20)
    result = sheet.get("X1")
    assert result == 24
    assert sheet.eval_count - before >= 1


def test_closure_includes_empty_cells_in_range():
    """Closure should include empty cells in ranges."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("A3", 3)
    sheet.set("X1", "=SUM(A1:A3)")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("A2", 20)
    result = sheet.get("X1")
    assert result == 24
    assert sheet.eval_count - before >= 1


def test_closure_includes_count_range_members():
    """Closure should include all members of COUNT ranges."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("A2", 2)
    sheet.set("X1", "=COUNT(A1:A2)")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("A1", 10)
    result = sheet.get("X1")
    assert result == 2
    assert sheet.eval_count - before >= 1


def test_invalid_range_adds_no_members_to_closure():
    """Invalid ranges should not add members to closure."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("X1", "=SUM(B2:A1)")
    sheet.get("X1")
    assert sheet.get("X1") == "#REF!"
    before = sheet.eval_count
    sheet.set("A1", 10)
    result = sheet.get("X1")
    assert result == "#REF!"
    assert sheet.eval_count - before == 0


def test_parse_error_closure_is_self():
    """#PARSE! closure should be just the cell itself."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("X1", "=1 $ 2")
    sheet.get("X1")
    assert sheet.get("X1") == "#PARSE!"
    before = sheet.eval_count
    sheet.set("A1", 10)
    result = sheet.get("X1")
    assert result == "#PARSE!"
    assert sheet.eval_count - before == 0


def test_literal_get_adds_zero_eval_count():
    """Getting a literal cell should not increment eval_count."""
    sheet = Sheet()
    sheet.set("A1", 42)
    before = sheet.eval_count
    sheet.get("A1")
    assert sheet.eval_count - before == 0


def test_empty_get_adds_zero_eval_count():
    """Getting an empty cell should not increment eval_count."""
    sheet = Sheet()
    before = sheet.eval_count
    sheet.get("Z99")
    assert sheet.eval_count - before == 0


def test_identical_set_still_counts_as_edit():
    """Setting a cell to the same value should still trigger invalidation."""
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("X1", "=A1+1")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("A1", 10)
    result = sheet.get("X1")
    assert result == 11
    assert sheet.eval_count - before >= 1


def test_cascade_invalidation():
    """If X depends on Y and Y depends on A, editing Y should invalidate both."""
    sheet = Sheet()
    sheet.set("A1", 10)
    sheet.set("Y1", "=A1+1")
    sheet.set("X1", "=Y1+1")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("Y1", "=A1+2")
    result = sheet.get("X1")
    assert result == 13
    assert sheet.eval_count - before >= 2


def test_transitive_cached_closure_invalidation():
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("Y1", "=A1+1")
    sheet.set("X1", "=Y1+1")
    assert sheet.get("X1") == 3
    before = sheet.eval_count
    sheet.set("A1", 10)
    assert sheet.get("X1") == 12
    assert sheet.eval_count - before >= 1


def test_range_with_formula_members():
    """Closure should include formula cells in ranges."""
    sheet = Sheet()
    sheet.set("A1", 1)
    sheet.set("B1", "=2")
    sheet.set("C1", 3)
    sheet.set("X1", "=SUM(A1:C1)")
    sheet.get("X1")
    before = sheet.eval_count
    sheet.set("B1", "=20")
    result = sheet.get("X1")
    assert result == 24
    assert sheet.eval_count - before >= 1
