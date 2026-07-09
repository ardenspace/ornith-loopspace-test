import re
from subcut.cue import Cue
from subcut.timecode import parse_timestamp


def parse_srt(s: str) -> list[Cue]:
    """Parse SRT text into a list of Cue objects.

    Accepts both LF and CRLF line endings. Strips \\r from all parsed fields.
    Empty or all-whitespace input returns []. Leading, inter-block, and trailing
    blank lines are ignored. Cue blocks are separated by one or more blank lines.

    Raises ValueError on malformed blocks: non-positive-integer index, missing or
    invalid time line, missing "-->" arrow, or block with no text lines.
    """
    if not s or not s.strip():
        return []

    normalized = s.replace("\r\n", "\n").replace("\r", "\n")

    blocks = re.split(r"\n\s*\n", normalized.strip())

    cues = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            raise ValueError(f"block must have at least 3 lines (index, time, text), got {len(lines)}")

        index_str = lines[0].strip()
        if not index_str.isdigit() or int(index_str) < 1:
            raise ValueError(f"index must be a positive integer, got {index_str!r}")

        time_line = lines[1].strip()
        if "-->" not in time_line:
            raise ValueError(f"time line missing '-->' separator: {time_line!r}")

        start_str, end_str = time_line.split("-->", 1)
        start_str = start_str.strip()
        end_str = end_str.strip()

        try:
            start_ms = parse_timestamp(start_str)
        except ValueError as e:
            raise ValueError(f"invalid start timestamp {start_str!r}: {e}") from None

        try:
            end_ms = parse_timestamp(end_str)
        except ValueError as e:
            raise ValueError(f"invalid end timestamp {end_str!r}: {e}") from None

        text_lines = [line.strip() for line in lines[2:]]
        if not any(text_lines):
            raise ValueError("block has no text lines")

        text = "\n".join(text_lines)

        cues.append(Cue(index=int(index_str), start=start_ms, end=end_ms, text=text))

    return cues
