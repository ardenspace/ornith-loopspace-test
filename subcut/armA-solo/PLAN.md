# Plan: subcut
version: 1
status: approved

## Phase 1: subcut pure-function toolkit
Goal: a Python package `subcut` exposing its pure functions and a `Cue`
type, with a full green pytest suite.
Phase acceptance: `pytest -q` passes with every acceptance criterion below
covered by a test, no skips/xfails; parse_timestamp, format_timestamp,
shift_cues, parse_srt, merge_overlapping and the `Cue` type are all
importable from the `subcut` package root (via subcut/__init__.py); no
function mutates its arguments.

### Task 1.1: Timestamp conversion (parse_timestamp / format_timestamp)
risk: light
covers: R1, R2, R3
files: subcut/timecode.py, subcut/__init__.py, tests/test_timecode.py
acceptance:
- parse_timestamp("00:01:23,456") returns 83456
- parse_timestamp accepts a "." separator: parse_timestamp("00:01:23.456") returns 83456
- format_timestamp(83456) returns "00:01:23,456"
- round-trip parse_timestamp(format_timestamp(ms)) == ms for a table including 0, 1, 3599999, and a value exceeding 100 hours
- format_timestamp zero-pads hours to at least 2 digits with no upper cap (a >=100h value formats with 3-digit hours)
- parse_timestamp raises ValueError on: minutes >= 60, seconds >= 60, minutes or seconds not exactly 2 digits, a non-numeric field, a milliseconds field not exactly 3 digits, hours fewer than 2 digits, and the wrong number of fields
- format_timestamp raises ValueError on a negative or non-integer argument

### Task 1.2: Cue type and shift_cues
risk: light
covers: R4, R8
files: subcut/cue.py, subcut/shift.py, subcut/__init__.py, tests/test_shift.py
acceptance:
- a Cue holds index (int), start (int ms), end (int ms), and text (str)
- shift_cues([cue], +500) returns cues whose start and end are each raised by 500
- shift_cues with a negative delta clamps each resulting negative time to 0, clamping start and end independently
- shift_cues returns a new list and leaves the input cues and input list unchanged after the call

### Task 1.3: parse_srt
risk: light
covers: R5, R6
files: subcut/parse.py, subcut/__init__.py, tests/test_parse.py
acceptance:
- parse_srt of a two-cue SRT string returns 2 Cues with correct index/start/end/text in file order
- multi-line cue text is preserved, joined by newline
- non-sequential or duplicate cue indices are preserved as written (not renumbered)
- CRLF input parses identically to the LF equivalent, with no stray "\r" left in any field or text
- empty string and all-whitespace input each return []
- leading, inter-block, and trailing blank lines are ignored
- parse_srt raises ValueError on: an index line that is not a positive integer, a missing or invalid time line, a missing "-->" arrow, and a block with no text lines

### Task 1.4: merge_overlapping
risk: light
covers: R7, R8
files: subcut/merge.py, subcut/__init__.py, tests/test_merge.py
acceptance:
- two strictly overlapping cues merge into one spanning [min start, max end] with texts joined by newline
- touching cues (earlier end == later start) stay separate
- chained/transitive overlaps (A-B overlap, B-C overlap) collapse into a single cue
- unsorted input is stable-sorted by start ascending; equal-start cues keep input order in the joined text
- a merged cue takes the index of its constituent cue with the smallest start (ties broken by input order)
- merge_overlapping returns a new list and leaves the input cues unchanged
- parse_timestamp, format_timestamp, shift_cues, parse_srt, merge_overlapping and Cue are all importable from the `subcut` package root

## Re-plans
