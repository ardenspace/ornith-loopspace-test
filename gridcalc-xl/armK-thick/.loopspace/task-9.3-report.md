# Task 9.3 Evidence

- task tests: `pytest -q tests/test_persistence_security.py`
- full suite: `pytest -q`

## Failed-First Evidence

Temporary change applied to `gridcalc/workbook.py` inside `Workbook.from_json`:

```python
s = str(s)
```

This reintroduced input-controlled `__str__` execution for `str` subclasses. Running the Task 9.3 tests produced:

```text
_____________ test_from_json_does_not_call_str_subclass_str_method _____________
E       AssertionError: from_json executed input-controlled __str__
FAILED tests/test_persistence_security.py::test_from_json_does_not_call_str_subclass_str_method
1 failed, 56 passed in 0.04s
```

The temporary line was then removed exactly.

## Green Evidence

```text
$ pytest -q tests/test_persistence_security.py
57 passed in 0.03s

$ pytest -q
3103 passed in 10.00s
```
