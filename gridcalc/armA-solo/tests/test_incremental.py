"""Phase 4 Task 4.2: Dependency graph + dirty propagation (R10, R11)."""
import pytest
from gridcalc import Sheet


# ── irrelevant edit: set outside closure → get adds 0 ────────────────

def test_irrelevant_edit_adds_zero():
    """set(Y) with Y outside X's closure, then get(X) adds 0."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    # A1 is in B1's closure. Now set C1 (outside closure).
    s.set("C1", 99)
    before = s.eval_count
    s.get("B1")
    assert s.eval_count == before  # no change
    assert s.get("B1") == 2


def test_irrelevant_edit_formula_outside_closure():
    s = Sheet()
    s.set("A1", "=10")
    s.set("B1", "=A1+1")
    s.get("B1")
    s.set("C1", "=100")  # C1 not in B1's closure
    before = s.eval_count
    s.get("B1")
    assert s.eval_count == before


# ── relevant edit: set inside closure → get adds ≥1 ─────────────────

def test_relevant_edit_adds_at_least_one():
    """set(Y) with Y inside X's closure, then get(X) adds ≥1."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    s.set("A1", 10)  # A1 is in B1's closure
    before = s.eval_count
    result = s.get("B1")
    delta = s.eval_count - before
    assert delta >= 1
    assert result == 11


def test_relevant_edit_set_self():
    """set(X) then get(X) adds ≥1."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    s.set("B1", "=A1+10")  # set X itself
    before = s.eval_count
    result = s.get("B1")
    delta = s.eval_count - before
    assert delta >= 1
    assert result == 11


# ── at most closure size ────────────────────────────────────────────

def test_at_most_closure_size():
    """get(X) after relevant edit adds at most number of formula cells in closure."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.set("C1", "=B1+1")
    s.get("C1")
    # Closure of C1: C1, B1, A1 (but A1 is literal, so 2 formula cells)
    s.set("A1", 100)
    before = s.eval_count
    s.get("C1")
    delta = s.eval_count - before
    # At most 2 (C1 and B1 are formula cells in closure)
    assert delta <= 2


# ── closure semantics ────────────────────────────────────────────────

def test_range_members_in_closure():
    """Range members count in closure."""
    s = Sheet()
    s.set("A1", 1)
    s.set("A2", 2)
    s.set("B1", "=SUM(A1:A2)")
    s.get("B1")
    # Set A1 (in closure via range)
    s.set("A1", 10)
    before = s.eval_count
    s.get("B1")
    delta = s.eval_count - before
    assert delta >= 1


def test_invalid_range_no_members_in_closure():
    """Invalid range contributes no members to closure."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=SUM(A0:A1)")  # A0 is invalid → #REF!, no deps
    s.get("B1")
    # B1's closure is just itself (invalid range contributes no members)
    # Set A1 (outside closure)
    s.set("A1", 100)
    before = s.eval_count
    s.get("B1")
    assert s.eval_count == before  # no change


def test_parse_error_closure_is_self():
    """#PARSE! formula's closure is just itself."""
    s = Sheet()
    s.set("A1", "=1 +")
    s.get("A1")
    # A1's closure is just itself
    s.set("B1", 99)  # outside closure
    before = s.eval_count
    s.get("A1")
    assert s.eval_count == before


def test_literal_edit_get_adds_zero():
    """Edit that leaves X literal/empty: get adds 0."""
    s = Sheet()
    s.set("A1", "=1+2")
    s.get("A1")
    s.set("A1", 42)  # X is now literal
    before = s.eval_count
    s.get("A1")
    assert s.eval_count == before  # literal read, no count


# ── identical content still counts as edit ───────────────────────────

def test_identical_content_still_counts():
    """set writing identical content still counts as an edit."""
    s = Sheet()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.get("B1")
    s.set("A1", 1)  # same value
    before = s.eval_count
    s.get("B1")
    delta = s.eval_count - before
    assert delta >= 1


# ── R11: values match naive full recompute ───────────────────────────

def test_values_match_naive_recompute():
    """Values are identical to naive full recompute."""
    s = Sheet()
    s.set("A1", 5)
    s.set("B1", "=A1+10")
    s.set("C1", "=B1*2")
    assert s.get("C1") == 30
    s.set("A1", 100)
    assert s.get("C1") == 220
