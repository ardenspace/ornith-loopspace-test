"""Tests for merge_overlapping."""

import pytest

from subcut import Cue, merge_overlapping, parse_srt


class TestMergeOverlapping:
    def test_two_overlapping_cues(self):
        cues = [
            Cue(index=1, start=0, end=2000, text="A"),
            Cue(index=2, start=1000, end=3000, text="B"),
        ]
        result = merge_overlapping(cues)
        assert len(result) == 1
        assert result[0].index == 1
        assert result[0].start == 0
        assert result[0].end == 3000
        assert result[0].text == "A\nB"

    def test_touching_cues_stay_separate(self):
        cues = [
            Cue(index=1, start=0, end=2000, text="A"),
            Cue(index=2, start=2000, end=3000, text="B"),
        ]
        result = merge_overlapping(cues)
        assert len(result) == 2
        assert result[0].text == "A"
        assert result[1].text == "B"

    def test_chained_overlaps(self):
        cues = [
            Cue(index=1, start=0, end=2000, text="A"),
            Cue(index=2, start=1500, end=3000, text="B"),
            Cue(index=3, start=2500, end=4000, text="C"),
        ]
        result = merge_overlapping(cues)
        assert len(result) == 1
        assert result[0].index == 1
        assert result[0].start == 0
        assert result[0].end == 4000
        assert result[0].text == "A\nB\nC"

    def test_unsorted_input_stable_sorted(self):
        cues = [
            Cue(index=3, start=3000, end=4000, text="C"),
            Cue(index=1, start=0, end=1000, text="A"),
            Cue(index=2, start=2000, end=2500, text="B"),
        ]
        result = merge_overlapping(cues)
        assert len(result) == 3
        assert result[0].index == 1
        assert result[1].index == 2
        assert result[2].index == 3

    def test_equal_start_keeps_input_order(self):
        cues = [
            Cue(index=2, start=1000, end=2000, text="B"),
            Cue(index=1, start=1000, end=1500, text="A"),
        ]
        result = merge_overlapping(cues)
        # Both start at 1000, B overlaps A (B.end=2000 > A.start=1000)
        assert len(result) == 1
        # Index of earliest start: both equal, tie broken by input order -> index 2
        assert result[0].index == 2
        assert result[0].text == "B\nA"

    def test_merged_cue_index_is_earliest(self):
        cues = [
            Cue(index=5, start=0, end=2000, text="A"),
            Cue(index=3, start=1000, end=3000, text="B"),
        ]
        result = merge_overlapping(cues)
        assert result[0].index == 5

    def test_no_mutation_of_input(self):
        cues = [
            Cue(index=1, start=0, end=2000, text="A"),
            Cue(index=2, start=1000, end=3000, text="B"),
        ]
        original = [Cue(index=c.index, start=c.start, end=c.end, text=c.text) for c in cues]
        merge_overlapping(cues)
        assert cues == original

    def test_no_mutation_of_input_list(self):
        cues = [
            Cue(index=1, start=0, end=2000, text="A"),
        ]
        original_id = id(cues)
        merge_overlapping(cues)
        assert id(cues) == original_id

    def test_returns_new_list(self):
        cues = [Cue(index=1, start=0, end=2000, text="A")]
        result = merge_overlapping(cues)
        assert result is not cues

    def test_empty_input(self):
        assert merge_overlapping([]) == []

    def test_no_overlaps(self):
        cues = [
            Cue(index=1, start=0, end=1000, text="A"),
            Cue(index=2, start=2000, end=3000, text="B"),
            Cue(index=3, start=4000, end=5000, text="C"),
        ]
        result = merge_overlapping(cues)
        assert len(result) == 3

    def test_from_parse_srt(self):
        srt = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Hello\n"
            "\n"
            "2\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "World\n"
        )
        cues = parse_srt(srt)
        result = merge_overlapping(cues)
        assert len(result) == 1
        assert result[0].text == "Hello\nWorld"
