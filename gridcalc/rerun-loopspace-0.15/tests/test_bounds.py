"""Task 4.3: Bounds hardening per R12."""
import pytest
from gridcalc import Sheet


class TestDepthBounds:
    """Within-bounds evaluations never raise for depth per R12."""

    def test_32_deep_nested_parens(self):
        """32-deep nested parentheses parse and evaluate without raising."""
        s = Sheet()
        # 32 open parens, then 1, then 32 close parens
        formula = "(" * 32 + "1" + ")" * 32
        s.set("A1", "=" + formula)
        # set never evaluates, so this should succeed
        assert s.get("A1") == 1

    def test_510_deep_unary_minus_tower(self):
        """~510-deep unary-minus tower inside 512 chars parses and evaluates."""
        s = Sheet()
        # Each unary minus is 1 char, so 510 minuses + "1" = 511 chars
        formula = "-" * 510 + "1"
        assert len(formula) == 511  # Within 512-char bound
        s.set("A1", "=" + formula)
        # 510 minuses → positive 1 (even number of negatives)
        assert s.get("A1") == 1

    def test_512_char_formula(self):
        """A 512-char formula (max allowed) completes without raising."""
        s = Sheet()
        # Build a 512-char formula: "1+" repeated 255 times + "1" = 1+1+1+...+1 (256 ones)
        # "1+" is 2 chars, so 255*2 + 1 = 511 chars. Need one more char.
        formula = ("1+" * 255) + "10"
        assert len(formula) == 512
        s.set("A1", "=" + formula)
        # 255 additions of 1, plus 10 at the end = 255 + 10 = 265
        assert s.get("A1") == 265


class TestMagnitudeBound:
    """Magnitude bound: intermediates and results at or below |2**63 - 1| complete without raising."""

    def test_large_multiplication_within_bound(self):
        """Multiplication peaking near 2**63 - 1 completes without raising."""
        s = Sheet()
        # (2**31) * (2**31) = 2**62, which is within bound
        s.set("A1", 2**31)
        s.set("B1", 2**31)
        s.set("C1", "=A1*B1")
        assert s.get("C1") == 2**62

    def test_addition_near_bound(self):
        """Addition near 2**63 - 1 completes without raising."""
        s = Sheet()
        half = (2**63 - 1) // 2
        s.set("A1", half)
        s.set("B1", half)
        s.set("C1", "=A1+B1")
        # Should not exceed 2**63 - 1
        result = s.get("C1")
        assert result <= 2**63 - 1

    def test_division_large_numbers(self):
        """Division of large numbers within bound completes."""
        s = Sheet()
        s.set("A1", 2**62)
        s.set("B1", 2)
        s.set("C1", "=A1/B1")
        assert s.get("C1") == 2**61


class TestConfinement:
    """Confinement: >512-char formula in unrelated cell doesn't affect within-bounds gets."""

    def test_out_of_bounds_formula_doesnt_affect_other_cells(self):
        """A >512-char formula in one cell doesn't break gets on other cells."""
        s = Sheet()
        # Create a >512-char formula (out of bounds)
        # This will be #PARSE! or cause issues, but should not affect other cells
        bad_formula = ("1+" * 300) + "1"  # 601 chars, exceeds 512
        s.set("A1", "=" + bad_formula)
        # A1 might be #PARSE! or might raise on get — that's OK
        # But B1 should still work fine
        s.set("B1", 42)
        s.set("C1", "=B1+1")
        assert s.get("C1") == 43

    def test_set_always_succeeds(self):
        """set() never evaluates, so it always succeeds per R2."""
        s = Sheet()
        # Even with a nonsensical formula, set should succeed
        s.set("A1", "=this is garbage formula text !!!")
        assert s.get("A1") == "#PARSE!"

    def test_within_bounds_gets_keep_guarantees(self):
        """Within-bounds gets keep all guarantees even with out-of-bounds formulas elsewhere."""
        s = Sheet()
        # Out-of-bounds formula elsewhere
        bad = ("=1+" * 300) + "1"
        s.set("Z99", bad)
        # Within-bounds operations should work fine
        s.set("A1", 10)
        s.set("B1", "=A1*2")
        assert s.get("B1") == 20
        assert s.eval_count == 1


class TestR12Chain:
    """256-formula-cell reference chain per R12."""

    def test_256_cell_chain(self):
        """A 256-formula-cell reference chain evaluates without raising."""
        s = Sheet()
        # Create 256 cells in a chain: A1, A2, ..., A99, B1, B2, ..., B99, C1, ..., C58
        cells = []
        # Column A: rows 1-99
        for row in range(1, 100):
            cells.append(f"A{row}")
        # Column B: rows 1-99
        for row in range(1, 100):
            cells.append(f"B{row}")
        # Column C: rows 1-58
        for row in range(1, 59):
            cells.append(f"C{row}")
        assert len(cells) == 256

        # Set A1 to 1
        s.set(cells[0], 1)
        # Chain: each cell references the previous one
        for i in range(1, 256):
            s.set(cells[i], f"={cells[i-1]}+1")

        # Get the last cell
        result = s.get(cells[-1])
        # Should be 256 (A1=1, then 255 increments of +1)
        assert result == 256
