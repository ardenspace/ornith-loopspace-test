# Handoff
version: 1
written: 2026-07-11
trigger: phase-boundary

## Where we are
Phase 1 complete. The `kvtx` package implements a `Database` class with base store operations (set/get/delete/count) and nested transactions (begin/rollback/commit). All 27 tests pass.

## Next session must know
- The base store uses a two-dict design: `_kv` for key->value mapping, `_vk` for value->count mapping. Both must stay consistent on set/delete/overwrite.
- Transactions use a stack-based overlay model where each frame stores key->value mappings with a `_DELETED` sentinel for deletions.
- `pyproject.toml` is missing `[build-system]` section — `pip install -e .` fails on PEP 668-managed envs. Acceptance criterion "from kvtx import Database works from the repo root" currently requires `PYTHONPATH=.` or a venv.
- `Store` class is exported from `kvtx/__init__.py` but unused by `Database` and not in acceptance criteria — dead code.

## Watch out for
- None
