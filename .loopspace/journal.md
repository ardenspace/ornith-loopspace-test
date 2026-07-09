# Journal
version: 1

## [harness] switched claude-code → opencode (tier A → A)

## [1.1] attempt 1 — FAIL
- implementer: Implemented parse_timestamp and format_timestamp with full validation per R1-R3 and acceptance criteria.
- approach: Split on ":" then on ","/".", validate digit counts and ranges before arithmetic; format via divmod chain with f-string zero-padding.
- verifier: FAIL — `pytest -q` fails with `ModuleNotFoundError: No module named 'subcut'` — the project has no pyproject.toml, conftest.py, or setup.py to make the `subcut` package importable from the test root. Tests pass only with `PYTHONPATH=. pytest -q`.
- findings:
  1. Add a `pyproject.toml` with `[tool.pytest.ini_options]` (or a `conftest.py` that appends the project root to `sys.path`) so `pytest -q` can resolve `subcut` without `PYTHONPATH`.

## [1.1] attempt 2 — PASS
- implementer: Added `tests/conftest.py` to prepend project root to `sys.path` so `from subcut.timecode import ...` resolves under `pytest -q`.
- approach: Added `tests/conftest.py` to prepend project root to `sys.path` so `from subcut.timecode import ...` resolves under `pytest -q`.
- tdd-evidence: N/A — code and tests pre-existed; `pytest -q` confirmed all 20 pass.
- verifier: PASS — All 20 tests pass; implementation and tests cover every acceptance criterion.
- files: tests/conftest.py

## [1.2] attempt 1 — PASS
- implementer: Implemented Cue dataclass and pure shift_cues with independent start/end clamping; 9 tests cover all acceptance criteria.
- approach: dataclass for Cue, list comprehension with max(0, t+delta) for independent clamping, new list via comprehension preserves input immutability.
- tdd-evidence: `ModuleNotFoundError: No module named 'subcut.cue'` (import failure before any source existed)
- verifier: PASS — All 9 tests pass. Every acceptance criterion is covered by at least one test that would fail if violated.
- files: subcut/cue.py, subcut/shift.py, subcut/__init__.py, tests/test_shift.py
