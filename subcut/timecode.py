def parse_timestamp(s: str) -> int:
    """Convert an SRT timestamp string to integer milliseconds.

    Accepts "HH:MM:SS,mmm" or "HH:MM:SS.mmm". Hours must be 2+ digits,
    minutes and seconds exactly 2 digits (00-59), milliseconds exactly 3.
    Raises ValueError on any malformed input.
    """
    if not isinstance(s, str):
        raise ValueError("input must be a string")

    parts = s.split(":")
    if len(parts) != 3:
        raise ValueError(f"expected 3 colon-separated fields, got {len(parts)}")

    hours_str, minutes_str, seconds_ms_str = parts

    if len(hours_str) < 2 or not hours_str.isdigit():
        raise ValueError(f"hours must be 2+ numeric digits, got {hours_str!r}")

    if len(minutes_str) != 2 or not minutes_str.isdigit():
        raise ValueError(f"minutes must be exactly 2 numeric digits, got {minutes_str!r}")

    if "," in seconds_ms_str:
        sep = ","
    elif "." in seconds_ms_str:
        sep = "."
    else:
        raise ValueError(f"milliseconds separator must be ',' or '.', got {seconds_ms_str!r}")

    seconds_str, ms_part = seconds_ms_str.split(sep, 1)

    if len(seconds_str) != 2 or not seconds_str.isdigit():
        raise ValueError(f"seconds must be exactly 2 numeric digits, got {seconds_str!r}")

    if len(ms_part) != 3 or not ms_part.isdigit():
        raise ValueError(f"milliseconds must be exactly 3 numeric digits, got {ms_part!r}")

    hours = int(hours_str)
    minutes = int(minutes_str)
    seconds = int(seconds_str)
    milliseconds = int(ms_part)

    if minutes >= 60:
        raise ValueError(f"minutes must be < 60, got {minutes}")
    if seconds >= 60:
        raise ValueError(f"seconds must be < 60, got {seconds}")

    return hours * 3600 * 1000 + minutes * 60 * 1000 + seconds * 1000 + milliseconds


def format_timestamp(ms: int) -> str:
    """Convert a non-negative integer millisecond value to canonical SRT format.

    Returns "HH:MM:SS,mmm" with hours zero-padded to at least 2 digits (no cap),
    minutes/seconds 2 digits, milliseconds 3 digits, comma separator.
    Raises ValueError on negative or non-integer input.
    """
    if not isinstance(ms, int) or isinstance(ms, bool):
        raise ValueError(f"input must be an integer, got {type(ms).__name__}")
    if ms < 0:
        raise ValueError(f"input must be non-negative, got {ms}")

    total_seconds, millis = divmod(ms, 1000)
    total_minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(total_minutes, 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
