from dataclasses import dataclass


@dataclass
class Cue:
    index: int
    start: int
    end: int
    text: str
