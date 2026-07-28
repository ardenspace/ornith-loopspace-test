"""Experiment L — broad mutation sweep over armSN, to relocate the gauge.

M7 was KILLED (failure mode 1), so the gauge must move to a mutation armSN's
own suite actually misses. This sweeps a wide candidate set and reports
KILLED/SURVIVED per mutation. Same protocol as mutate_lineage.py: apply, run
the arm's suite, restore in `finally`.

Axis column: what the 1000-seed differential can observe.
  VALUE   — changes a cell value; the differential should see it
  BLIND   — value-identical, only eval_count / invalidation / error-choice
            ordering changes; the differential is structurally blind to it
"""
import os
import subprocess
import sys

ARM = "/Users/arden/code/gridcalc-sonnet"

E = "gridcalc/evaluator.py"
S = "gridcalc/sheet.py"

# (name, axis, relpath, old, new)
SPECS = [
    # ---- VALUE axis: differential should catch these ----
    ("M01 div-python-floor", "VALUE", E,
     '        q = abs(l) // abs(r)\n        return -q if (l < 0) != (r < 0) else q\n',
     '        return l // r\n'),
    ("M02 div-zero-yields-0", "VALUE", E,
     '        if r == 0:\n            return "#DIV!"\n',
     '        if r == 0:\n            return 0\n'),
    ("M03 lte-becomes-lt", "VALUE", E,
     '    if op == "<=":\n        return 1 if l <= r else 0\n',
     '    if op == "<=":\n        return 1 if l < r else 0\n'),
    ("M04 neg-parity-dropped", "VALUE", E,
     '        return -v if count % 2 else v\n',
     '        return -v\n'),
    ("M05 addr-regex-widened", "VALUE", E,
     'ADDR_RE = re.compile(r"^[A-Z]([1-9][0-9]?)$")',
     'ADDR_RE = re.compile(r"^[A-Z]([0-9]+)$")'),
    ("M10 missing-cell-is-REF", "VALUE", S,
     '        cell = self._cells.get(addr)\n        if cell is None:\n            return 0\n',
     '        cell = self._cells.get(addr)\n        if cell is None:\n            return "#REF!"\n'),
    ("M12 COUNT-counts-empty", "VALUE", S,
     '            return sum(1 for a in addrs if a in self._cells)\n',
     '            return len(addrs)\n'),
    ("M13 MIN-empty-yields-0", "VALUE", S,
     '            return min(values) if values else "#TYPE!"\n',
     '            return min(values) if values else 0\n'),
    ("M17 invalidate-self-only", "VALUE", S,
     '            for dependent in self._rdeps.get(cur, ()):\n'
     '                if dependent not in seen:\n'
     '                    stack.append(dependent)\n',
     '            continue\n'),
    ("M08 range-deps-dropped", "VALUE", E,
     '        if addrs:\n            deps.update(addrs)\n',
     '        if False:\n            deps.update(addrs)\n'),

    # ---- BLIND axis: value-identical, differential cannot observe ----
    ("M09 range-order-col-major", "BLIND", E,
     '    return [make_addr(c, r) for r in range(tr, br_ + 1) for c in range(tc, bc + 1)]\n',
     '    return [make_addr(c, r) for c in range(tc, bc + 1) for r in range(tr, br_ + 1)]\n'),
    ("M06 bin-error-right-wins", "BLIND", E,
     '        lv = evaluate(left, ctx)\n        if _is_error(lv):\n            return lv\n'
     '        rv = evaluate(right, ctx)\n        if _is_error(rv):\n            return rv\n',
     '        lv = evaluate(left, ctx)\n        rv = evaluate(right, ctx)\n'
     '        if _is_error(rv):\n            return rv\n        if _is_error(lv):\n            return lv\n'),
    ("M14 eval-count-frozen", "BLIND", S,
     '        self._eval_count += 1\n', ''),
    ("M15 rdeps-never-cleaned", "BLIND", S,
     '        for d in old_deps:\n            bucket = self._rdeps.get(d)\n'
     '            if bucket is not None:\n                bucket.discard(addr)\n',
     '        pass\n'),
    ("M16 cache-never-stored", "BLIND", S,
     '        self._cache[addr] = value\n        return value\n',
     '        return value\n'),
    ("M18 redundant-cache-pop", "BLIND", S,
     '        self._cells[addr] = content\n        self._cache.pop(addr, None)\n',
     '        self._cells[addr] = content\n'),
]


# Stale-bytecode guard. A mutation that preserves source SIZE (M09 swaps two
# for-clauses of equal length) is invisible to CPython's (mtime_seconds, size)
# pyc invalidation when apply+restore land in the same second: the restored
# tree keeps executing MUTATED bytecode, and every later mutation is silently
# graded on a poisoned tree. That is what happened on the first sweep. Two
# defences: never write bytecode, and re-assert the clean baseline after every
# restore so contamination aborts the run instead of producing quiet garbage.
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
BASELINE = 107


def _pytest():
    subprocess.run(["find", ARM, "-name", "__pycache__", "-type", "d",
                    "-exec", "rm", "-rf", "{}", "+"], capture_output=True)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=ARM, capture_output=True, text=True, timeout=300, env=ENV,
    )


def main():
    base = _pytest()
    if base.returncode:
        sys.exit(f"baseline is not green before sweep:\n{base.stdout[-800:]}")
    print(f"baseline green: {base.stdout.strip().splitlines()[-1]}\n")

    rows = []
    for name, axis, rel, old, new in SPECS:
        path = os.path.join(ARM, rel)
        src = open(path).read()
        n = src.count(old)
        if n != 1:
            rows.append((name, axis, f"SITE ERROR (count={n})", ""))
            continue
        open(path, "w").write(src.replace(old, new, 1))
        try:
            r = _pytest()
            tail = (r.stdout.strip().splitlines() or ["?"])[-1]
            verdict = "KILLED" if r.returncode else "SURVIVED"
        except subprocess.TimeoutExpired:
            verdict, tail = "TIMEOUT", "(>300s — treat as killed-by-hang)"
        finally:
            open(path, "w").write(src)
        # contamination check: restored tree must be green again
        chk = _pytest()
        if chk.returncode:
            rows.append((name, axis, verdict, tail))
            print(f"{name}: verdict={verdict}")
            sys.exit(f"ABORT — tree not green after restoring {name}:\n"
                     f"{chk.stdout[-800:]}")
        rows.append((name, axis, verdict, tail))

    print(f"{'mutation':30} {'axis':6} {'verdict':9} detail")
    print("-" * 96)
    for name, axis, verdict, tail in rows:
        print(f"{name:30} {axis:6} {verdict:9} {tail[:48]}")
    surv = [r for r in rows if r[2] == "SURVIVED"]
    print(f"\nSURVIVED: {len(surv)}/{len(rows)}")
    for name, axis, _, _ in surv:
        print(f"  - {name}  [{axis}]")


if __name__ == "__main__":
    main()
