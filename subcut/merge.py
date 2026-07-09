from subcut.cue import Cue


def merge_overlapping(cues):
    """Merge strictly overlapping cues into a single cue.

    Stable-sorts cues by start ascending (equal-start preserves input order),
    then merges cues where earlier.end > later.start into a cue spanning
    [min(start), max(end)] with texts joined by newline. Chained/transitive
    overlaps collapse in a single pass. A merged cue takes the index of its
    earliest constituent cue (smallest start, ties broken by input order).
    Touching cues (earlier.end == later.start) stay separate.

    Returns a new list; input cues are not mutated.
    """
    if not cues:
        return []

    sorted_cues = sorted(cues, key=lambda c: c.start)

    merged = []
    for cue in sorted_cues:
        if merged and merged[-1].end > cue.start:
            prev = merged[-1]
            new_start = min(prev.start, cue.start)
            new_end = max(prev.end, cue.end)
            new_text = prev.text + "\n" + cue.text
            merged[-1] = Cue(index=prev.index, start=new_start, end=new_end, text=new_text)
        else:
            merged.append(cue)

    return merged
