# Loopspace State
version: 1
run_status: complete
harness: opencode
tier: A
mode: lead
budget_dispatches: 60
budget_wall_hours: 10
base_branch: main
run_branch: loopspace/gridcalc-xl/run
current_branch: loopspace/gridcalc-xl/run

## Project Facts
- test: pytest -q
- build/run: none yet
- stack: Python 3.10+ pure-logic library, package `gridcalc`, stdlib-only runtime, pytest-only tests
- security: no file I/O, network, eval, exec, compile, __import__, importlib, or pickle in runtime code
- api: public surface is `from gridcalc import Workbook`; `gridcalc.__all__ == ["Workbook"]`
- gate: sh /Users/arden/code/loopspace/scripts/gate.sh
