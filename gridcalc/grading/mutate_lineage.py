"""Experiment L — mutation matrix for armSN (Sonnet solo).

Two modes:

  python3 mutate_lineage.py discover <arm_dir>
      Print candidate mutation sites in the arm's source. Mutation specs are
      literal strings and every arm writes different code, so the sites must be
      read off the actual tree before step 2 can run.

  python3 mutate_lineage.py run <arm_dir>
      Apply each spec in SPECS, run the arm's own suite, report KILLED/SURVIVED,
      restore the file. Same protocol as mutate.py / mutate2.py.

M7 is the gauge: it already reads SURVIVED on three same-mind suites and KILL
under a different-lineage verifier. See PREREG-tier-vs-lineage.md.
"""
import os
import re
import subprocess
import sys

# Fill after step 1. Each entry: (name, relpath, old, new, count)
# `discover` prints the literals to paste in.
SPECS = [
    # ("M7 lex-range-order", "gridcalc/evaluator.py",
    #  "<component-wise check as Sonnet wrote it>",
    #  "<same check, lexicographic tuple compare>", 1),
    # ("M8 range-error-demote", "gridcalc/evaluator.py",
    #  "<first-error-wins propagation>",
    #  "<demoted to TYPE error>", 1),
]

# Heuristics for the sites the gauge needs.
PATTERNS = [
    ("M7 range-order check", r"(col|column).{0,40}[<>].{0,40}(row|col)"),
    ("M8 error propagation", r"return\s+\w*(ERR|ERROR)\w*|isinstance\(\w+,\s*str\)"),
]


def discover(arm):
    for dirpath, _, names in os.walk(os.path.join(arm, "gridcalc")):
        for name in sorted(n for n in names if n.endswith(".py")):
            path = os.path.join(dirpath, name)
            lines = open(path).read().splitlines()
            for label, pat in PATTERNS:
                for i, line in enumerate(lines, 1):
                    if re.search(pat, line):
                        rel = os.path.relpath(path, arm)
                        print(f"{label:24} {rel}:{i}  {line.strip()}")


def run(arm):
    if not SPECS:
        sys.exit("SPECS is empty — run `discover` and fill it in first.")
    for name, relpath, old, new, cnt in SPECS:
        path = os.path.join(arm, relpath)
        src = open(path).read()
        if src.count(old) < cnt:
            print(f"  {name}: SITE NOT FOUND ({src.count(old)})")
            continue
        open(path, "w").write(src.replace(old, new, cnt))
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "tests", "-q", "--no-header",
                 "-p", "no:cacheprovider"],
                cwd=arm, capture_output=True, text=True, timeout=120,
            )
            tail = (r.stdout.strip().splitlines() or ["?"])[-1]
            print(f"  {name}: {'KILLED' if r.returncode else 'SURVIVED'}  ({tail})")
        finally:
            open(path, "w").write(src)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("discover", "run"):
        sys.exit(__doc__)
    {"discover": discover, "run": run}[sys.argv[1]](os.path.abspath(sys.argv[2]))
    print("done")
