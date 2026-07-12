# Experiment W: multi-session drift A/B (gridcalc)

written: 2026-07-11 (design; run pending) · follows subcut (X, precise-spec
delta 0), intervalset (Y, ambiguous-spec delta 0), kvtx (Z, heavy-task
delta 0 + coherence gap → loopspace 0.14 intra-phase carry, verified by
rerun)

## RESULTS (2026-07-12, both arms complete)

- **arm B (loopspace)**: completed 11/11 tasks, one supervised run, wall
  ~5.9h (incl. ~2h tier-A stall on 2.1 — ornith reasoning-drop on heavy
  subagent dispatches; finished under tier C role-swap). Own suite 161
  green. **Oracle 124/131.** All 7 failures share one root cause:
  `#REF!`/`#CYCLE!` degraded to `#TYPE!` when a formula references an
  error-bearing cell — latent since phase 2-3 (R11 was never fully green),
  so *not* a phase-4 regression. Trajectory (17 snapshots,
  `../armB-loopspace/trajectory.csv`): monotonic 18→124, **0 drift
  events**. Coherence findings: 4.2-4.4 finished but left uncommitted at
  `run_status: complete` (preserved via labeled grader commit
  `gridcalc-trial@93457e0`); run branch never advanced past plan-approval;
  tier-C journal entries show weak failed-first evidence (4.2 "tests
  adjusted to match actual behavior", 4.3/4.4 none).
- **arm A (solo)**: declared `<DONE>` after **one 40-minute session** —
  the multi-session boundary was never crossed. Own suite 188 green.
  **Oracle 130/131** (single failure: R10 error-result caching —
  eval_count 2 where 1 expected). Kept a 46-line structured NOTES.md
  (status / architecture / 7 design decisions / limitations) that was
  never consumed by a later session. Trajectory: seed→final, 0 drift
  events (trivially).
- **Primary criterion: oracle delta B − A = 124 − 130 = −6/131 (−4.6pp)**
  — first nonzero correctness delta of the series, **in solo's favor**.
- Measurement note: a stray `pip install -e` (arm B created setup.py and
  self-installed into site-packages) made pre-code snapshots fall back to
  the live repo on import, contaminating the first trajectory pass —
  uninstalled and regraded. Protocol addition: preflight
  `python3 -c "import <pkg>"` must FAIL before grading.

### Verdict vs pre-registration

The premise did not engage: gridcalc fits in one ornith context when
built directly, so arm A faced zero drift pressure — none of the three
pre-registered interpretations applies cleanly. What was actually
measured is **harness overhead vs direct build at one-shottable scale**:
loopspace consumed ~9x wall clock, hit a backend-specific tier-A stall,
and its per-task decomposition let a cross-phase error-propagation bug
survive every per-task verifier (each task's local tests passed; the
composed semantics were wrong). Solo held the whole error-semantics model
in one context (NOTES decision #6 is exactly the semantics arm B got
wrong) and passed R11 clean. Caveats: n=1 per arm; arm B ran tier C
(weakened verifier isolation) after the tier-A stall; the delta is one
root-cause bug, not diffuse decay. The structural drift claim remains
untested — testing it requires a task that genuinely overflows a solo
context window (a W′ would need ~3-5x this size).

## Question

Four experiments in, every correctness delta is 0 and the one axis
loopspace lost on (intra-phase coherence) has been repaired and verified.
The remaining untested claim is loopspace's *structural* core: that
fresh-agent-per-task + handoff discipline survives runs **too big for one
context window**, where a solo build must cross session boundaries and can
drift — forget early invariants, regress finished features, lose unwritten
decisions between sessions. This is the last axis on which a correctness
delta is plausible for a capable model on a well-specified task.

## Task: `gridcalc` — mini spreadsheet engine, 4 phases / 10-11 tasks

Drift pressure is built into the structure: each phase forces revisiting
the previous phases' evaluation path.

- **Phase 1 — cell store** (2 tasks): A1-style addressing, literal
  set/get, types (number / string / empty).
- **Phase 2 — formulas** (3 tasks; parser `heavy`): `=A1+B2*2` grammar
  (arithmetic, parentheses, comparison), cell references, full recompute
  on read, error values (`#REF!` etc.) with propagation.
- **Phase 3 — ranges, functions, cycles** (3 tasks; cycle detection
  `heavy`): `SUM(A1:B3)`-family over ranges, circular-reference detection
  → `#CYCLE!` (self-reference, 2-cycles, cycles through ranges).
- **Phase 4 — incremental recompute** (2-3 tasks; `heavy`): dependency
  graph + dirty propagation. An `eval_count` counter is part of the public
  API so incrementality itself is acceptance-testable ("editing a cell
  outside A's dependency closure re-evaluates nothing on read of A").

Phase 4 is the designed trap: it rewrites the phase 2-3 evaluation path
while the *results* must stay identical — drift shows up precisely as
regressions on early requirements.

Sizing: kvtx rerun did 2 tasks in ~1-1.5h on ornith (opencode, Tier A), so
10-11 tasks ≈ 6-8h ≈ one overnight per arm. Budget: one unattended night
per arm, arm B first (daytime left for debugging if the harness fails),
arm A the next night.

## Arms — the only variable is the execution machinery

Both arms receive the **identical SPEC.md + PLAN.md** (frontier-authored:
Claude Code via loopspec → loopplan, then the same content seeded to arm
A) — Experiment X/Z isolation structure. loopspace version: 0.14.0 +
`d21f392` (reuse check judges from the tree) + `0d2cd3a` (templates
dispatched verbatim).

- **Arm B (loopspace)** — `~/code/gridcalc-trial`: ornith runs looprun
  under **loopsupervise** (unattended; context-threshold handoffs happen
  without a human typing /clear). Task/phase checkpoint commits are the
  built-in snapshots.
- **Arm A (solo)** — `~/code/gridcalc-solo`: a shell loop of repeated
  `opencode run` calls; each iteration is a fresh session. Prompt: read
  SPEC.md/PLAN.md, continue the implementation from the repo state; you
  MAY keep a free-form progress-notes file if you find it useful (allowed,
  never forced — the "self-managed notes" baseline); print `<DONE>` when
  you judge the project complete. The loop commits the tree after every
  session (snapshot), runs `pkill -9 -f opencode` between iterations
  (zombie GOTCHA), and stops on `<DONE>`, 12 sessions, or 8h, whichever
  comes first.

Fairness notes: arm A's notes policy is deliberately permissive — if solo
survives *because* it kept good notes, that is an honest finding about
what the structured handoff is worth. Non-completion (stall, loop,
premature `<DONE>`) is a valid outcome, not a broken run.

## Grading: held-out oracle, authored before either arm runs

Independently authored (never shown to either arm) and committed to this
directory **before** any run starts — pre-registration. Components:

1. **Brute-force reference** (~100 lines, embedded in the oracle): no
   dependency tracking; every read naively re-evaluates recursively.
   Self-tested green before use.
2. **Named killer cases**: reference-update chains, formula cells inside
   ranges, self-reference / 2-cycle / cycle-through-range, error
   propagation, mixed types, empty-cell semantics.
3. **Randomized sequences**: 40+ random set/formula/read command
   sequences cross-checked against the reference.
4. **Incrementality checks**: `eval_count` upper bounds (phase-4 R-ids
   only).
5. **Every assertion tagged with its R-id group** — enables per-phase
   pass rates per snapshot.

## Trajectory grading — the drift signature

A grading script walks each arm's full commit history: checkout →
run oracle → emit `(snapshot, R-group, pass/fail)` CSV. **Drift event :=
an R-group that passed at snapshot t fails at some t+k.** Even a final
delta of 0 leaves a trajectory comparison (wobbled-and-recovered vs
never-wobbled), which is exactly the information the endpoint-only
experiments couldn't produce.

## Pre-registered verdict criteria

- **Primary**: final held-out oracle pass-rate delta (B − A).
- **Secondary**: drift-event count per arm; sessions consumed; completion
  (did the arm finish at all); arm A's actual notes behavior (did it keep
  notes, were they load-bearing); arm B's handoff quality (journal +
  handoff.md against what the next session actually needed).
- **Interpretations fixed in advance**:
  - Delta > 0 with arm A drift events → loopspace's structural claim
    validated on the local backend; the series ends with a demonstrated
    correctness value.
  - Delta 0 and zero drift events both arms → ornith holds even at
    multi-session scale; final series verdict: loopspace's value for a
    capable model is process/integrity insurance + unattended operation,
    not correctness. This closes the series honestly.
  - Arm A non-completion (stall/loop) with arm B completion → counts as
    a delta in kind: the harness's value is *finishing at all*.

## Operations

- Night 1 = arm B, night 2 = arm A (B first: harness failures get
  daylight).
- Pre-flight (both nights): `pkill -9 -f opencode`; confirm ornith serving
  on :18081 (`llm ornith` if not); prompt pins the project cwd and
  ".loopspace/ resolves there" (headless GOTCHA).
- During B's first task, check the opencode session store (`part` table)
  for the template A contract sentence — verifies the `0d2cd3a`
  verbatim-dispatch reinforcement on a real run.
- Locations: `~/code/gridcalc-trial` (B), `~/code/gridcalc-solo` (A),
  oracle + this design in `gridcalc/grading/` (this repo), run archives
  to `gridcalc/armB-loopspace/`, `gridcalc/armA-solo/` after grading.

## Pre-registration record (2026-07-12)

- Spec authored via loopspec: 3 panel rounds (r1: 6 blocking roots —
  function grammar missing, ref-token classing, COUNT contradiction,
  string-flow hole; r2: 3 blocking — set(X) contradiction, closure
  measurement timing, depth definition; r3: 2 blocking fixed post-panel —
  integer-magnitude bound, literal-edit carve-out). Approved
  `gridcalc-trial@f933d38`.
- Plan authored via loopplan: 4 phases / 11 tasks, heavy = 2.1 parser,
  3.2 cycles, 4.2 dirty propagation. 2 panel rounds (r1 blocking: task
  2.1's #PARSE! tests would die at phase 3 — fixed by pinning only
  forever-invalid inputs and pulling R12 sizing into 2.1/2.2). Approved
  `gridcalc-trial@1099c8a`.
- Oracle: `gridcalc_ref.py` (naive reference, ~250 LOC) +
  `gridcalc_oracle.py` — 47 test functions / 131 executed assertions,
  R-group-tagged (`test_rNN_*`); 40 seeded differential sequences vs the
  reference; R10 (12 checks) asserted against the arm only. Self-test
  (reference graded against itself via `selftest_shim/`, R10 excluded):
  **119/119 green**.
- Trajectory grader: `grade_trajectory.py` — per-commit × per-R-group
  CSV + drift-event detection; smoke-tested on the pre-code trial repo
  (3 snapshots, import-fail rows as expected).
- Neither arm has run yet as of this record.

## Order of work

1. Author SPEC.md via /loopspec, PLAN.md via /loopplan (arm B repo);
   copy both into arm A's seed. Human approves both (last touchpoints).
2. Author + self-test the oracle and the trajectory grading script;
   commit here (pre-registration).
3. Night 1: arm B under loopsupervise. Morning: sanity checks.
4. Night 2: arm A under the session loop script.
5. Trajectory-grade both, archive, write results into this file +
   EXPERIMENTS-LOG.
