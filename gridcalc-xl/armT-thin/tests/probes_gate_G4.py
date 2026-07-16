"""Gate G4 probes — R10 (incremental counting / closures / bounds),
R11 (naive equivalence), R12 (size/depth/magnitude bounds).

Derived fresh from FULL SPEC for this gate round. Each test states the
input and the exact spec-dictated output, citing the R-id. Several probes
are cross-cutting into already-gated groups (G1 store, G2 grammar, G3
ranges/cycles), as required.

Trust nothing the lead produced: expected values below come from the spec
text, not from the implementation.
"""

from gridcalc import Workbook


def fresh():
    return Workbook().add_sheet("S")


# --- Probe 1: R10 counting rule + repeat-read bound ------------------------
# A1=1 (literal), B1==A1+1, C1==B1+1, D1==B1+C1.
# get(D1) starts exactly the 3 formula cells D1,B1,C1 (A1 literal never
# counts; C1's read of B1 hits the cache, no second start) → delta 3, value 5.
# A second get(D1) with no edit in between adds 0 (R10 repeat-read).
def test_r10_started_count_and_repeat_read_zero():
    s = fresh()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    s.set("C1", "=B1+1")
    s.set("D1", "=B1+C1")

    before = s.eval_count
    assert s.get("D1") == 5          # R11: 2+3
    assert s.eval_count - before == 3  # R10: D1,B1,C1 started once each

    before = s.eval_count
    assert s.get("D1") == 5
    assert s.eval_count - before == 0  # R10 repeat-read: cached, +0


# --- Probe 2: R5 short-circuit is observable via R10 counters (G2 cross-cut) -
# A1==1/0+B1, B1==99+1. Per R5 the first error (#DIV! from 1/0) is the
# result and operands textually after it (B1) are NOT evaluated → B1's
# computation never starts. get(A1) therefore adds exactly 1 (only A1), and
# a later fresh get(B1) adds 1 — proving B1 was never computed during get(A1).
def test_r5_shortcircuit_leaves_later_operand_unstarted():
    s = fresh()
    s.set("A1", "=1/0+B1")
    s.set("B1", "=99+1")

    before = s.eval_count
    assert s.get("A1") == "#DIV!"      # R4/R5
    assert s.eval_count - before == 1  # R10: only A1 started; B1 skipped

    before = s.eval_count
    assert s.get("B1") == 100          # R3
    assert s.eval_count - before == 1  # B1 computed now for the first time


# --- Probe 3: R10 irrelevant-edit (+0) vs relevant-edit (>=1, <=closure) ----
# B1==A1+1. Editing Z99 (outside B1's closure {B1,A1}) leaves get(B1) at +0.
# Editing A1 (inside the closure) forces recompute: value updates and the
# add is >=1 and <= the number of formula cells in the closure (just B1 → 1).
# Writing content identical to what A1 already holds still counts (R10: no
# content-comparison short-circuit).
def test_r10_irrelevant_zero_relevant_recomputes():
    s = fresh()
    s.set("A1", 1)
    s.set("B1", "=A1+1")
    assert s.get("B1") == 2

    s.set("Z99", 100)                  # irrelevant edit (not in closure)
    before = s.eval_count
    assert s.get("B1") == 2
    assert s.eval_count - before == 0  # R10 irrelevant-edit bound

    s.set("A1", 5)                     # relevant edit
    before = s.eval_count
    assert s.get("B1") == 6            # R11 against restored contents
    assert s.eval_count - before == 1  # >=1 and <= 1 formula cell in closure

    s.set("A1", 5)                     # identical content — still an edit
    before = s.eval_count
    assert s.get("B1") == 6
    assert s.eval_count - before == 1  # R10: no content-comparison short-circuit


# --- Probe 4: R10 formula replacement cleans stale dependency edges (G1 x-cut)
# C1==A1+1 then replaced by C1==B1+1. After replacement, editing A1 (no
# longer referenced) must be irrelevant (+0); editing B1 (now referenced) is
# relevant. A stale A1->C1 edge surviving the replacement would wrongly
# recompute on the A1 edit.
def test_r10_replacement_drops_old_edges():
    s = fresh()
    s.set("A1", 1)
    s.set("B1", 10)
    s.set("C1", "=A1+1")
    assert s.get("C1") == 2

    s.set("C1", "=B1+1")               # R2 replacement
    assert s.get("C1") == 11

    s.set("A1", 99)                    # old dependency — must be irrelevant
    before = s.eval_count
    assert s.get("C1") == 11
    assert s.eval_count - before == 0

    s.set("B1", 20)                    # new dependency — relevant
    before = s.eval_count
    assert s.get("C1") == 21
    assert s.eval_count - before == 1


# --- Probe 5: R8 COUNT is structural + R10 closure/counting (G3 cross-cut) --
# COUNT counts non-empty members WITHOUT evaluating them (no counter for
# members) and members do not participate in cycle detection. SUM by
# contrast evaluates every non-empty member (each starts, each counts).
def test_r8_count_structural_vs_sum_evaluating_under_r10():
    # COUNT: B1==COUNT(A1:A1) with A1 a formula. get(B1) starts only B1.
    s = fresh()
    s.set("A1", "=1+1")
    s.set("B1", "=COUNT(A1:A1)")
    before = s.eval_count
    assert s.get("B1") == 1            # R8: one non-empty member
    assert s.eval_count - before == 1  # R10: A1 never evaluated by COUNT
    # A1 was genuinely not computed above → first real compute counts now.
    before = s.eval_count
    assert s.get("A1") == 2
    assert s.eval_count - before == 1

    # COUNT self-reference is not a cycle (R8): A1==COUNT(A1:A1) → 1.
    s2 = Workbook().add_sheet("T")
    s2.set("A1", "=COUNT(A1:A1)")
    before = s2.eval_count
    assert s2.get("A1") == 1           # R8: structural, no #CYCLE!
    assert s2.eval_count - before == 1

    # SUM evaluates every non-empty member: B1==SUM(A1:A2) starts B1,A1,A2.
    s3 = Workbook().add_sheet("U")
    s3.set("A1", "=1+1")
    s3.set("A2", "=2+2")
    s3.set("B1", "=SUM(A1:A2)")
    before = s3.eval_count
    assert s3.get("B1") == 6           # R7/R8
    assert s3.eval_count - before == 3  # R10: B1,A1,A2 started


# --- Probe 6: R9 cycle caching + R10 in-progress-not-restarted (G3 x-cut) ---
# Mutual cycle A1==B1+1, B1==A1+1. get(A1) starts A1 then B1; the read of the
# in-progress A1 returns #CYCLE! without starting A1 a second time → delta 2.
# Both cells are #CYCLE!, cached (repeat/other get adds 0). Editing A1 to a
# literal clears the cycle for both.
def test_r9_mutual_cycle_counts_and_clears():
    s = fresh()
    s.set("A1", "=B1+1")
    s.set("B1", "=A1+1")

    before = s.eval_count
    assert s.get("A1") == "#CYCLE!"    # R9
    assert s.eval_count - before == 2  # R10: A1,B1 started; in-progress A1 not restarted

    before = s.eval_count
    assert s.get("B1") == "#CYCLE!"    # R9: on the cycle
    assert s.eval_count - before == 0  # cached (R10)

    s.set("A1", 3)                     # edit clears the cycle
    assert s.get("A1") == 3            # literal
    assert s.get("B1") == 4            # R11: A1+1 = 4 against restored content


# --- Probe 7: R11 naive equivalence through a diamond under repeated edits --
# D1==B1+C1, B1==A1*2, C1==A1+3. Every get equals a naive full recompute at
# the current stored contents, regardless of caching/incremental strategy.
def test_r11_diamond_matches_naive_recompute():
    s = fresh()
    s.set("A1", 10)
    s.set("B1", "=A1*2")
    s.set("C1", "=A1+3")
    s.set("D1", "=B1+C1")
    assert s.get("D1") == 33           # 20 + 13
    assert s.get("B1") == 20
    assert s.get("C1") == 13

    s.set("A1", 1)
    assert s.get("D1") == 6            # 2 + 4  (naive)
    assert s.get("B1") == 2
    assert s.get("C1") == 4

    s.set("A1", -4)
    assert s.get("B1") == -8
    assert s.get("C1") == -1
    assert s.get("D1") == -9


# --- Probe 8: R12 directed bounds — chain of 256 formula cells, 500-deep -----
# unary tower, and 2**63-1 magnitude. Within-bounds evaluations must complete
# WITHOUT raising (no RecursionError inside the bounds).
def test_r12_directed_within_bounds_complete():
    s = fresh()
    # Build A1=1 literal then a chain of 256 formula cells across columns,
    # each == predecessor + 1. get on the last reaches 256 formula cells.
    def addr(i):
        return chr(ord("A") + i // 99) + str(i % 99 + 1)
    s.set(addr(0), 1)
    for i in range(1, 257):
        s.set(addr(i), "=" + addr(i - 1) + "+1")
    assert s.get(addr(256)) == 257     # R12(b): 256-cell chain completes

    # 500-deep unary-minus tower (fits in 512 source chars, R12(a)); an even
    # count of minuses over 1 is 1.
    s.set("B1", "=" + "-" * 500 + "1")
    assert s.get("B1") == 1            # R3 unary stacks, R12 no RecursionError

    # Magnitude at the R12(c) ceiling 2**63-1 as literal and as a product.
    s.set("C1", "=9223372036854775807")
    assert s.get("C1") == 2 ** 63 - 1
    s.set("D1", "=4611686018427387903*2+1")
    assert s.get("D1") == 2 ** 63 - 1  # R12(c): |intermediate/result| <= 2**63-1
