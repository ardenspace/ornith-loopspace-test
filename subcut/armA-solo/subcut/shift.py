"""Shift cues by a signed millisecond delta."""

from __future__ import annotations

from typing import List

from .cue import Cue


def shift_cues(cues: List[Cue], delta: int) -> List[Cue]:
    """Return a new list of cues with start/end shifted by *delta*.

    Each resulting time below zero is clamped to zero independently.
    The input list and its Cue objects are not mutated.
    """
    result: List[Cue] = []
    for cue in cues:
        new_start = max(0, cue.start + delta)
        new_end = max(0, cue.end + delta)
        result.append(Cue(index=cue.index, start=new_start, end=new_end, text=cue.text))
    return result
