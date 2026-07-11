# Spec: subcut
version: 1
status: approved

## Overview
subcut is a small, disposable pure-function Python library for SRT subtitle
timecode manipulation. Its real purpose is to validate that the loopspace
pipeline runs correctly on the opencode/ornith local-model backend (Path A);
the library itself is throwaway. It provides four deterministic pure
functions built under TDD with pytest, each with machine-checkable behavior.

## Goals
- Deterministic pure functions for: timestamp<->ms conversion, cue
  time-shifting, SRT parsing, and overlapping-cue merging.
- Every behavior expressible as a machine-checkable pytest assertion, so the
  verifier can judge pass/fail mechanically.
- Zero external dependencies beyond pytest.
- Produce a clean signal for whether ornith (35B Q5) holds loopspace's
  verification bar.

## Non-Goals
- No CLI, no UI, no file/network I/O — strings in, values out.
- No API polish, packaging, or real-world robustness (disposable fixture).
- No subtitle formats other than SRT.
- No performance targets.

## Company Lens
Purpose is harness validation, not a product. Success = the loopspace loop
completes on ornith with honest verification and yields correct pure
functions. Concretely: the run reaches `complete` with every pytest case
green and no skipped or xfail assertions. Investment is deliberately minimal — edge cases exist only to
generate clean verification signal, not to harden a real tool. Scope: one
short run, one phase, ~4 tasks. Cost: local model only. Disposable — safe to
halt or fail.

## User Lens
No human end-user. The consumer is the pytest suite. No UX, adoption, or
convenience concerns. (Lens compressed on the human's own framing: pure
harness validation, throwaway, "API 다듬기 신경 안 씀 … 순수함수 몇 개, 버림".)

## Engineer Lens
- Runtime: Python 3.10+; pytest is the only dependency.
- Purity: every function is pure and deterministic — no I/O, no globals, no
  mutation of arguments.
- Error handling: STRICT. Malformed input (invalid timestamp, malformed SRT
  block) raises `ValueError`; tests assert via `pytest.raises(ValueError)`.
- Security: no eval, no untrusted execution, no file/network access. Inputs
  are plain in-memory strings; the only theoretical concern is unbounded input
  size (memory / super-linear merge on adversarial overlaps), explicitly out
  of scope for this disposable fixture.
- Testing: TDD, table-driven pytest cases per function, covering edge cases
  (comma vs dot separator, 3-digit millisecond enforcement, minutes/seconds
  >= 60, clamp-at-zero, LF vs CRLF, empty/all-whitespace input, touching vs
  overlapping cues, and chained/transitive merges).
- Over-engineering boundary: no config, no class hierarchy beyond a simple
  `Cue` holder (namedtuple/dataclass); no generalization past the four
  functions.

## Designer Lens
Not applicable: no UI surface.

## Requirements
- R1: `parse_timestamp` converts an SRT timestamp "HH:MM:SS,mmm" to integer
  milliseconds, accepting both "," and "." as the millisecond separator. The
  hours field may be 2 or more digits; minutes and seconds are exactly 2
  digits; milliseconds are exactly 3 digits.
- R2: `format_timestamp` converts a non-negative integer millisecond value to
  a canonical "HH:MM:SS,mmm" string — comma separator, hours zero-padded to
  at least 2 digits with no upper cap, minutes/seconds 2 digits, milliseconds
  3 digits — such that `parse_timestamp(format_timestamp(ms)) == ms` for
  every `ms >= 0`. It raises `ValueError` on a negative or non-integer
  argument.
- R3: `parse_timestamp` raises `ValueError` on malformed input — hours fewer
  than 2 digits, minutes or seconds not exactly 2 digits, non-numeric fields,
  minutes or seconds >= 60, a milliseconds field that is not exactly 3 digits,
  or the wrong number of colon/comma-separated fields.
- R4: `shift_cues` shifts each cue's start and end by a signed integer
  millisecond delta; any resulting time below zero is clamped to zero (start
  and end are clamped independently).
- R5: `parse_srt` parses SRT text into a list of `Cue`s in file order, each
  with index (int), start (ms), end (ms), and text (str, multi-line
  preserved). It accepts both LF and CRLF line endings and strips `\r` from
  parsed fields and text. Empty or all-whitespace input returns `[]`; leading,
  inter-block, and trailing blank lines are ignored. Cue blocks are separated
  by one or more blank lines; within a block the first line is the index, the
  second is the time line, and every remaining line up to the next blank line
  or EOF is cue text (joined by newline). Cue indices are preserved as written
  and are not required to be sequential or unique.
- R6: `parse_srt` raises `ValueError` on a malformed SRT block — an index line
  that does not parse as a positive integer, a missing or invalid time line, a
  missing "-->" arrow, or a block with no text lines.
- R7: `merge_overlapping` performs a stable sort of cues by start ascending
  (equal-start cues keep input order), then merges cues that strictly overlap
  (earlier end > later start) into a cue spanning [min start, max end] with
  texts joined by newline, iterating until stable so that chained/transitive
  overlaps collapse into a single cue; a merged cue takes the index of its
  earliest constituent cue. Cues that merely touch (earlier end == later
  start) stay separate.
- R8: All functions are pure — they never mutate their arguments and return
  identical output for identical input.

## Approval
Approved by human on 2026-07-10. Open non-blocking issues at approval:
- R7: merge_overlapping is potentially super-linear on adversarially
  overlapping large inputs; accepted out of scope for this disposable fixture.
