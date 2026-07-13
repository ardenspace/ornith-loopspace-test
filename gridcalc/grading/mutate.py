"""Mutation harness: same 6 behavioral mutations per arm, run arm's own suite."""
import subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))

SPECS = {
    "solo": [
        ("M1 div-floor", "gridcalc/evaluator.py", "return int(left / right)", "return left // right", 1),
        ("M2 no-left-shortcircuit", "gridcalc/evaluator.py", "return left  # short-circuit", "left = 0  # mutated", 1),
        ("M3 range-order-off", "gridcalc/evaluator.py", "if tl_col_ord > br_col_ord or tl_row > br_row:", "if False:", 1),
        ("M4 cycle-to-zero", "gridcalc/evaluator.py", "return ERR_CYCLE", "return 0", 1),
        ("M5 strcell-to-zero", "gridcalc/evaluator.py", "return ERR_TYPE", "return 0", 1),
        ("M6 count-off", "gridcalc/sheet.py", "self._eval_count += count_ref[0]", "self._eval_count += 0", 1),
    ],
    "armB": [
        ("M1 div-floor", "gridcalc/evaluator.py", "return int(left / right)", "return left // right", 1),
        ("M2 no-left-shortcircuit", "gridcalc/evaluator.py", "if isinstance(left, str):\n            return left", "if isinstance(left, str):\n            left = 0", 1),
        ("M3 range-order-off", "gridcalc/evaluator.py", "if col1 > col2 or row1 > row2:", "if False:", 1),
        ("M4 cycle-to-zero", "gridcalc/evaluator.py", "return CYCLE_ERROR", "return 0", 1),
        ("M5 strcell-to-zero", "gridcalc/evaluator.py", "return TYPE_ERROR  # String cell yields #TYPE! in numeric context", "return 0", 1),
        ("M6 count-off", "gridcalc/sheet.py", "self._eval_count += 1", "self._eval_count += 0", 1),
    ],
    "rerun": [
        ("M1 div-floor", "gridcalc/evaluator.py", "return int(left / right)", "return left // right", 1),
        ("M2 no-left-shortcircuit", "gridcalc/evaluator.py", "if isinstance(left, str):\n            return left", "if isinstance(left, str):\n            left = 0", 1),
        ("M3 range-order-off", "gridcalc/evaluator.py", "if (start_col, start_row) > (end_col, end_row):", "if False:", 1),
        ("M4 cycle-to-zero", "gridcalc/evaluator.py", "if addr in _evaluating:\n        return ERROR_CYCLE", "if addr in _evaluating:\n        return 0", 1),
        ("M5 strcell-to-zero", "gridcalc/evaluator.py", "            sheet._dirty.discard(addr)\n            return ERROR_TYPE", "            sheet._dirty.discard(addr)\n            return 0", 1),
        ("M6 count-off", "gridcalc/sheet.py", "self._eval_count += 1", "self._eval_count += 0", 2),
    ],
}

for arm, specs in SPECS.items():
    print(f"== {arm}")
    for name, relpath, old, new, cnt in specs:
        path = os.path.join(BASE, arm, relpath)
        src = open(path).read()
        found = src.count(old)
        if found < cnt:
            print(f"  {name}: SITE NOT FOUND ({found} occurrences)")
            continue
        patched = src.replace(old, new, cnt)
        open(path, "w").write(patched)
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-x", "-p", "no:cacheprovider"],
                cwd=os.path.join(BASE, arm), capture_output=True, text=True, timeout=120,
            )
            tail = (r.stdout.strip().splitlines() or ["?"])[-1]
            killed = r.returncode != 0
            print(f"  {name}: {'KILLED' if killed else 'SURVIVED'}  ({tail})")
        finally:
            open(path, "w").write(src)
print("done")
