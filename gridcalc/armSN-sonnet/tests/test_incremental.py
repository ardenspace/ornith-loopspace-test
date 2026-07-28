from gridcalc import Sheet


def test_irrelevant_edit_adds_zero():
    s = Sheet()
    s.set("A1", 1)
    s.set("X1", "=A1+1")
    s.get("X1")
    s.set("Y1", 99)  # Y1 outside X1's closure
    before = s.eval_count
    s.get("X1")
    assert s.eval_count == before


def test_relevant_edit_recomputes_and_adds_at_least_one():
    s = Sheet()
    s.set("A1", 1)
    s.set("X1", "=A1+1")
    assert s.get("X1") == 2
    s.set("A1", 10)
    before = s.eval_count
    assert s.get("X1") == 11
    assert s.eval_count - before >= 1


def test_relevant_edit_bounded_by_closure_size():
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.set("C1", "=B1+1")
    s.set("D1", "=C1+1")  # closure of D1: {D1, C1, B1, A1} -> 3 formula cells
    s.get("D1")
    s.set("A1", 5)
    before = s.eval_count
    s.get("D1")
    assert s.eval_count - before <= 3


def test_formula_outside_closure_never_recomputed():
    s = Sheet()
    s.set("A1", 1)
    s.set("X1", "=A1+1")
    s.set("Z1", "=1+1")
    s.get("Z1")
    s.set("A1", 2)
    s.get("X1")
    before = s.eval_count
    s.get("Z1")
    assert s.eval_count == before  # cached, untouched by A1's edit


def test_range_closure_includes_members_empty_included():
    s = Sheet()
    s.set("A1", 1)
    s.set("Q1", "=SUM(A1:B2)")  # B1, A2, B2 all empty
    assert s.get("Q1") == 1
    s.set("B2", 10)  # B2 is in the closure though it was empty
    before = s.eval_count
    assert s.get("Q1") == 11
    assert s.eval_count - before >= 1


def test_invalid_range_contributes_no_closure_members():
    s = Sheet()
    s.set("Q1", "=SUM(B2:A1)")  # mis-ordered -> #REF!, no deps
    assert s.get("Q1") == "#REF!"
    s.set("A1", 100)
    before = s.eval_count
    assert s.get("Q1") == "#REF!"
    assert s.eval_count == before


def test_parse_error_formula_closure_is_itself():
    s = Sheet()
    s.set("Q1", "=a1")  # #PARSE!, no deps
    assert s.get("Q1") == "#PARSE!"
    s.set("A1", 5)
    before = s.eval_count
    assert s.get("Q1") == "#PARSE!"
    assert s.eval_count == before


def test_edit_leaving_cell_literal_adds_zero():
    s = Sheet()
    s.set("A1", "=1+1")
    s.get("A1")
    s.set("A1", 5)  # now literal
    before = s.eval_count
    assert s.get("A1") == 5
    assert s.eval_count == before


def test_identical_content_set_still_counts_as_edit():
    s = Sheet()
    s.set("A1", 1)
    s.set("X1", "=A1+1")
    s.get("X1")
    s.set("A1", 1)  # identical content, still an edit
    before = s.eval_count
    s.get("X1")
    assert s.eval_count - before >= 1
