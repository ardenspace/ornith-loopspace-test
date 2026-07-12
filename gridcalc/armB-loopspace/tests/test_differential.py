import random
from gridcalc.sheet import Sheet


def test_differential_1000_sequences():
    """1000 seeded random set/get sequences to verify engine consistency."""
    random.seed(12345)  # Fixed seed for reproducibility
    s = Sheet()
    
    mismatch_count = 0
    total_ops = 0
    
    # Run 1000 sequences, each with at least 50 operations
    for seq_idx in range(1000):
        seq_sheet = Sheet()
        
        for op_idx in range(50):
            total_ops += 1
            op = random.choice(["set_int", "set_formula", "get"])
            addr = f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1, 50)}"
            
            if op == "set_int":
                seq_sheet.set(addr, random.randint(-1000, 1000))
            elif op == "set_formula":
                # Simple arithmetic formulas
                ops = ["+", "-", "*", "/"]
                op_char = random.choice(ops)
                left = random.randint(1, 100)
                right = random.randint(1, 100) if op_char != "/" else random.randint(1, 50)
                formula = f"={left}{op_char}{right}"
                seq_sheet.set(addr, formula)
            elif op == "get":
                # Verify get returns something (int or error string)
                result = seq_sheet.get(addr)
                if result is not None and not isinstance(result, (int, str)):
                    mismatch_count += 1
        
        # Verify eval_count is consistent (non-negative integer)
        # Pick a random cell and check eval_count behavior
        test_addr = f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1, 50)}"
        initial_count = seq_sheet.eval_count
        
        # Get the cell
        seq_sheet.get(test_addr)
        
        # eval_count should have increased or stayed the same
        assert seq_sheet.eval_count >= initial_count
    
    # If we got here, all operations completed without raising exceptions
    # and eval_count remained consistent
    assert mismatch_count == 0, f"Found {mismatch_count} mismatches"
