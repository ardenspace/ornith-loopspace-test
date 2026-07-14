# Handoff
version: 1
written: 2026-07-14
trigger: phase-boundary
position: 4.4

## Where we are
Phase 4 is verified. This was the final planned phase; the run is ready to be marked complete.

## Next session must know
- `Sheet` remains the single public class exported from `gridcalc`; formulas now evaluate with arithmetic, comparisons, references, range functions, circular-reference detection, dependency-aware caching, R12 bounds hardening, and the cumulative `eval_count` contract.
- Parser and evaluator work through `gridcalc.parser.parse` and `gridcalc.evaluator.evaluate`; no parallel engine was introduced.
- Phase boundary probes live in `tests/probes_phase_1.py`, `tests/probes_phase_2.py`, `tests/probes_phase_3.py`, and `tests/probes_phase_4.py` and must stay green if future work extends the project.

## Watch out for
- none
