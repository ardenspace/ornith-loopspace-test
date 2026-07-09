from subcut.cue import Cue


def shift_cues(cues, delta):
    return [
        Cue(
            index=cue.index,
            start=max(0, cue.start + delta),
            end=max(0, cue.end + delta),
            text=cue.text,
        )
        for cue in cues
    ]
