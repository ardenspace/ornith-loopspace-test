"""Gate G3 probes — R7 (ranges), R8 (SUM/MIN/MAX/COUNT), R9 (cycles).

Derived fresh for this gate round from the frozen spec alone (replaces any
earlier tests/probes_gate_G3.py). Every case is input -> the exact spec-dictated
output, citing the R-id. Cross-cutting cases exercise G3 behavior where it meets
already-gated G1 (R1/R2) and G2 (R3-R6).
"""
from gridcalc import Workbook


def _s(name="S1"):
    return Workbook().add_sheet(name)


# --- Scenario 1: R7 range validity & mis-ordering (each dimension independent) --
def test_r7_valid_range_row_major_sum():
    s = _s()
    s.set("A1", 1); s.set("B1", 2); s.set("A2", 3); s.set("B2", 4)
    s.set("A3", "=SUM(A1:B2)")
    assert s.get("A3") == 10                      # R7: valid TL<=BR both dims

def test_r7_both_dims_misordered_ref():
    s = _s()
    s.set("A1", 1); s.set("B2", 4)
    s.set("C1", "=SUM(B2:A1)")                     # col B>A AND row 2>1
    assert s.get("C1") == "#REF!"                  # R7

def test_r7_row_only_misordered_ref():
    # Equal columns, TL.row > BR.row -> #REF! (R7 second clause alone).
    s = _s()
    s.set("A1", 9); s.set("A2", 9)
    s.set("C1", "=SUM(A2:A1)")
    assert s.get("C1") == "#REF!"                  # R7: 2 > 1 on equal col

def test_r7_col_only_misordered_ref():
    # Equal rows, TL.col > BR.col -> #REF! (R7 first clause alone).
    s = _s()
    s.set("A1", 9); s.set("B1", 9)
    s.set("C1", "=SUM(B1:A1)")
    assert s.get("C1") == "#REF!"                  # R7: B > A on equal row

def test_r7_row_only_misorder_via_min():
    # Same guard must hold for MIN, not just SUM.
    s = _s()
    s.set("A1", 1); s.set("A2", 2)
    s.set("C1", "=MIN(A2:A1)")
    assert s.get("C1") == "#REF!"                  # R7

def test_r7_offgrid_endpoint_ref():
    s = _s()
    s.set("A1", 1)
    s.set("C1", "=SUM(A1:A100)")                   # A100 off grid (R6/R7)
    assert s.get("C1") == "#REF!"
    s.set("C2", "=SUM(A0:A5)")                     # A0 denotes no cell (R6)
    assert s.get("C2") == "#REF!"


# --- Scenario 2: R7 first error in row-major visit order short-circuits --------
def test_r7_rowmajor_first_error_wins():
    s = _s()
    # A1:B3 visit order: A1,B1,A2,B2,A3,B3. B1 (#DIV!) precedes A2 (string).
    s.set("B1", "=1/0"); s.set("A2", "str")
    s.set("C1", "=SUM(A1:B3)")
    assert s.get("C1") == "#DIV!"                  # R7: B1 first, not #TYPE!

def test_r7_string_member_type_fuel():
    s = _s()
    s.set("A1", 7); s.set("B1", "x")
    s.set("C1", "=SUM(A1:B1)")
    assert s.get("C1") == "#TYPE!"                 # R7: str member is #TYPE! fuel


# --- Scenario 3: R8 SUM/MIN/MAX/COUNT over empty & mixed ----------------------
def test_r8_all_empty_aggregates():
    s = _s()
    s.set("A1", "=SUM(C1:C3)")                     # R8: all-empty SUM -> 0
    s.set("A2", "=MIN(C1:C3)")                     # R8: all-empty MIN -> #TYPE!
    s.set("A3", "=MAX(C1:C3)")                     # R8: all-empty MAX -> #TYPE!
    assert s.get("A1") == 0
    assert s.get("A2") == "#TYPE!"
    assert s.get("A3") == "#TYPE!"

def test_r8_empty_cells_skipped_in_aggregate():
    s = _s()
    s.set("A1", 5); s.set("A3", 3)                 # A2 empty -> contributes nothing
    s.set("B1", "=SUM(A1:A3)"); s.set("B2", "=MIN(A1:A3)"); s.set("B3", "=MAX(A1:A3)")
    assert s.get("B1") == 8
    assert s.get("B2") == 3
    assert s.get("B3") == 5

def test_r8_count_structural_no_eval():
    s = _s()
    s.set("A1", 5); s.set("A2", "x"); s.set("A3", "=1/0")  # A4 empty
    s.set("B1", "=COUNT(A1:A4)")
    assert s.get("B1") == 3                        # R8: 3 non-empty, no error

def test_r8_count_self_reference_not_cycle():
    s = _s()
    s.set("A1", "=COUNT(A1:A1)")
    assert s.get("A1") == 1                        # R8 explicit example

def test_r8_count_invalid_range_ref():
    s = _s()
    s.set("A1", "=COUNT(B2:A1)")
    assert s.get("A1") == "#REF!"                  # R7 invalid range still #REF!


# --- Scenario 4: R9 cycles ---------------------------------------------------
def test_r9_direct_self_cycle():
    s = _s()
    s.set("A1", "=A1")
    assert s.get("A1") == "#CYCLE!"

def test_r9_mutual_cycle():
    s = _s()
    s.set("A1", "=B1"); s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    assert s.get("B1") == "#CYCLE!"

def test_r9_cycle_through_sum_range():
    s = _s()
    s.set("A1", "=SUM(A1:A2)"); s.set("A2", 5)     # range covers in-progress A1
    assert s.get("A1") == "#CYCLE!"                # R9 via range

def test_r9_offcycle_dependent_propagates():
    s = _s()
    s.set("A1", "=B1"); s.set("B1", "=A1")
    s.set("C1", "=A1+1")
    assert s.get("C1") == "#CYCLE!"                # R9/R5 propagation off cycle


# --- Scenario 5: cross-cut R5 (G2) ordering meets R7/R8 range functions -------
def test_crosscut_r5_operand_before_range():
    s = _s()
    s.set("A1", 1); s.set("B1", 2); s.set("D1", "=1/0")
    s.set("C1", "=D1+SUM(A1:B1)")                  # R5 L-to-R: D1 first
    assert s.get("C1") == "#DIV!"

def test_crosscut_r5_range_offends_first():
    s = _s()
    s.set("A1", "x"); s.set("B1", 2); s.set("D1", "=1/0")
    s.set("C1", "=SUM(A1:B1)+D1")                  # SUM (#TYPE!) precedes D1
    assert s.get("C1") == "#TYPE!"


# --- Scenario 6: cross-cut R2/R6 (G1/G2) typed read meets R8 ------------------
def test_crosscut_formula_string_member_type_fuel():
    s = _s()
    s.set("A1", "hi"); s.set("A2", "=A1")          # R6 typed read -> str result
    s.set("B1", "=MAX(A2:A2)")
    assert s.get("B1") == "#TYPE!"                 # R7/R8: str member -> #TYPE!

def test_crosscut_replacement_clears_cycle_then_sums():
    # G1 R2 replacement x R9 x R8.
    s = _s()
    s.set("A1", "=B1"); s.set("B1", "=A1")
    assert s.get("A1") == "#CYCLE!"
    s.set("B1", 7)                                  # replace formula with literal
    assert s.get("A1") == 7
    s.set("C1", "=SUM(A1:B1)")
    assert s.get("C1") == 14
