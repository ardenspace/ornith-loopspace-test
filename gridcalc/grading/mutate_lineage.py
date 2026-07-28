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
    # M7 — armSN wrote the order check component-wise (evaluator.py:98), the same
    # shape every earlier arm produced. Mutate to ROW-MAJOR lexicographic: the one
    # variant whose only discriminating case is B1:A2.
    #   B2:A1 (every arm tests this)  correct=invalid  mutant=invalid  -> no kill
    #   B1:A2 (no arm tests this)     correct=invalid  mutant=VALID    -> kills
    # Column-major lexicographic `(tc,tr) > (bc,br_)` would be the wrong gauge:
    # it also calls B1:A2 invalid, so it cannot detect the missing test at all.
    ("M7 lex-range-order", "gridcalc/evaluator.py",
     "    if tc > bc or tr > br_:\n        return None\n",
     "    if (tr, tc) > (br_, bc):\n        return None\n", 1),
    # M8 — first-error-wins propagation out of a range (sheet.py:141) demoted to a
    # flat #TYPE!. NOTE: armSN routes SUM/MIN/MAX through one shared
    # `_range_values`, so this mutates all three; earlier arms' M8 hit the SUM path
    # only. Broader than the historical M8 — a KILL here is therefore weaker
    # evidence than a KILL there, and is not the experiment's gate.
    ("M8 range-error-demote", "gridcalc/sheet.py",
     "            if isinstance(v, str):\n                return v\n",
     "            if isinstance(v, str):\n                return \"#TYPE!\"\n", 1),
    # M15 — THE GAUGE, after M7 was KILLED (see EXPERIMENT.md UPDATE L-1).
    # Drops the stale reverse-dependency edges when a formula is rewritten to
    # depend on fewer cells. Values stay correct; only eval_count inflates, so
    # the 1000-seed differential is structurally blind to it. Violates R10's
    # normative "irrelevant edit adds 0" bound:
    #   A1=1; B1="=A1"; get(B1); B1="=5"; get(B1); set(A1,2); get(B1)
    #   -> original delta 0, mutant delta 1.
    ("M15 rdeps-never-cleaned", "gridcalc/sheet.py",
     "        for d in old_deps:\n            bucket = self._rdeps.get(d)\n"
     "            if bucket is not None:\n                bucket.discard(addr)\n",
     "        pass\n", 1),
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


def _pytest(arm):
    """Run the arm's suite with the stale-bytecode guard (EXPERIMENT.md L-1 ⑥).

    A size-preserving mutation is invisible to CPython's (mtime_seconds, size)
    pyc invalidation when apply+restore land in the same second, so a restored
    tree can keep executing MUTATED bytecode and poison every later mutation.
    Never write bytecode, and drop any cache dir before running.
    """
    for dirpath, names, _ in os.walk(arm):
        for d in [n for n in names if n == "__pycache__"]:
            subprocess.run(["rm", "-rf", os.path.join(dirpath, d)])
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=arm, capture_output=True, text=True, timeout=120,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )


def run(arm):
    if not SPECS:
        sys.exit("SPECS is empty — run `discover` and fill it in first.")
    base = _pytest(arm)
    if base.returncode:
        sys.exit(f"baseline not green before mutating:\n{base.stdout[-800:]}")
    print(f"  baseline: {base.stdout.strip().splitlines()[-1]}")
    for name, relpath, old, new, cnt in SPECS:
        path = os.path.join(arm, relpath)
        src = open(path).read()
        if src.count(old) < cnt:
            print(f"  {name}: SITE NOT FOUND ({src.count(old)})")
            continue
        open(path, "w").write(src.replace(old, new, cnt))
        try:
            r = _pytest(arm)
            tail = (r.stdout.strip().splitlines() or ["?"])[-1]
            print(f"  {name}: {'KILLED' if r.returncode else 'SURVIVED'}  ({tail})")
        finally:
            open(path, "w").write(src)
        chk = _pytest(arm)
        if chk.returncode:
            sys.exit(f"ABORT — tree not green after restoring {name} "
                     f"(contamination):\n{chk.stdout[-800:]}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("discover", "run"):
        sys.exit(__doc__)
    {"discover": discover, "run": run}[sys.argv[1]](os.path.abspath(sys.argv[2]))
    print("done")
