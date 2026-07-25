"""Task 5.3: IF evaluation and static closure (R15, R10).

Covers:
- IF(condition, then_expr, else_expr) evaluates the condition first.
- Error conditions return that error.
- String conditions return #TYPE!.
- Integer conditions select the then branch when nonzero and the else
  branch when zero, returning the selected branch value of any type.
- The unselected branch is not evaluated even if it contains errors or
  formula cells, with eval_count evidence.
- R10 closure for an IF formula statically includes references in the
  condition and both branches for invalidation purposes.
- Extends the naive reference model from Task 4.2 to cover string
  literals, string type rules, CONCAT, LEN, and IF, with directed
  equivalence tests for the new semantics.
"""
import pytest

from gridcalc.formula import (
    PARSE_ERROR, DIV_ERROR, TYPE_ERROR, REF_ERROR,
    parse_formula,
)
from gridcalc.workbook import Workbook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wb_with(cells):
    """Create a workbook with one sheet and set the given cells."""
    wb = Workbook()
    sh = wb.add_sheet("S1")
    for addr, value in cells.items():
        sh.set(addr, value)
    return wb, sh


# ---------------------------------------------------------------------------
# 1. Basic IF behavior (criterion 1, 2)
# ---------------------------------------------------------------------------

class TestIfBasic:
    def test_if_nonzero_condition_selects_then(self):
        """IF(1, 10, 20) returns 10 (nonzero condition selects then)."""
        assert parse_formula('IF(1,10,20)') == 10

    def test_if_zero_condition_selects_else(self):
        """IF(0, 10, 20) returns 20 (zero condition selects else)."""
        assert parse_formula('IF(0,10,20)') == 20

    def test_if_negative_nonzero_selects_then(self):
        """IF(-1, 10, 20) returns 10 (negative nonzero selects then)."""
        assert parse_formula('IF(-1,10,20)') == 10

    def test_if_then_returns_string(self):
        """IF(1, "a", "b") returns "a" (then branch can return string)."""
        assert parse_formula('IF(1,"a","b")') == "a"

    def test_if_else_returns_string(self):
        """IF(0, "a", "b") returns "b" (else branch can return string)."""
        assert parse_formula('IF(0,"a","b")') == "b"

    def test_if_then_returns_error(self):
        """IF(1, 1/0, 20) returns #DIV! (then branch can return error)."""
        assert parse_formula('IF(1,1/0,20)') == DIV_ERROR

    def test_if_else_returns_error(self):
        """IF(0, 10, 1/0) returns #DIV! (else branch can return error)."""
        assert parse_formula('IF(0,10,1/0)') == DIV_ERROR

    def test_if_with_expression_condition(self):
        """IF(1+1, 10, 20) returns 10 (expression condition)."""
        assert parse_formula('IF(1+1,10,20)') == 10

    def test_if_with_expression_then(self):
        """IF(1, 2+3, 20) returns 5 (expression then branch)."""
        assert parse_formula('IF(1,2+3,20)') == 5

    def test_if_with_expression_else(self):
        """IF(0, 10, 2*3) returns 6 (expression else branch)."""
        assert parse_formula('IF(0,10,2*3)') == 6

    def test_if_with_ref_condition(self):
        """IF(A1, 10, 20) with A1=5 returns 10."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=IF(A1,10,20)")
        assert sh.get("C1") == 10

    def test_if_with_ref_condition_zero(self):
        """IF(A1, 10, 20) with A1=0 returns 20."""
        wb, sh = _wb_with({"A1": 0})
        sh.set("C1", "=IF(A1,10,20)")
        assert sh.get("C1") == 20

    def test_if_with_ref_then(self):
        """IF(1, A1, 20) with A1=42 returns 42."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=IF(1,A1,20)")
        assert sh.get("C1") == 42

    def test_if_with_ref_else(self):
        """IF(0, 10, A1) with A1=42 returns 42."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=IF(0,10,A1)")
        assert sh.get("C1") == 42


# ---------------------------------------------------------------------------
# 2. String condition (criterion 3)
# ---------------------------------------------------------------------------

class TestIfStringCondition:
    def test_if_string_literal_condition(self):
        """IF("x", 10, 20) returns #TYPE! (string condition)."""
        assert parse_formula('IF("x",10,20)') == TYPE_ERROR

    def test_if_string_ref_condition(self):
        """IF(A1, 10, 20) with A1="x" returns #TYPE! (string ref condition)."""
        wb, sh = _wb_with({"A1": "x"})
        sh.set("C1", "=IF(A1,10,20)")
        assert sh.get("C1") == TYPE_ERROR

    def test_if_string_condition_then_not_evaluated(self):
        """IF("x", 1/0, 20) returns #TYPE! (then branch not evaluated)."""
        assert parse_formula('IF("x",1/0,20)') == TYPE_ERROR

    def test_if_string_condition_else_not_evaluated(self):
        """IF("x", 10, 1/0) returns #TYPE! (else branch not evaluated)."""
        assert parse_formula('IF("x",10,1/0)') == TYPE_ERROR


# ---------------------------------------------------------------------------
# 3. Error condition (criterion 4)
# ---------------------------------------------------------------------------

class TestIfErrorCondition:
    def test_if_div_error_condition(self):
        """IF(1/0, 10, 20) returns #DIV! (error condition)."""
        assert parse_formula('IF(1/0,10,20)') == DIV_ERROR

    def test_if_type_error_condition(self):
        """IF("x"+1, 10, 20) returns #TYPE! (error condition)."""
        assert parse_formula('IF("x"+1,10,20)') == TYPE_ERROR

    def test_if_error_condition_then_not_evaluated(self):
        """IF(1/0, 10, 20) returns #DIV! (then branch not evaluated)."""
        assert parse_formula('IF(1/0,10,20)') == DIV_ERROR

    def test_if_error_condition_else_not_evaluated(self):
        """IF(1/0, 10, 20) returns #DIV! (else branch not evaluated)."""
        assert parse_formula('IF(1/0,10,20)') == DIV_ERROR

    def test_if_ref_error_condition(self):
        """IF(A1, 10, 20) with A1=#DIV! returns #DIV! (error ref condition)."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(A1,10,20)")
        assert sh.get("C1") == DIV_ERROR


# ---------------------------------------------------------------------------
# 4. Short-circuit with eval_count evidence (criterion 5)
# ---------------------------------------------------------------------------

class TestIfShortCircuit:
    def test_if_nonzero_condition_else_not_evaluated(self):
        """IF(1, 10, A1) with A1=#DIV!: else branch not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            return ("int", 0)

        result = parse_formula('IF(1,10,A1)', resolve_ref=resolve_ref)
        assert result == 10
        assert "A1" not in eval_log

    def test_if_zero_condition_then_not_evaluated(self):
        """IF(0, A1, 20) with A1=#DIV!: then branch not evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            return ("int", 0)

        result = parse_formula('IF(0,A1,20)', resolve_ref=resolve_ref)
        assert result == 20
        assert "A1" not in eval_log

    def test_if_error_condition_branches_not_evaluated(self):
        """IF(1/0, A1, B1): neither branch evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("int", 10)
            if addr == "B1":
                return ("int", 20)
            return ("int", 0)

        result = parse_formula('IF(1/0,A1,B1)', resolve_ref=resolve_ref)
        assert result == DIV_ERROR
        assert "A1" not in eval_log
        assert "B1" not in eval_log

    def test_if_string_condition_branches_not_evaluated(self):
        """IF("x", A1, B1): neither branch evaluated."""
        eval_log = []

        def resolve_ref(addr):
            eval_log.append(addr)
            if addr == "A1":
                return ("int", 10)
            if addr == "B1":
                return ("int", 20)
            return ("int", 0)

        result = parse_formula('IF("x",A1,B1)', resolve_ref=resolve_ref)
        assert result == TYPE_ERROR
        assert "A1" not in eval_log
        assert "B1" not in eval_log

    def test_if_with_formula_cell_in_unselected_branch(self):
        """IF(1, 10, A1) with A1=#DIV!: unselected branch formula not evaluated."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(1,10,A1)")
        assert sh.get("C1") == 10

    def test_if_with_formula_cell_in_selected_branch(self):
        """IF(1, A1, 20) with A1=#DIV!: selected branch formula evaluated."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(1,A1,20)")
        assert sh.get("C1") == DIV_ERROR

    def test_if_eval_count_with_error_condition(self):
        """IF(A1, 10, 20) with A1=#DIV!: C1 and A1 evaluated, branches skipped."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(A1,10,20)")
        assert sh.get("C1") == DIV_ERROR
        # C1 and A1 were evaluated (condition resolved A1 which is a formula cell).
        assert sh.eval_count == 2

    def test_if_eval_count_with_literal_error_condition(self):
        """IF(1/0, 10, 20): only C1 evaluated (literal error, no ref)."""
        wb, sh = _wb_with({})
        sh.set("C1", "=IF(1/0,10,20)")
        assert sh.get("C1") == DIV_ERROR
        # Only C1 was evaluated (literal error condition, no formula cell refs).
        assert sh.eval_count == 1

    def test_if_eval_count_with_nonzero_condition(self):
        """IF(1, 10, A1) with A1=#DIV!: only condition and then evaluated."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(1,10,A1)")
        assert sh.get("C1") == 10
        # Only C1 was evaluated (A1 in unselected branch not evaluated).
        assert sh.eval_count == 1

    def test_if_eval_count_with_zero_condition(self):
        """IF(0, A1, 20) with A1=#DIV!: only condition and else evaluated."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(0,A1,20)")
        assert sh.get("C1") == 20
        # Only C1 was evaluated (A1 in unselected branch not evaluated).
        assert sh.eval_count == 1


# ---------------------------------------------------------------------------
# 5. Static closure includes both branches (criterion 6)
# ---------------------------------------------------------------------------

class TestIfStaticClosure:
    def test_if_closure_includes_condition_ref(self):
        """IF(A1, 10, 20): closure includes A1 (condition ref)."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=IF(A1,10,20)")
        sh.get("C1")  # Trigger evaluation and closure computation.
        closure = sh._closure_cache.get("C1", set())
        assert "A1" in closure

    def test_if_closure_includes_then_ref(self):
        """IF(1, A1, 20): closure includes A1 (then branch ref)."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=IF(1,A1,20)")
        sh.get("C1")
        closure = sh._closure_cache.get("C1", set())
        assert "A1" in closure

    def test_if_closure_includes_else_ref(self):
        """IF(0, 10, A1): closure includes A1 (else branch ref)."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=IF(0,10,A1)")
        sh.get("C1")
        closure = sh._closure_cache.get("C1", set())
        assert "A1" in closure

    def test_if_closure_includes_both_branch_refs(self):
        """IF(1, A1, B1): closure includes both A1 and B1."""
        wb, sh = _wb_with({"A1": 10, "B1": 20})
        sh.set("C1", "=IF(1,A1,B1)")
        sh.get("C1")
        closure = sh._closure_cache.get("C1", set())
        assert "A1" in closure
        assert "B1" in closure

    def test_if_invalidation_on_condition_edit(self):
        """Edit A1 in condition: C1 invalidated."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=IF(A1,10,20)")
        sh.get("C1")
        sh.set("A1", 0)
        # C1 should be invalidated (cache cleared).
        assert "C1" not in sh._cache

    def test_if_invalidation_on_then_edit(self):
        """Edit A1 in then branch: C1 invalidated."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=IF(1,A1,20)")
        sh.get("C1")
        sh.set("A1", 100)
        assert "C1" not in sh._cache

    def test_if_invalidation_on_else_edit(self):
        """Edit A1 in else branch: C1 invalidated."""
        wb, sh = _wb_with({"A1": 42})
        sh.set("C1", "=IF(0,10,A1)")
        sh.get("C1")
        sh.set("A1", 100)
        assert "C1" not in sh._cache

    def test_if_invalidation_irrelevant_edit(self):
        """Edit B1 not in closure: C1 not invalidated."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=IF(A1,10,20)")
        sh.get("C1")
        sh.set("B1", 99)
        # C1 should still be cached (B1 not in closure).
        assert "C1" in sh._cache

    def test_if_eval_count_on_irrelevant_edit(self):
        """Edit B1 not in closure: eval_count unchanged."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=IF(A1,10,20)")
        sh.get("C1")
        initial_count = sh.eval_count
        sh.get("C1")  # Repeat read with no edit.
        assert sh.eval_count == initial_count
        sh.set("B1", 99)  # Irrelevant edit.
        sh.get("C1")  # Repeat read.
        assert sh.eval_count == initial_count

    def test_if_eval_count_on_relevant_edit(self):
        """Edit A1 in closure: eval_count increases."""
        wb, sh = _wb_with({"A1": 5})
        sh.set("C1", "=IF(A1,10,20)")
        sh.get("C1")
        initial_count = sh.eval_count
        sh.set("A1", 0)  # Relevant edit.
        sh.get("C1")  # Re-evaluate.
        assert sh.eval_count > initial_count


# ---------------------------------------------------------------------------
# 6. IF with CONCAT, LEN, string literals (criterion 7)
# ---------------------------------------------------------------------------

class TestIfWithOtherFunctions:
    def test_if_then_concat(self):
        """IF(1, CONCAT("a","b"), "c") returns "ab"."""
        assert parse_formula('IF(1,CONCAT("a","b"),"c")') == "ab"

    def test_if_else_concat(self):
        """IF(0, "a", CONCAT("x","y")) returns "xy"."""
        assert parse_formula('IF(0,"a",CONCAT("x","y"))') == "xy"

    def test_if_then_len(self):
        """IF(1, LEN("hello"), 0) returns 5."""
        assert parse_formula('IF(1,LEN("hello"),0)') == 5

    def test_if_else_len(self):
        """IF(0, 0, LEN("world")) returns 5."""
        assert parse_formula('IF(0,0,LEN("world"))') == 5

    def test_if_condition_concat(self):
        """IF(CONCAT("a","b"), 10, 20) returns 10 (string result -> #TYPE!)."""
        # CONCAT("a","b") returns "ab" (string), so condition is string -> #TYPE!.
        assert parse_formula('IF(CONCAT("a","b"),10,20)') == TYPE_ERROR

    def test_if_nested_if(self):
        """IF(1, IF(1, 10, 20), 30) returns 10 (nested IF)."""
        assert parse_formula('IF(1,IF(1,10,20),30)') == 10

    def test_if_with_string_literal_in_branch(self):
        """IF(1, "hello", "world") returns "hello"."""
        assert parse_formula('IF(1,"hello","world")') == "hello"

    def test_if_with_string_literal_condition(self):
        """IF("x", 10, 20) returns #TYPE! (string literal condition)."""
        assert parse_formula('IF("x",10,20)') == TYPE_ERROR


# ---------------------------------------------------------------------------
# 7. Reference model differential tests
# ---------------------------------------------------------------------------

class TestDifferential:
    """Compare implementation against independent reference model."""

    def _ref_eval(self, formula_text, resolve_ref=None):
        """Evaluate using the reference model."""
        from tests.reference_model import (
            _ref_tokenize, _ref_parse_expr, _ref_evaluate,
            _RefErrorValue,
        )

        tokens = _ref_tokenize(formula_text)
        if tokens is None:
            return "#PARSE!"

        pos = [0]
        ast_node = _ref_parse_expr(tokens, pos)
        if ast_node is None or pos[0] != len(tokens):
            return "#PARSE!"

        eval_count = [0]
        result = _ref_evaluate(ast_node, resolve_ref, eval_count)

        if isinstance(result, _RefErrorValue):
            return result.code
        return result

    @pytest.mark.parametrize("formula_text", [
        'IF(1,10,20)',
        'IF(0,10,20)',
        'IF(-1,10,20)',
        'IF(1,"a","b")',
        'IF(0,"a","b")',
        'IF(1,1/0,20)',
        'IF(0,10,1/0)',
        'IF(1+1,10,20)',
        'IF(1,2+3,20)',
        'IF(0,10,2*3)',
        'IF("x",10,20)',
        'IF(1/0,10,20)',
        'IF("x"+1,10,20)',
        'IF("x",1/0,20)',
        'IF("x",10,1/0)',
        'IF(1,10,A1)',
        'IF(0,A1,20)',
        'IF(1/0,A1,B1)',
        'IF("x",A1,B1)',
        'IF(1,CONCAT("a","b"),"c")',
        'IF(0,"a",CONCAT("x","y"))',
        'IF(1,LEN("hello"),0)',
        'IF(0,0,LEN("world"))',
        'IF(CONCAT("a","b"),10,20)',
        'IF(1,IF(1,10,20),30)',
        'IF(1,"hello","world")',
        'IF("x",10,20)',
    ])
    def test_differential(self, formula_text):
        """Implementation and reference model agree on all these formulas."""
        impl_result = parse_formula(formula_text)
        ref_result = self._ref_eval(formula_text)
        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )

    @pytest.mark.parametrize("formula_text", [
        'IF(1,10,A1)',
        'IF(0,A1,20)',
        'IF(1/0,A1,B1)',
        'IF("x",A1,B1)',
    ])
    def test_differential_short_circuit(self, formula_text):
        """Short-circuit behavior matches reference model."""
        eval_log_impl = []
        eval_log_ref = []

        def resolve_ref_impl(addr):
            eval_log_impl.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            if addr == "B1":
                return ("int", 20)
            return ("int", 0)

        def resolve_ref_ref(addr):
            eval_log_ref.append(addr)
            if addr == "A1":
                return ("error", "#DIV!")
            if addr == "B1":
                return ("int", 20)
            return ("int", 0)

        impl_result = parse_formula(formula_text, resolve_ref=resolve_ref_impl)
        ref_result = self._ref_eval(formula_text, resolve_ref=resolve_ref_ref)

        assert impl_result == ref_result, (
            f"Mismatch for {formula_text!r}: impl={impl_result!r}, ref={ref_result!r}"
        )
        assert eval_log_impl == eval_log_ref, (
            f"Eval log mismatch for {formula_text!r}: "
            f"impl={eval_log_impl}, ref={eval_log_ref}"
        )


# ---------------------------------------------------------------------------
# 8. Verifier finding 1: error condition with eval_count evidence
# ---------------------------------------------------------------------------

class TestVerifierFinding1:
    def test_if_error_condition_with_different_error_branch(self):
        """IF(1/0, A1, 20) with A1="=1+1": returns #DIV!, eval_count == 1."""
        wb, sh = _wb_with({"A1": "=1+1"})
        sh.set("C1", "=IF(1/0,A1,20)")
        result = sh.get("C1")
        assert result == DIV_ERROR
        # Only C1 was evaluated (condition produced error, branches skipped).
        assert sh.eval_count == 1

    def test_if_error_condition_with_error_in_unselected_branch(self):
        """IF(1/0, 10, A1) with A1="=1/0": returns #DIV!, A1 not evaluated."""
        wb, sh = _wb_with({"A1": "=1/0"})
        sh.set("C1", "=IF(1/0,10,A1)")
        result = sh.get("C1")
        assert result == DIV_ERROR
        # Only C1 was evaluated (A1 in unselected branch not evaluated).
        assert sh.eval_count == 1

    def test_if_string_condition_with_error_in_branches(self):
        """IF("x", A1, B1) with A1="=1/0", B1="=1/0": returns #TYPE!, neither branch evaluated."""
        wb, sh = _wb_with({"A1": "=1/0", "B1": "=1/0"})
        sh.set("C1", '=IF("x",A1,B1)')
        result = sh.get("C1")
        assert result == TYPE_ERROR
        # Only C1 was evaluated (condition is string, branches skipped).
        assert sh.eval_count == 1
