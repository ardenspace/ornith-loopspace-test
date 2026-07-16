"""Gate G6 probes — R16 ($ marks), R17 (copy rewrite), R18 (named ranges).

Derived from the frozen spec alone, before opening any lead test file.
Scenarios (input -> spec-dictated output, R-id):

S1  R16: $-marked refs denote exactly the unmarked cell — evaluation,
    ranges, and cycles unaffected; $ matters only to copy.
S2  R17: copy shifts unmarked components by delta, keeps $-marked ones,
    re-rendered in place ("=A1+$A1+A$1+$A$1" copied +1col/+2row ->
    "=B3+$A3+B$1+$A$1").
S3  R17: a shifted component leaving the grid replaces the whole token
    (incl. $s) with #REF!; either endpoint of a RANGE leaving the grid
    replaces the whole range with #REF!; a $-pinned component is never
    shifted, hence protected from replacement.
S4  R17: a REF-shaped token that already denotes no grid cell (A0, B07)
    is kept verbatim, never shifted.
S5  R17 x G2/G5/R18 cross-cut: NAME tokens, STRING contents, INTs and
    function names are never touched by copy ("=AA1" copied stays
    "=AA1"; "=SUM(DATA1)" stays; CONCAT string "A1" stays); #PARSE!
    formula text is copied byte-for-byte.
S6  R17: the token #REF! is grammar-legal as a primary and RANGE-ARG,
    always evaluating to #REF!; copy(src, src) is legal; literal copy
    stores the identical value; copy never evaluates (eval_count flat).
S7  R17/R18: programmer errors raise ValueError with no observable
    state change — copy from empty cell, invalid addresses, invalid
    names (REF-shaped, function names, bad length/charset, non-str),
    invalid targets (mis-ordered, out-of-grid endpoint, non-str).
S8  R18: NAME as primary -> typed value of a single-address or 1x1
    target (#REF! for a larger target); NAME as RANGE-ARG -> its
    binding's range; undefined NAME -> #NAME!; redefinition replaces;
    names are per-sheet (cross-cut G3: SUM/COUNT over NAME; cross-cut
    G5: str value through NAME, LEN(NAME), str in arithmetic #TYPE!).
S9  R18/R17 x G4 cross-cut (R10): define_name is an edit touching
    exactly the mention-holding formula cells of its sheet, with no
    binding-comparison short-circuit; copy is an edit at dst; both add
    0 to unrelated cells.
"""

import pytest

from gridcalc import Workbook


def fresh():
    wb = Workbook()
    return wb, wb.add_sheet("S1")


# ---------------------------------------------------------------- S1: R16


class TestS1DollarMarksEvaluation:
    def test_dollar_forms_evaluate_like_plain(self):
        _, s = fresh()
        s.set("B2", 7)
        s.set("A1", "=$B$2")
        s.set("A2", "=B$2")
        s.set("A3", "=$B2")
        assert s.get("A1") == 7
        assert s.get("A2") == 7
        assert s.get("A3") == 7

    def test_dollar_range_endpoints_in_functions(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("B1", 2)
        s.set("A2", 3)
        s.set("B2", 4)
        s.set("C1", "=SUM($A$1:B$2)")
        s.set("C2", "=MIN($A1:$B$2)")
        s.set("C3", "=MAX(A$1:$B2)")
        assert s.get("C1") == 10
        assert s.get("C2") == 1
        assert s.get("C3") == 4

    def test_dollar_ref_participates_in_cycles(self):
        _, s = fresh()
        s.set("A1", "=$A$1")
        assert s.get("A1") == "#CYCLE!"

    def test_dollar_ref_to_empty_cell_is_zero(self):
        _, s = fresh()
        s.set("A1", "=$C$9+1")
        assert s.get("A1") == 1


# ---------------------------------------------------------------- S2: R17 shift/pin


class TestS2CopyShiftAndPin:
    def test_all_four_dollar_forms_shift_correctly(self):
        # C3: "=A1+$A1+A$1+$A$1" copied to D5 (dcol=+1, drow=+2)
        # -> "=B3+$A3+B$1+$A$1" = B3+A3+B1+A1
        _, s = fresh()
        s.set("A1", 1)
        s.set("A3", 2)
        s.set("B1", 4)
        s.set("B3", 8)
        s.set("C3", "=A1+$A1+A$1+$A$1")
        s.copy("C3", "D5")
        assert s.get("C3") == 1 + 1 + 1 + 1
        assert s.get("D5") == 8 + 2 + 4 + 1

    def test_range_arg_endpoints_shift_with_pins(self):
        # C1: "=SUM($A$1:B2)" copied to D2 (+1,+1) -> "=SUM($A$1:C3)"
        _, s = fresh()
        for addr, v in [("A1", 1), ("B2", 2), ("C3", 4)]:
            s.set(addr, v)
        s.set("C1", "=SUM($A$1:B2)")
        s.copy("C1", "D2")
        assert s.get("C1") == 3
        # D2 holds "=SUM($A$1:C3)": A1(1)+B2(2)+C3(4)+C1(formula, 3) = 10.
        # A dropped pin (B2:C3) would give 6; an unshifted endpoint
        # (A1:B2) would give 3.
        assert s.get("D2") == 10

    def test_copy_of_literal_and_negative_shift(self):
        # "=C3" copied from B2 to A1 (dcol=-1, drow=-1) -> "=B2"
        _, s = fresh()
        s.set("B2", "=C3")
        s.set("C3", 5)
        s.set("B2", "=C3")
        s.copy("B2", "A1")
        s.set("B2", 9)
        assert s.get("A1") == 9  # now reads B2's new literal


# ---------------------------------------------------------------- S3: R17 out-of-grid


class TestS3OutOfGridReplacement:
    def test_column_shift_out_of_grid_becomes_ref_error(self):
        _, s = fresh()
        s.set("Z1", 3)
        s.set("A1", "=Z1")
        s.copy("A1", "B1")  # Z -> beyond Z
        assert s.get("B1") == "#REF!"

    def test_row_shift_out_of_grid_becomes_ref_error(self):
        _, s = fresh()
        s.set("A1", 3)
        s.set("A2", "=A1")
        s.copy("A2", "A1")  # row 1 -> row 0
        assert s.get("A1") == "#REF!"

    def test_row_99_shift_out_of_grid(self):
        _, s = fresh()
        s.set("A99", 3)
        s.set("B98", "=A99")
        s.copy("B98", "B99")  # row 99 -> 100
        assert s.get("B99") == "#REF!"

    def test_range_endpoint_out_replaces_whole_range(self):
        _, s = fresh()
        s.set("Y1", 1)
        s.set("Z2", 2)
        s.set("C1", "=SUM(Y1:Z2)")
        s.copy("C1", "D1")  # Z -> out: whole range -> #REF!
        assert s.get("C1") == 3
        assert s.get("D1") == "#REF!"

    def test_pinned_column_is_protected_from_replacement(self):
        _, s = fresh()
        s.set("Z1", 3)
        s.set("A1", "=$Z1")
        s.copy("A1", "B1")  # col pinned: stays $Z1
        assert s.get("B1") == 3

    def test_pinned_row_is_protected_from_replacement(self):
        _, s = fresh()
        s.set("A99", 3)
        s.set("B98", "=A$99")
        s.copy("B98", "B99")
        assert s.get("B99") == 3

    def test_replacement_swallows_dollar_on_other_component(self):
        _, s = fresh()
        s.set("Z1", 3)
        s.set("A1", "=Z$1")
        s.copy("A1", "B1")  # Z shifts out; whole token incl $1 -> #REF!
        assert s.get("B1") == "#REF!"

    def test_surrounding_expression_preserved_around_replacement(self):
        _, s = fresh()
        s.set("A1", "=Z1+1")
        s.copy("A1", "B1")  # -> "=#REF!+1"
        assert s.get("B1") == "#REF!"


# ---------------------------------------------------------------- S4: R17 non-grid REFs verbatim


class TestS4NonGridRefsKeptVerbatim:
    def test_a0_is_not_shifted_into_the_grid(self):
        _, s = fresh()
        s.set("A1", 42)
        s.set("C1", "=A0")
        s.copy("C1", "C2")  # drow=+1: a wrong shift would give =A1 -> 42
        assert s.get("C2") == "#REF!"

    def test_leading_zero_ref_is_not_shifted(self):
        _, s = fresh()
        s.set("C7", 9)
        s.set("C3", "=B07")
        s.copy("C3", "D3")  # dcol=+1: a wrong shift would give =C7 -> 9
        assert s.get("D3") == "#REF!"

    def test_out_of_range_row_ref_kept(self):
        _, s = fresh()
        s.set("C1", "=A100")
        s.copy("C1", "D2")
        assert s.get("D2") == "#REF!"


# ---------------------------------------------------------------- S5: R17 preservation (cross-cut G2/G5/R18)


class TestS5CopyPreservesNonRefText:
    def test_name_token_embedding_ref_shape_is_never_touched(self):
        # The prior round's defect: =AA1 copied down must stay =AA1.
        _, s = fresh()
        s.set("B1", 5)
        s.define_name("AA1", "B1")
        s.set("A1", "=AA1")
        s.copy("A1", "A2")
        assert s.get("A2") == 5

    def test_name_range_arg_embedding_ref_shape_is_never_touched(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("A2", 2)
        s.define_name("DATA1", "A1:A2")
        s.set("C1", "=SUM(DATA1)")
        s.copy("C1", "D2")  # a corrupted rewrite would break the NAME
        assert s.get("D2") == 3

    def test_string_literal_contents_never_touched(self):
        _, s = fresh()
        s.set("B1", 5)
        s.set("B2", 7)
        s.set("A1", '=CONCAT("A1",B1)')
        s.copy("A1", "A2")  # "A1" is text; B1 -> B2
        assert s.get("A1") == "A15"
        assert s.get("A2") == "A17"

    def test_parse_error_formula_copied_byte_for_byte(self):
        _, s = fresh()
        s.set("A1", "=A1+")  # not derivable -> #PARSE!
        s.copy("A1", "B2")
        assert s.get("A1") == "#PARSE!"
        assert s.get("B2") == "#PARSE!"

    def test_int_tokens_are_not_shifted(self):
        _, s = fresh()
        s.set("A1", "=007+1")
        s.copy("A1", "B2")
        assert s.get("B2") == 8


# ---------------------------------------------------------------- S6: R17 #REF! token, self-copy, literals


class TestS6RefTokenAndCopyBasics:
    def test_ref_token_is_a_legal_primary(self):
        _, s = fresh()
        s.set("A1", "=#REF!")
        s.set("A2", "=#REF!+1")
        s.set("A3", "=1+#REF!")
        assert s.get("A1") == "#REF!"
        assert s.get("A2") == "#REF!"
        assert s.get("A3") == "#REF!"

    def test_ref_token_is_a_legal_range_arg(self):
        _, s = fresh()
        s.set("A1", "=SUM(#REF!)")
        s.set("A2", "=COUNT(#REF!)")
        assert s.get("A1") == "#REF!"
        assert s.get("A2") == "#REF!"

    def test_copy_to_self_is_legal_zero_shift(self):
        _, s = fresh()
        s.set("B1", 4)
        s.set("A1", "=B1+1")
        s.copy("A1", "A1")
        assert s.get("A1") == 5

    def test_copy_literals_stores_identical_values(self):
        _, s = fresh()
        s.set("A1", 42)
        s.set("A2", "hello")
        s.copy("A1", "B1")
        s.copy("A2", "B2")
        assert s.get("B1") == 42
        assert s.get("B2") == "hello"

    def test_copy_and_define_name_never_evaluate(self):
        _, s = fresh()
        s.set("A1", "=1+1")
        s.set("B1", "=2+2")
        before = s.eval_count
        s.copy("A1", "C1")
        s.define_name("FOO", "B1")
        assert s.eval_count == before == 0

    def test_copy_replaces_existing_content(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("B1", "old")
        s.copy("A1", "B1")
        assert s.get("B1") == 1


# ---------------------------------------------------------------- S7: ValueError atomicity


class TestS7ProgrammerErrors:
    def test_copy_from_empty_cell_raises_and_changes_nothing(self):
        _, s = fresh()
        s.set("B9", 3)
        with pytest.raises(ValueError):
            s.copy("A9", "B9")
        assert s.get("B9") == 3
        assert s.get("A9") is None

    def test_copy_invalid_addresses_raise(self):
        _, s = fresh()
        s.set("A1", 1)
        for bad in ["A100", "a1", "A01", "AA1", "", " A1", 5, None]:
            with pytest.raises(ValueError):
                s.copy("A1", bad)
            with pytest.raises(ValueError):
                s.copy(bad, "B1")
        assert s.get("B1") is None

    def test_define_name_invalid_names_raise(self):
        _, s = fresh()
        for bad in [
            "A1",          # REF shape
            "Z99",         # REF shape
            "SUM", "MIN", "MAX", "COUNT", "CONCAT", "LEN", "IF", "NOW",
            "X",           # too short
            "X" * 33,      # too long
            "foo",         # lowercase
            "1AB",         # starts with digit
            "A-B",         # bad char
            "",            # empty
            None, 7,       # non-str
        ]:
            with pytest.raises(ValueError):
                s.define_name(bad, "B1")

    def test_define_name_valid_edge_names_accepted(self):
        _, s = fresh()
        s.set("B1", 1)
        s.define_name("_X", "B1")          # leading underscore, 2 chars
        s.define_name("X" * 32, "B1")      # max length
        s.define_name("A_1", "B1")         # not REF shape (underscore)
        s.set("A1", "=_X+A_1")
        assert s.get("A1") == 2

    def test_define_name_invalid_targets_raise_and_keep_binding(self):
        _, s = fresh()
        s.set("B1", 5)
        s.define_name("FOO", "B1")
        for bad_target in ["B1:A1", "A2:A1", "A0", "A01", "a1", "A100",
                           "A1:B0", "", None, 3]:
            with pytest.raises(ValueError):
                s.define_name("FOO", bad_target)
        s.set("A1", "=FOO")
        assert s.get("A1") == 5  # original binding intact


# ---------------------------------------------------------------- S8: R18 resolution


class TestS8NameResolution:
    def test_undefined_name_is_name_error_in_both_positions(self):
        _, s = fresh()
        s.set("A1", "=BAZ")
        s.set("A2", "=SUM(BAZ)")
        assert s.get("A1") == "#NAME!"
        assert s.get("A2") == "#NAME!"

    def test_single_address_target_as_primary_and_range(self):
        _, s = fresh()
        s.set("B2", 9)
        s.define_name("FOO", "B2")
        s.set("A1", "=FOO")
        s.set("A2", "=SUM(FOO)")
        s.set("A3", "=FOO*2")
        assert s.get("A1") == 9
        assert s.get("A2") == 9
        assert s.get("A3") == 18

    def test_one_by_one_range_target_as_primary(self):
        _, s = fresh()
        s.set("B2", 9)
        s.define_name("FOO", "B2:B2")
        s.set("A1", "=FOO")
        assert s.get("A1") == 9

    def test_larger_target_as_primary_is_ref_error(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("B2", 2)
        s.define_name("BAR", "A1:B2")
        s.set("C1", "=BAR")
        s.set("C2", "=BAR+1")
        assert s.get("C1") == "#REF!"
        assert s.get("C2") == "#REF!"

    def test_larger_target_as_range_arg(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("B1", 2)
        s.set("A2", 3)
        s.set("B2", 4)
        s.define_name("BAR", "A1:B2")
        s.set("C1", "=SUM(BAR)")
        s.set("C2", "=MAX(BAR)")
        s.set("C3", "=COUNT(BAR)")
        assert s.get("C1") == 10
        assert s.get("C2") == 4
        assert s.get("C3") == 4

    def test_count_over_name_is_structural(self):
        _, s = fresh()
        s.set("A1", "=1/0")
        s.set("A2", "text")
        s.define_name("BAR", "A1:A3")
        s.set("C1", "=COUNT(BAR)")
        before = s.eval_count
        assert s.get("C1") == 2  # A3 empty; members not evaluated
        assert s.eval_count == before + 1  # only C1 itself

    def test_string_typed_value_through_name(self):
        _, s = fresh()
        s.set("B2", "hi")
        s.define_name("FOO", "B2")
        s.set("A1", "=FOO")
        s.set("A2", "=LEN(FOO)")
        s.set("A3", "=FOO+1")
        s.set("A4", '=FOO="hi"')
        assert s.get("A1") == "hi"
        assert s.get("A2") == 2
        assert s.get("A3") == "#TYPE!"
        assert s.get("A4") == 1

    def test_str_contribution_in_name_range_is_type_fuel(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("A2", "x")
        s.define_name("BAR", "A1:A2")
        s.set("C1", "=SUM(BAR)")
        assert s.get("C1") == "#TYPE!"

    def test_empty_single_target_contributes_zero_as_primary(self):
        _, s = fresh()
        s.define_name("FOO", "B2")
        s.set("A1", "=FOO+1")
        s.set("A2", "=SUM(FOO)")
        s.set("A3", "=MIN(FOO)")
        assert s.get("A1") == 1     # R6 single-reference context
        assert s.get("A2") == 0     # R8 empty range member: nothing
        assert s.get("A3") == "#TYPE!"  # all-empty MIN

    def test_redefinition_replaces_binding(self):
        _, s = fresh()
        s.set("B1", 1)
        s.set("B2", 2)
        s.define_name("FOO", "B1")
        s.set("A1", "=FOO")
        assert s.get("A1") == 1
        s.define_name("FOO", "B2")
        assert s.get("A1") == 2

    def test_names_are_per_sheet(self):
        wb = Workbook()
        s1 = wb.add_sheet("S1")
        s2 = wb.add_sheet("S2")
        s1.set("B1", 5)
        s1.define_name("FOO", "B1")
        s1.set("A1", "=FOO")
        s2.set("A1", "=FOO")
        assert s1.get("A1") == 5
        assert s2.get("A1") == "#NAME!"

    def test_name_binding_participates_in_cycles(self):
        _, s = fresh()
        s.define_name("SELF", "A1")
        s.set("A1", "=SELF")
        assert s.get("A1") == "#CYCLE!"


# ---------------------------------------------------------------- S9: R10 cross-cut (G4)


class TestS9EditAccounting:
    def test_define_name_is_relevant_edit_for_mentioning_cells(self):
        _, s = fresh()
        s.set("B1", 3)
        s.set("A1", "=NX_VAL")
        assert s.get("A1") == "#NAME!"
        c0 = s.eval_count
        assert s.get("A1") == "#NAME!"
        assert s.eval_count == c0  # repeat read +0

        s.define_name("NX_VAL", "B1")
        assert s.eval_count == c0
        assert s.get("A1") == 3
        assert s.eval_count == c0 + 1  # exactly the one closure formula

    def test_rebinding_identically_still_invalidates(self):
        _, s = fresh()
        s.set("B1", 3)
        s.define_name("NX_VAL", "B1")
        s.set("A1", "=NX_VAL")
        assert s.get("A1") == 3
        c0 = s.eval_count
        s.define_name("NX_VAL", "B1")  # identical binding
        assert s.get("A1") == 3
        assert s.eval_count == c0 + 1  # no comparison short-circuit

    def test_define_name_is_irrelevant_to_non_mentioning_cells(self):
        _, s = fresh()
        s.set("C1", "=1+1")
        assert s.get("C1") == 2
        c0 = s.eval_count
        s.define_name("SOME_NAME", "B1")
        assert s.get("C1") == 2
        assert s.eval_count == c0

    def test_copy_is_an_edit_at_dst(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        s.set("B2", "=$A$1+2")
        assert s.get("B1") == 2
        assert s.get("B2") == 3
        c0 = s.eval_count
        s.copy("B2", "B1")  # fully pinned: text lands unchanged at B1
        assert s.get("B1") == 3
        assert s.eval_count == c0 + 1

    def test_copy_is_irrelevant_to_cells_outside_closure(self):
        _, s = fresh()
        s.set("A1", 1)
        s.set("B1", "=A1+1")
        assert s.get("B1") == 2
        c0 = s.eval_count
        s.copy("A1", "C9")  # C9 not in B1's closure
        assert s.get("B1") == 2
        assert s.eval_count == c0
