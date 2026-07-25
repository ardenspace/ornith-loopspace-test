# Task 5.3 Report: IF evaluation and static closure

## Summary
IF evaluation (R15) and static closure for IF (R10) were already implemented in `gridcalc/formula.py` and `gridcalc/workbook.py` by prior tasks. This task produced TDD evidence by temporarily disabling the IF evaluation path, capturing the red output, and restoring it. All 85 tests in `tests/test_if_function.py` pass.

## TDD Evidence

**Test file:** `tests/test_if_function.py`

**Failed-first failure log (IF evaluation temporarily disabled at `gridcalc/formula.py:747-748`):**

```
=========================== short test summary info ============================
FAILED tests/test_if_function.py::TestIfBasic::test_if_nonzero_condition_selects_then
FAILED tests/test_if_function.py::TestIfBasic::test_if_zero_condition_selects_else
FAILED tests/test_if_function.py::TestIfBasic::test_if_negative_nonzero_selects_then
FAILED tests/test_if_function.py::TestIfBasic::test_if_then_returns_string
FAILED tests/test_if_function.py::TestIfBasic::test_if_else_returns_string
FAILED tests/test_if_function.py::TestIfBasic::test_if_then_returns_error
FAILED tests/test_if_function.py::TestIfBasic::test_if_else_returns_error
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_expression_condition
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_expression_then
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_expression_else
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_ref_condition
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_ref_condition_zero
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_ref_then
FAILED tests/test_if_function.py::TestIfBasic::test_if_with_ref_else
FAILED tests/test_if_function.py::TestIfStringCondition::test_if_string_literal_condition
FAILED tests/test_if_function.py::TestIfStringCondition::test_if_string_ref_condition
FAILED tests/test_if_function.py::TestIfStringCondition::test_if_string_condition_then_not_evaluated
FAILED tests/test_if_function.py::TestIfStringCondition::test_if_string_condition_else_not_evaluated
FAILED tests/test_if_function.py::TestIfErrorCondition::test_if_div_error_condition
FAILED tests/test_if_function.py::TestIfErrorCondition::test_if_type_error_condition
FAILED tests/test_if_function.py::TestIfErrorCondition::test_if_error_condition_then_not_evaluated
FAILED tests/test_if_function.py::TestIfErrorCondition::test_if_error_condition_else_not_evaluated
FAILED tests/test_if_function.py::TestIfErrorCondition::test_if_ref_error_condition
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_nonzero_condition_else_not_evaluated
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_zero_condition_then_not_evaluated
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_error_condition_branches_not_evaluated
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_string_condition_branches_not_evaluated
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_with_formula_cell_in_unselected_branch
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_with_formula_cell_in_selected_branch
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_eval_count_with_error_condition
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_eval_count_with_literal_error_condition
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_eval_count_with_nonzero_condition
FAILED tests/test_if_function.py::TestIfShortCircuit::test_if_eval_count_with_zero_condition
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_then_concat
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_else_concat
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_then_len
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_else_len
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_condition_concat
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_nested_if
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_with_string_literal_in_branch
FAILED tests/test_if_function.py::TestIfWithOtherFunctions::test_if_with_string_literal_condition
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(-1,10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,"a","b")]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,"a","b")]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,1/0,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,10,1/0)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1+1,10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,2+3,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,10,2*3)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF("x",10,20)0]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1/0,10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF("x"+1,10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF("x",1/0,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF("x",10,1/0)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,10,A1)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,A1,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1/0,A1,B1)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF("x",A1,B1)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,CONCAT("a","b"),"c")]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,"a",CONCAT("x","y"))]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,LEN("hello"),0)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(0,0,LEN("world"))]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(CONCAT("a","b"),10,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,IF(1,10,20),30)]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF(1,"hello","world")]
FAILED tests/test_if_function.py::TestDifferential::test_differential[IF("x",10,20)1]
FAILED tests/test_if_function.py::TestDifferential::test_differential_short_circuit[IF(1,10,A1)]
FAILED tests/test_if_function.py::TestDifferential::test_differential_short_circuit[IF(0,A1,20)]
FAILED tests/test_if_function.py::TestDifferential::test_differential_short_circuit[IF(1/0,A1,B1)]
FAILED tests/test_if_function.py::TestDifferential::test_differential_short_circuit[IF("x",A1,B1)]
FAILED tests/test_if_function.py::TestVerifierFinding1::test_if_error_condition_with_different_error_branch
FAILED tests/test_if_function.py::TestVerifierFinding1::test_if_error_condition_with_error_in_unselected_branch
FAILED tests/test_if_function.py::TestVerifierFinding1::test_if_string_condition_with_error_in_branches
75 failed, 10 passed in 0.25s
```

**Restored:** Reverted `gridcalc/formula.py:747-748` to call `_evaluate_if`. All 85 tests pass. Full suite: 1728 passed.

## Pre-existing

The IF evaluation behavior was already implemented in this tree before this task ran:
- `gridcalc/formula.py:999-1035` — `_evaluate_if()` implements R15 short-circuit evaluation (condition first, error→error, string→#TYPE!, integer nonzero→then, zero→else, unselected branch never evaluated).
- `gridcalc/formula.py:442-484` — `_parse_if_call()` parses `IF(cond, then, else)` into `('IF', cond, then, else)` AST nodes.
- `gridcalc/workbook.py:428-434` — `_compute_closure()` walks all three IF branches for static closure per R10.

The red output above came from the temporary-removal route: commenting out the `if kind == 'IF': return _evaluate_if(...)` dispatch at `gridcalc/formula.py:747-748` (replaced with `return _PARSE_ERR`), running `pytest -q tests/test_if_function.py` to capture 75 failures, then restoring the original line.
