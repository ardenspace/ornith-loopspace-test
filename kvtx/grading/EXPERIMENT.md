# Experiment: heavy-task A/B (kvtx) — Experiment Z

written: 2026-07-11 · follows subcut (precise-spec, delta 0) and intervalset
(ambiguous-spec, delta 0)

## Question
Does the loopspace pipeline add a correctness delta on a task **hard enough
that the model actually slips** — exercising the so-far-untested part of
looprun: the **three-lens heavy verification panel** (correctness / security
/ test-integrity) plus **retry-on-FAIL**? Two prior A/B experiments (precise
spec, ambiguous spec) both gave delta 0 because ornith never produced a bug
the spec didn't already prevent. Difficulty is the remaining lever.

## Design (Experiment Z — isolate looprun's heavy loop)
- **Task:** `kvtx` — an in-memory key/value `Database` with nested
  transactions (`begin`/`rollback`/`commit`) and a value-count query
  (`count`). The killer is keeping `count` consistent across transaction
  overlays through overwrite + nested rollback — the classic spot
  implementations slip. It is a state machine with partial-failure branches
  → honestly `risk: heavy`.
- **Spec is behaviorally PRECISE** (unlike intervalset): the difficulty is
  implementing the state machine, not reading the spec. Both arms get
  identical spec AND identical plan (edge-enumerated), so the ONLY variable
  is looprun's heavy verification loop.
- **Arm B (loopspace)** — `~/code/kvtx-trial`: ornith runs looprun; task 1.2
  is `risk: heavy` → three-lens panel (template D) + retry-on-FAIL.
- **Arm A (solo)** — `~/code/kvtx-solo`: same spec + plan; ornith builds
  solo, iterates to its own green, stops.
- **Grading:** `kvtx_oracle.py` — held-out, authored before either arm,
  neither sees it. 64 assertions: named cases for the slip-prone
  count/overlay interactions + 40 randomized command sequences cross-checked
  against an independent overlay-layer reference. Self-tested green (64/64).

## Isolation vs prior experiments
This is Experiment **X** structure (identical spec+plan both arms, only
looprun differs) — same as the subcut isolation — but with a HARD task and a
`heavy` tag, so the untested three-lens panel + retry actually run. If
ornith slips, the delta shows whether the panel/retry caught it (Arm B) while
solo shipped the bug (Arm A).

## What would produce a delta
ornith writes buggy transaction/count code AND self-tests that miss the bug
(declaring premature success) → Arm A ships it, held-out oracle fails Arm A;
Arm B's correctness lens (criteria→test mapping + mechanical failed-first) or
test-integrity lens catches it, forces a retry, ships correct code. Delta =
oracle-pass gap.

## Grade
    PYTHONPATH=<repo> python3 -m pytest kvtx_oracle.py -q

## Result (2026-07-11)
**Both arms 64/64 on the held-out oracle. Correctness delta = 0 (4th time) —
but the heavy three-lens panel fired for real for the first time.**

| | Arm A (solo) | Arm B (loopspace) |
|---|---|---|
| held-out oracle | 64/64 | 64/64 |
| impl size | **60 LOC, no dead code** | 135 LOC (incl. dead `Store` class) |
| self-tests | 26 | 27 |
| attempts | 1 session | 1.1: 1 attempt · 1.2: **2 attempts** (1 retry) |
| TDD | tests written post-impl (unchecked) | **enforced** — see below |

### The interesting part: the heavy panel actually did something
Task 1.2 (`risk: heavy`) ran the three-lens panel. **Attempt 1 FAILed**:
correctness PASS / security PASS / **test-integrity FAIL**. The
test-integrity lens caught the implementer's own contradictory evidence —
it reported "15 tests failed-first: (none - all passed on first run after
implementation)", i.e. it wrote tests AFTER the code, not TDD. The panel
rejected it and forced a retry. **Attempt 2** did real TDD (correctness lens
mechanically confirmed the tests fail with the implementation stashed —
ImportError) and all three lenses PASSed.

This is the **first verification intervention across all four experiments**
(subcut, intervalset ×2 arms, kvtx). The previously-untested heavy panel +
retry machinery works on the ornith/opencode local backend, and the
test-integrity lens specifically enforced TDD discipline the model would
otherwise skip.

### But it was a PROCESS fix, not a CORRECTNESS save
The correctness lens PASSed attempt 1 too — attempt 1's code was already
correct. So the retry fixed *how the tests were produced* (genuine
failed-first evidence), not a bug. Net shipped-correctness delta is still 0.
The panel guards against the **test-gaming failure mode** (tests written to
pass buggy code, hiding the bug) — it just didn't bite here because ornith's
code was correct. The guard operated; the thing it guards against didn't
occur.

### Honest conclusion
Even on a classic slip-prone heavy task (nested-tx `count`/overlay
consistency, where humans routinely bug out), ornith shipped correct code
solo — including 40 randomized sequences vs an independent overlay
reference. loopspace added **no correctness delta and produced messier code**
(a dead `Store` class its own panel flagged as non-blocking scope creep,
135 vs 60 LOC). What loopspace *did* add is **process/integrity assurance**:
it enforced real TDD (caught post-hoc tests, forced a redo) and surfaced
advisories (dead code, missing `[build-system]` so `pip install -e .` fails).
For a model this capable, loopspace's value is insurance against test-gaming
and discipline drift, not correctness — and that insurance costs an extra
retry and some verbosity.

### Across all four experiments
Correctness delta = 0 every time (precise spec, ambiguous spec, heavy task).
The only loopspace intervention that ever fired was a **process** catch, not
a **correctness** one. To find a correctness delta you now almost certainly
need the model to *actually ship a wrong answer* — which ornith has not done
on any well-specified task, easy or hard. The remaining candidate is
**long multi-session runs** where context drift / handoff loss hurts a solo
build while loopspace's fresh-agent-per-task + handoff discipline holds.

## Rerun (2026-07-11) — loopspace 0.14.0 intra-phase carry, coherence gap closed

The coherence finding above drove a loopspace repair ("intra-phase carry":
implementer `exports:` self-report, a PRIOR WORK THIS PHASE block assembled
from the journal into every dispatch, and two-layer duplication enforcement
— merge `4f91830` + review follow-up `d21f392`). Rerun with identical
spec+plan, only the loopspace version changed; archived at
`../armB-loopspace-rerun/`.

| | old Arm B (0.13) | rerun (0.14) | Arm A solo |
|---|---|---|---|
| held-out oracle | 64/64 | **64/64** | 64/64 |
| impl size | 135 LOC, dead `Store` + dead `_vk` | **85 LOC, no dead code** | 60 LOC |
| task 1.2 | 2 attempts (test-integrity FAIL) | **1 attempt, all lenses PASS** | — |

Task 1.2 received `[1.1] files: … — exports: kvtx.database.Store —
set/get/delete/count, O(1) two-dict` in its dispatch (verified in the
opencode session store) and **wrapped Store by composition** instead of
re-implementing it — its own exports line says "Store … (unchanged)". The
phase verifier applied the new blocking duplication check ("no duplication
between tasks") and surfaced the `Database.count()` O(n) vs `Store.count()`
O(1) asymmetry as a spec-concern — the same class of observation that went
completely unflagged in the 0.13 run.

Caveats: n=1; the enforcement path (verifier FAIL on duplication) never
fired because the information alone was enough — deterrence worked before
the teeth were needed. One benign harness slip: ornith dropped template A's
fixed contract sentence ("never build a parallel implementation … verifier
FAIL") when instantiating the dispatch, delivering the block data without
the warning — a candidate for a "fixed template text is dispatched
verbatim" clarification in looprun. The remaining 85-vs-60 LOC gap is the
plan's intended two-layer structure (tx layer over base store), not waste.
Correctness delta remains 0, as expected — that was never this repair's
target; the multi-session drift experiment is still the open question.
