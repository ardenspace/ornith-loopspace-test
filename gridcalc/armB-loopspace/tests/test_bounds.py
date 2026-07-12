from gridcalc.sheet import Sheet


class TestR12Bounds:
    """R12: Size, depth, and magnitude bounds."""

    def test_32_deep_nested_parens(self):
        """32-deep nested parentheses should parse and evaluate without raising."""
        s = Sheet()
        # Build a formula with 32 levels of nested parens: (((...)))
        formula = "(" * 32 + "1" + ")" * 32
        s.set("A1", "=" + formula)
        # Should evaluate to 1
        assert s.get("A1") == 1

    def test_510_deep_unary_minus_tower(self):
        """~510-deep unary-minus tower inside 512 chars should parse and evaluate."""
        s = Sheet()
        # Build a formula with ~510 unary minuses: ------...1
        # Each minus is 1 char, so 510 minuses + "1" = 511 chars, plus "=" = 512
        formula = "-" * 510 + "1"
        s.set("A1", "=" + formula)
        # 510 minuses: even number, so result is 1
        assert s.get("A1") == 1

    def test_256_cell_reference_chain(self):
        """256-formula-cell reference chain should evaluate without raising."""
        s = Sheet()
        # Create a chain using A1-A99, B1-B99, C1-C58 (99+99+58=256 cells)
        cells = []
        for col in ['A', 'B', 'C']:
            if col == 'A':
                max_row = 99
            elif col == 'B':
                max_row = 99
            else:
                max_row = 58
            for row in range(1, max_row + 1):
                cells.append(f"{col}{row}")
        
        # Verify we have 256 cells
        assert len(cells) == 256
        
        # Set the first cell
        s.set(cells[0], 1)
        
        # Set subsequent cells as =prev+1
        for i in range(1, 256):
            s.set(cells[i], f"={cells[i-1]}+1")
        
        # Get the last cell - should be 256
        result = s.get(cells[255])
        assert result == 256

    def test_magnitude_bound_near_max_int(self):
        """Arithmetic with intermediates up to |2**63 - 1| should complete without raising."""
        s = Sheet()
        max_int = 2**63 - 1
        # Set a cell to max_int
        s.set("A1", max_int)
        # Add 0 to it (should not overflow)
        s.set("B1", "=A1+0")
        assert s.get("B1") == max_int

    def test_confinement_large_formula_unrelated_cell(self):
        """>512-char formula in unrelated cell should not affect within-bounds gets."""
        s = Sheet()
        # Create a >512-char formula in Z1 (unrelated to A1)
        # This formula is out of bounds but should not affect other cells
        large_formula = "=1+" + "1+".join(["1"] * 600)
        s.set("Z1", large_formula)
        
        # Set and get A1 normally
        s.set("A1", 42)
        assert s.get("A1") == 42
        
        # The large formula should fail to parse or evaluate, but shouldn't affect A1
        # (confinement guarantee)
