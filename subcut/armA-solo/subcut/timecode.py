"""SRT timestamp parsing and formatting."""

import re

_TS_RE = re.compile(
    r"^(?P<hours>\d{2,}):(?P<minutes>\d{2}):(?P<seconds>\d{2})[,.](?P<millis>\d{3})$"
)


def parse_timestamp(ts: str) -> int:
    """Parse an SRT timestamp "HH:MM:SS,mmm" or "HH:MM:SS.mmm" to integer ms.

    Raises ValueError on any malformed input.
    """
    if not isinstance(ts, str):
        raise ValueError(f"expected str, got {type(ts).__name__}")
    m = _TS_RE.match(ts)
    if not m:
        raise ValueError(f"malformed timestamp: {ts!r}")
    hours = int(m.group("hours"))
    minutes = int(m.group("minutes"))
    seconds = int(m.group("seconds"))
    millis = int(m.group("millis"))
    if minutes >= 60:
        raise ValueError(f"minutes out of range: {minutes}")
    if seconds >= 60:
        raise ValueError(f"seconds out of range: {seconds}")
    return hours * 3600000 + minutes * 60000 + seconds * 1000 + millis


def format_timestamp(ms: int) -> str:
    """Format a non-negative integer millisecond value as 'HH:MM:SS,mmm'.

    Raises ValueError on negative or non-integer input.
    """
    if not isinstance(ms, int) or isinstance(ms, bool):
        raise ValueError(f"expected int, got {type(ms).__name__}")
    if ms < 0:
        raise ValueError(f"negative millisecond value: {ms}")
    hours, rem = divmod(ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
