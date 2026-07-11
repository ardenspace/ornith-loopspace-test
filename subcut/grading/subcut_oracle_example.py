"""Held-out acceptance oracle for subcut. Authored independently from the spec.
Neither arm (loopspace-B nor solo-A) sees this file. Run with the target repo
root on PYTHONPATH:  PYTHONPATH=<repo> python3 -m pytest test_oracle.py -q
Grades correctness against the spec's public API from the package root."""
import pytest
from subcut import (
    parse_timestamp,
    format_timestamp,
    shift_cues,
    parse_srt,
    merge_overlapping,
    Cue,
)


def C(index, start, end, text):
    return Cue(index=index, start=start, end=end, text=text)


# ---------- parse_timestamp / format_timestamp (R1, R2, R3) ----------

def test_parse_comma():
    assert parse_timestamp("00:01:23,456") == 83456


def test_parse_dot():
    assert parse_timestamp("00:01:23.456") == 83456


def test_parse_three_digit_hours():
    assert parse_timestamp("123:00:00,000") == 123 * 3600 * 1000


def test_format_basic():
    assert format_timestamp(83456) == "00:01:23,456"


def test_format_hours_over_100_three_digits():
    assert format_timestamp(123 * 3600 * 1000) == "123:00:00,000"


@pytest.mark.parametrize("ms", [0, 1, 999, 1000, 3599999, 3600000,
                                100 * 3600 * 1000 + 12345,
                                359999999, 500 * 3600 * 1000 + 42])
def test_roundtrip(ms):
    assert parse_timestamp(format_timestamp(ms)) == ms


@pytest.mark.parametrize("bad", [
    "00:60:00,000",   # minutes >= 60
    "00:00:60,000",   # seconds >= 60
    "00:1:00,000",    # minutes not 2 digits
    "00:00:1,000",    # seconds not 2 digits
    "0:00:00,000",    # hours fewer than 2 digits
    "00:00:00,00",    # ms not exactly 3 digits (too few)
    "00:00:00,0000",  # ms not exactly 3 digits (too many)
    "00:0a:00,000",   # non-numeric field
    "00:00:00,000:9", # wrong number of fields
    "0000,000",       # missing colons entirely
])
def test_parse_malformed_raises(bad):
    with pytest.raises(ValueError):
        parse_timestamp(bad)


@pytest.mark.parametrize("bad", [-1, -1000, 1.5, "100", None, True])
def test_format_bad_arg_raises(bad):
    with pytest.raises(ValueError):
        format_timestamp(bad)


# ---------- shift_cues (R4, R8) — independent clamp is the trap class ----------

def test_shift_positive():
    r = shift_cues([C(1, 1000, 2000, "a")], 500)
    assert (r[0].start, r[0].end) == (1500, 2500)


def test_shift_negative_clamps_BOTH_start_and_end():
    # both shifted times go below zero -> both clamp to 0 (independent clamp)
    r = shift_cues([C(1, 300, 800, "a")], -1000)
    assert r[0].start == 0
    assert r[0].end == 0          # the planted-trap dimension


def test_shift_returns_new_list_no_mutation():
    original = [C(1, 1000, 2000, "a")]
    r = shift_cues(original, 100)
    assert r is not original
    assert original[0].start == 1000 and original[0].end == 2000


# ---------- parse_srt (R5, R6) ----------

_TWO = "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:03,000 --> 00:00:04,500\nWorld\nsecond line"


def test_parse_two_cues_file_order():
    cues = parse_srt(_TWO)
    assert len(cues) == 2
    assert cues[0].index == 1 and cues[0].start == 1000 and cues[0].end == 2000
    assert cues[0].text == "Hello"
    assert cues[1].index == 2 and cues[1].start == 3000 and cues[1].end == 4500


def test_parse_multiline_text_preserved():
    cues = parse_srt(_TWO)
    assert cues[1].text == "World\nsecond line"


def test_parse_crlf_equals_lf_and_no_cr():
    lf = parse_srt(_TWO)
    crlf = parse_srt(_TWO.replace("\n", "\r\n"))
    assert [ (c.index, c.start, c.end, c.text) for c in crlf ] == \
           [ (c.index, c.start, c.end, c.text) for c in lf ]
    assert all("\r" not in c.text for c in crlf)


@pytest.mark.parametrize("blank", ["", "   ", "\n\n", "  \n \t\n "])
def test_parse_empty_or_whitespace_returns_empty(blank):
    assert parse_srt(blank) == []


def test_parse_surrounding_blank_lines_ignored():
    padded = "\n\n" + _TWO + "\n\n\n"
    assert len(parse_srt(padded)) == 2


def test_parse_non_sequential_duplicate_indices_preserved():
    s = "5\n00:00:01,000 --> 00:00:02,000\nA\n\n2\n00:00:03,000 --> 00:00:04,000\nB\n\n2\n00:00:05,000 --> 00:00:06,000\nC"
    cues = parse_srt(s)
    assert [c.index for c in cues] == [5, 2, 2]


@pytest.mark.parametrize("bad", [
    "x\n00:00:01,000 --> 00:00:02,000\nHi",          # index not a positive integer
    "0\n00:00:01,000 --> 00:00:02,000\nHi",          # index not positive
    "1\n00:00:01,000 00:00:02,000\nHi",              # missing arrow
    "1\nnot-a-time --> also-bad\nHi",                # invalid time line
    "1\n00:00:01,000 --> 00:00:02,000",              # no text lines
])
def test_parse_malformed_block_raises(bad):
    with pytest.raises(ValueError):
        parse_srt(bad)


# ---------- merge_overlapping (R7, R8) ----------

def test_merge_strict_overlap():
    r = merge_overlapping([C(1, 0, 2000, "a"), C(2, 1000, 3000, "b")])
    assert len(r) == 1
    assert r[0].start == 0 and r[0].end == 3000 and r[0].text == "a\nb"


def test_merge_touching_stays_separate():
    r = merge_overlapping([C(1, 0, 1000, "a"), C(2, 1000, 2000, "b")])
    assert len(r) == 2


def test_merge_transitive_collapse():
    r = merge_overlapping([C(1, 0, 1500, "a"), C(2, 1000, 2500, "b"), C(3, 2000, 3000, "c")])
    assert len(r) == 1
    assert r[0].start == 0 and r[0].end == 3000 and r[0].text == "a\nb\nc"


def test_merge_unsorted_stable_and_text_order():
    r = merge_overlapping([C(2, 1000, 3000, "b"), C(1, 0, 2000, "a")])
    assert len(r) == 1
    assert r[0].start == 0 and r[0].end == 3000 and r[0].text == "a\nb"


def test_merge_index_is_smallest_start():
    r = merge_overlapping([C(9, 0, 2000, "a"), C(4, 1000, 3000, "b")])
    assert r[0].index == 9  # earliest-start cue's index


def test_merge_no_mutation():
    original = [C(1, 0, 2000, "a"), C(2, 1000, 3000, "b")]
    snapshot = [(c.index, c.start, c.end, c.text) for c in original]
    merge_overlapping(original)
    assert [(c.index, c.start, c.end, c.text) for c in original] == snapshot
