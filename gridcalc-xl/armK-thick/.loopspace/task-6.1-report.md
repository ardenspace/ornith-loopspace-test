# Task 6.1 Report: Mutation journal foundation

- verdict: DONE
- summary: Implemented mutation journal for set/add_sheet with undo/redo, fixed formula cache invalidation bug in _revert_entry/_apply_entry, added 40 tests covering all R19 acceptance criteria
- approach: TDD — wrote failing-first tests for formula cache invalidation and failed-call non-journaling, then added _invalidate_dependents helper to _SheetHandle and called it from _revert_entry/_apply_entry for set operations
- tdd-evidence: tests/test_mutation_journal.py failed-first: "2 failed, 38 passed in 0.06s" (TestFormulaCacheInvalidation::test_undo_set_invalidates_formula_cache and test_redo_set_invalidates_formula_cache failed because _revert_entry wrote to _cells without invalidating formula caches)
- pre-existing: set journaling (workbook.py:167-172), add_sheet journaling (workbook.py:537-540), undo/redo (workbook.py:572-588), _revert_entry/_apply_entry (workbook.py:590-624) were already implemented in a prior phase. The formula cache invalidation bug (finding #1) was real and fixed by adding _invalidate_dependents helper.
- files: gridcalc/workbook.py, tests/test_mutation_journal.py
- exports: _SheetHandle._invalidate_dependents (private helper for cache invalidation on cell change)
- facts: none
- contested: none
- blocker: none
