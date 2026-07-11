"""Cue data type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cue:
    """An SRT cue: index, start/end in ms, and text."""

    index: int
    start: int
    end: int
    text: str
