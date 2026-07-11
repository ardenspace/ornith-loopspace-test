"""Merge overlapping cues."""

from __future__ import annotations

from typing import List

from .cue import Cue


def merge_overlapping(cues: List[Cue]) -> List[Cue]:
    """Merge cues that strictly overlap into single cues.

    - Stable sort by start ascending; equal-start cues keep input order.
    - Two cues strictly overlap when earlier.end > later.start.
    - Touching cues (earlier.end == later.start) stay separate.
    - Chained/transitive overlaps collapse into one cue.
    - Merged cue takes the index of the earliest constituent cue (smallest
      start; ties broken by input order).
    - Texts are joined by newline.
    - Returns a new list; input is not mutated.
    """
    if not cues:
        return []

    # Stable sort by start; equal-start preserves input order (enumerate index)
    indexed = list(enumerate(cues))
    indexed.sort(key=lambda pair: (pair[1].start, pair[0]))

    merged: List[Cue] = []
    for orig_idx, cue in indexed:
        if merged and merged[-1].end > cue.start:
            # Strict overlap — merge
            prev = merged[-1]
            new_end = max(prev.end, cue.end)
            new_text = prev.text + "\n" + cue.text
            merged[-1] = Cue(index=prev.index, start=prev.start, end=new_end, text=new_text)
        else:
            merged.append(Cue(index=cue.index, start=cue.start, end=cue.end, text=cue.text))

    return merged
