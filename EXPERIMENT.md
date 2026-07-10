# Experiment: ambiguous-spec A/B (IntervalSet) — Experiment Y

written: 2026-07-11 · follows the subcut experiment (see subcut-trial/HANDOFF.md)

## Question
Does the loopspace pipeline (loopplan edge-derivation + looprun
verification) recover behavior that a **deliberately under-specified** spec
*forces but does not enumerate* — behavior a solo model, handed the same
spec, might slip on? The subcut experiment found delta=0 on a *precise*
spec; this changes exactly one variable: **spec ambiguity**.

## Design (Experiment Y — loopspace end-to-end vs solo)
- **Shared input:** one deliberately shallow spec. It pins the representation
  (closed integer intervals `[a,b]`; `start>end` = empty set) and states a
  precise invariant — `intervals()` is the SHORTEST list of closed integer
  intervals whose union equals exactly the members — but does NOT enumerate
  the merge/split edge cases that invariant forces. Both arms get identical
  spec prose.
- **Arm B (loopspace)** — `~/code/intervalset-trial`: frontier authors
  `plan.md` via loopplan discipline (derives the forced edges from the
  invariant into concrete acceptance criteria); ornith runs looprun
  (staged implementer + fresh verifier per task) headless in opencode.
- **Arm A (solo)** — `~/code/intervalset-solo`: same shallow spec only (no
  plan — planning is loopspace's contribution); ornith builds solo headless,
  prompted to honor R1-R7 and the invariant, iterate to green, stop.
- **Grading:** `experiment/intervalset_oracle.py` — a held-out oracle
  authored independently BEFORE either arm was built, testing only
  consequences the shared invariant *forces* (so grading is fair, not
  telepathy). Neither arm sees it. 56 assertions. Embeds an independent
  brute-force reference so stress cases are not hand-computed; self-tested
  green (55/55, large-magnitude case excluded from the brute self-test only).

## Fairness invariants
- Every oracle case is entailed by the invariant BOTH arms received; no
  oracle case tests a free choice (all free choices pinned in the spec).
- No experiment/meta framing leaks into the arms' spec (no "this is
  under-specified, derive the edges" nudge) — kept here only, so solo is a
  true baseline.
- Same held-out-oracle grading method as subcut.

## Forced edges the oracle probes (NOT enumerated in the spec)
adjacency merge (`[1,3]+[4,6]→[1,6]`, the +1 over integers), multi-interval
bridging, contained/idempotent add, empty-range (`start>end`) no-op,
remove-splitting, boundary trims, cross-multiple removal, sorted/non-adjacent
readout, negatives & zero-spanning, randomized stress vs brute reference.

## Grade
    PYTHONPATH=<repo> python3 -m pytest experiment/intervalset_oracle.py -q
(run the oracle file against each arm's repo root; copy it out of the trial
repo so the arm never has it in-tree during its own run).

## Result (2026-07-11)
**Both arms 56/56 on the held-out oracle. Delta = 0 — again, now on an
ambiguous spec.**

| | Arm A (solo) | Arm B (loopspace) |
|---|---|---|
| held-out oracle | 56/56 | 56/56 |
| input | shallow spec only | shallow spec + loopplan plan + looprun verify |
| impl | 76 LOC, single `__init__.py` | 82 LOC, `interval_set.py` + `__init__.py` |
| self-tests | 49 | 36 (test_add + test_remove + conftest) |
| loop stats | 1 opencode session, ~340s | tasks 1.1 & 1.2 both PASS first try, phase verified |

### What this shows
- Solo ornith, given ONLY the shallow spec (invariant stated, edges NOT
  enumerated, no plan), independently derived every forced edge: adjacency
  merge (`e < start-1 or s > end+1` — the integer off-by-one a naive impl
  misses), multi-interval bridging, remove-splitting, boundary trims,
  empty-range no-op, and passed the randomized stress + large-magnitude
  cases. Its own approach note explicitly reasoned "adjacent intervals
  `[a,b]` and `[b+1,c]` are always merged on add" — derivation, not luck.
- loopspace (Arm B) also reached 56/56, both tasks PASS on the first
  implementer attempt, verifier confirmed, phase verified. It added
  verification discipline but **no correctness delta** — solo was already
  fully correct. Notably solo wrote MORE self-tests (49 vs 36) without a
  plan telling it to.
- **Replicates and strengthens the subcut finding (delta 0 on a precise
  spec): even deliberately under-specified — invariant stated but
  consequences left implicit — a capable model + a precise invariant is
  enough. The ambiguity axis, predicted to be the highest-discrimination
  test, still yields delta 0** because ornith derives forced consequences
  from a stated invariant reliably. loopspace's verification loop is
  redundant whenever the model doesn't actually slip.

### Operational finding (headless entry)
The documented headless entry `opencode run "Read <abs>/loopresume/SKILL.md
and follow it exactly."` FAILED on the first Arm B attempt: ornith resolved
the relative `.loopspace/` path against the SKILL's own directory
(`/Users/arden/code/loopspace/.loopspace`, not present) and reported "no
unfinished run to resume" — a no-op exit (0 code, 0 work). Fixed by pinning
the project dir in the prompt: state that the loopspace project is the cwd
(`/Users/arden/code/intervalset-trial`) and every `.loopspace/...` path
resolves there. Worth folding into the harness profile / handoff — the raw
"Read abs SKILL" entry is fragile with a local model that anchors relative
paths to the last-read file.

### Where a delta would require going next
Both delta-0 results share a cause: the model never actually produced a bug
the invariant/spec didn't already prevent. To surface loopspace's value the
next experiment must make the model *genuinely slip* — heavy task with real
state/partial-failure branches (exercises the untested 3-lens panel), or a
long multi-session run where drift/context-loss hurts solo while
loopspace's fresh-agent-per-task + handoff discipline holds. Pure ambiguity
did not do it.
