"""Shipped-bug cross-mutations: would each arm's suite catch the bugs the other arms shipped?
M7 = rerun's shipped bug (lexicographic range-order check — mixed mis-order accepted)
M8 = original armB's shipped bug (range-member error demoted to #TYPE!)
"""
import subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))

SPECS = {
    "solo": [
        ("M7 lex-range-order", "gridcalc/evaluator.py",
         "if tl_col_ord > br_col_ord or tl_row > br_row:",
         "if (tl_col_ord, tl_row) > (br_col_ord, br_row):", 1),
        ("M8 range-error-demote", "gridcalc/evaluator.py",
         "        if isinstance(result, str):\n            return result  # first error wins (from formula evaluation)",
         "        if isinstance(result, str):\n            return ERR_TYPE  # mutated demotion", 1),
    ],
    "armB": [
        ("M7 lex-range-order", "gridcalc/evaluator.py",
         "if col1 > col2 or row1 > row2:",
         "if (col1, row1) > (col2, row2):", 1),
        # M8 = armB's own shipped bug: suite green over it by construction (161 passed) -> SURVIVED
    ],
    "rerun": [
        # M7 = rerun's own shipped bug: suite green over it by construction (174 passed) -> SURVIVED
        ("M8 range-error-demote", "gridcalc/evaluator.py",
         "                result = _eval_reference(addr, sheet, _evaluating)\n                if isinstance(result, str):\n                    # Short-circuit: return first error immediately\n                    return result",
         "                result = _eval_reference(addr, sheet, _evaluating)\n                if isinstance(result, str):\n                    # Short-circuit: return first error immediately\n                    return ERROR_TYPE", 1),
    ],
}

for arm, specs in SPECS.items():
    print(f"== {arm}")
    for name, relpath, old, new, cnt in specs:
        path = os.path.join(BASE, arm, relpath)
        src = open(path).read()
        if src.count(old) < cnt:
            print(f"  {name}: SITE NOT FOUND ({src.count(old)})")
            continue
        open(path, "w").write(src.replace(old, new, cnt))
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-p", "no:cacheprovider"],
                cwd=os.path.join(BASE, arm), capture_output=True, text=True, timeout=120,
            )
            tail = (r.stdout.strip().splitlines() or ["?"])[-1]
            print(f"  {name}: {'KILLED' if r.returncode else 'SURVIVED'}  ({tail})")
        finally:
            open(path, "w").write(src)
print("done")
