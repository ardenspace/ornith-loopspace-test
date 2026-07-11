"""Tests for shift_cues and Cue."""

import pytest

from subcut import Cue, shift_cues


class TestCue:
    def test_cue_creation(self):
        c = Cue(index=1, start=1000, end=2000, text="hello")
        assert c.index == 1
        assert c.start == 1000
        assert c.end == 2000
        assert c.text == "hello"

    def test_cue_is_frozen(self):
        c = Cue(index=1, start=1000, end=2000, text="hello")
        with pytest.raises(AttributeError):
            c.start = 5000


class TestShiftCues:
    def test_positive_shift(self):
        cues = [Cue(index=1, start=1000, end=2000, text="hi")]
        result = shift_cues(cues, +500)
        assert result[0].start == 1500
        assert result[0].end == 2500

    def test_negative_shift_clamps_start(self):
        cues = [Cue(index=1, start=200, end=2000, text="hi")]
        result = shift_cues(cues, -500)
        assert result[0].start == 0
        assert result[0].end == 1500

    def test_negative_shift_clamps_end(self):
        cues = [Cue(index=1, start=100, end=200, text="hi")]
        result = shift_cues(cues, -500)
        assert result[0].start == 0
        assert result[0].end == 0

    def test_independent_clamping(self):
        cues = [Cue(index=1, start=100, end=800, text="hi")]
        result = shift_cues(cues, -200)
        assert result[0].start == 0
        assert result[0].end == 600

    def test_no_mutation_of_input_cues(self):
        cues = [Cue(index=1, start=1000, end=2000, text="hi")]
        original = cues[0]
        shift_cues(cues, 500)
        assert cues[0].start == original.start
        assert cues[0].end == original.end

    def test_no_mutation_of_input_list(self):
        cues = [Cue(index=1, start=1000, end=2000, text="hi")]
        original_id = id(cues)
        shift_cues(cues, 500)
        assert id(cues) == original_id

    def test_returns_new_list(self):
        cues = [Cue(index=1, start=1000, end=2000, text="hi")]
        result = shift_cues(cues, 500)
        assert result is not cues

    def test_empty_input(self):
        assert shift_cues([], 100) == []

    def test_multiple_cues(self):
        cues = [
            Cue(index=1, start=1000, end=2000, text="a"),
            Cue(index=2, start=3000, end=4000, text="b"),
        ]
        result = shift_cues(cues, -1500)
        assert result[0].start == 0
        assert result[0].end == 500
        assert result[1].start == 1500
        assert result[1].end == 2500
