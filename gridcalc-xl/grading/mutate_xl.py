"""Mutation harness for Experiment W' (gridcalc-xl) — same pattern as
gridcalc/grading/mutate.py and mutate2.py.

Pre-registered part (this file, committed before any run): the driver
and the workflow. The SPECS tables are *necessarily* filled in after
the runs — mutation sites are arm-source-specific — following the two
pre-registered protocols:

1. Behavioral mutations (mutate.py pattern): the same N semantic
   mutations applied to each arm's own source, each arm's own pytest
   suite run — KILLED/SURVIVED measures suite strength. Candidate
   mutation classes for XL (pick sites present in every arm):
   div-floor, no-left-shortcircuit, cycle-to-zero, strcell-to-zero,
   count-off, typed-read-to-numeric (R13), copy-anchor-ignored (R17),
   name-resolution-global (R18), redo-not-cleared (R19),
   volatile-never-dirty (R27), journal-persisted (R24).
2. Cross-mutations (mutate2.py pattern): each arm's *shipped* bugs
   (found by the held-out oracle) re-expressed as mutations in the
   other arms' sources — would their suites have caught it?

Each SPECS entry: (name, relpath, old_text, new_text, occurrence_count).
The driver refuses to run when a site is not found, restores sources
afterwards, and never commits mutated trees.

Usage (after filling SPECS):
    python3 mutate_xl.py
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
# Arm run repos live under gridcalc-xl/runs/<arm>/ (2026-07-15 location
# convention); post-run snapshots may be graded in place.
ARM_DIRS = {
    "solo": os.path.join(BASE, "..", "runs", "solo"),
    "thin": os.path.join(BASE, "..", "runs", "thin"),
    "thick": os.path.join(BASE, "..", "runs", "thick"),
}

SPECS = {
    # Filled in after the runs (arm-source-specific sites). Shape:
    # "solo": [
    #     ("M1 div-floor", "gridcalc/evaluator.py",
    #      "<exact old text>", "<mutated text>", 1),
    # ],
}


def main():
    if not SPECS:
        sys.exit("SPECS is empty — fill in per-arm mutation sites first "
                 "(see module docstring).")
    for arm, specs in SPECS.items():
        print(f"== {arm}")
        arm_dir = ARM_DIRS[arm]
        for name, relpath, old, new, cnt in specs:
            path = os.path.join(arm_dir, relpath)
            with open(path) as fh:
                src = fh.read()
            found = src.count(old)
            if found < cnt:
                print(f"  {name}: SITE NOT FOUND ({found} occurrences)")
                continue
            with open(path, "w") as fh:
                fh.write(src.replace(old, new, cnt))
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "pytest", "tests", "-q",
                     "--no-header", "-p", "no:cacheprovider"],
                    cwd=arm_dir, capture_output=True, text=True,
                    timeout=600,
                )
                tail = (r.stdout.strip().splitlines() or ["?"])[-1]
                killed = r.returncode != 0
                print(f"  {name}: {'KILLED' if killed else 'SURVIVED'}"
                      f"  ({tail})")
            finally:
                with open(path, "w") as fh:
                    fh.write(src)
    print("done")


if __name__ == "__main__":
    main()
