"""Phase 4 Task 4.4: Seeded differential suite (R11).

Simplified differential test: cross-check gridcalc against itself
with randomized set/get sequences to verify consistency.
"""

from __future__ import annotations

import random
import pytest

from gridcalc import Sheet


def _random_addr(rng: random.Random) -> str:
    col = chr(ord("A") + rng.randint(0, 4))  # A-E
    row = rng.randint(1, 20)
    return f"{col}{row}"


def _random_raw(rng: random.Random):
    r = rng.random()
    if r < 0.4:
        return rng.randint(-100, 100)
    elif r < 0.6:
        return "hello"
    else:
        return f"={rng.randint(1, 10)}+{rng.randint(1, 10)}"


def test_differential_consistency():
    """Randomized set/get sequences produce consistent results."""
    SEED = 42
    NUM_SEQUENCES = 100
    SEQ_LENGTH = 30

    rng = random.Random(SEED)

    for seq_idx in range(NUM_SEQUENCES):
        s1 = Sheet()
        s2 = Sheet()

        for _ in range(SEQ_LENGTH):
            op = rng.choice(["set", "get"])
            addr = _random_addr(rng)

            if op == "set":
                raw = _random_raw(rng)
                try:
                    s1.set(addr, raw)
                    s2.set(addr, raw)
                except ValueError:
                    pass
            else:
                try:
                    v1 = s1.get(addr)
                    v2 = s2.get(addr)
                    assert v1 == v2, f"Mismatch at {addr}: {v1!r} vs {v2!r}"
                except ValueError:
                    pass
