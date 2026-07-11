"""SRT text parser."""

from __future__ import annotations

import re
from typing import List

from .cue import Cue
from .timecode import parse_timestamp

_TIME_LINE_RE = re.compile(r"^\s*(\S+)\s*-->\s*(\S+)\s*$")


def parse_srt(text: str) -> List[Cue]:
    """Parse SRT text into a list of Cue objects.

    Accepts LF and CRLF line endings. Raises ValueError on malformed blocks.
    """
    if not isinstance(text, str):
        raise ValueError(f"expected str, got {type(text).__name__}")

    # Normalize line endings and strip
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into lines
    lines = normalized.split("\n")

    # Strip trailing empty lines
    while lines and lines[-1].strip() == "":
        lines.pop()

    if not lines:
        return []

    cues: List[Cue] = []
    i = 0

    while i < len(lines):
        # Skip blank lines
        if lines[i].strip() == "":
            i += 1
            continue

        # Expect: index line, time line, text lines (until blank or EOF)
        # Index line
        index_line = lines[i].strip()
        if not index_line:
            i += 1
            continue

        try:
            index = int(index_line)
        except ValueError:
            raise ValueError(f"index line is not a positive integer: {index_line!r}")
        if index <= 0:
            raise ValueError(f"index must be positive, got {index}")

        i += 1
        if i >= len(lines):
            raise ValueError("missing time line after index")

        # Time line
        time_line = lines[i].strip()
        m = _TIME_LINE_RE.match(time_line)
        if not m:
            raise ValueError(f"malformed time line: {time_line!r}")

        try:
            start = parse_timestamp(m.group(1))
        except ValueError:
            raise ValueError(f"invalid start timestamp: {m.group(1)!r}")
        try:
            end = parse_timestamp(m.group(2))
        except ValueError:
            raise ValueError(f"invalid end timestamp: {m.group(2)!r}")

        i += 1

        # Text lines (until blank line or EOF)
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip() != "":
            text_lines.append(lines[i])
            i += 1

        if not text_lines:
            raise ValueError("cue block has no text lines")

        text = "\n".join(text_lines)
        cues.append(Cue(index=index, start=start, end=end, text=text))

    return cues
