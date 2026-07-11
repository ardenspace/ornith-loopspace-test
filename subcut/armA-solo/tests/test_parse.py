"""Tests for parse_srt."""

import pytest

from subcut import Cue, parse_srt


class TestParseSrt:
    def test_two_cues(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello\n"
            "\n"
            "2\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "World\n"
        )
        cues = parse_srt(srt)
        assert len(cues) == 2
        assert cues[0] == Cue(index=1, start=1000, end=4000, text="Hello")
        assert cues[1] == Cue(index=2, start=5000, end=8000, text="World")

    def test_multiline_text(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Line one\n"
            "Line two\n"
        )
        cues = parse_srt(srt)
        assert len(cues) == 1
        assert cues[0].text == "Line one\nLine two"

    def test_non_sequential_indices(self):
        srt = (
            "10\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "First\n"
            "\n"
            "10\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "Duplicate\n"
        )
        cues = parse_srt(srt)
        assert cues[0].index == 10
        assert cues[1].index == 10

    def test_crlf_input(self):
        srt = "1\r\n00:00:01,000 --> 00:00:04,000\r\nHello\r\n"
        cues = parse_srt(srt)
        assert len(cues) == 1
        assert cues[0].text == "Hello"
        assert "\r" not in cues[0].text

    def test_empty_string(self):
        assert parse_srt("") == []

    def test_whitespace_only(self):
        assert parse_srt("   \n  \n  ") == []

    def test_leading_blank_lines(self):
        srt = "\n\n1\n00:00:01,000 --> 00:00:04,000\nHello\n"
        cues = parse_srt(srt)
        assert len(cues) == 1

    def test_inter_block_blank_lines(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello\n"
            "\n"
            "\n"
            "\n"
            "2\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "World\n"
        )
        cues = parse_srt(srt)
        assert len(cues) == 2

    def test_trailing_blank_lines(self):
        srt = "1\n00:00:01,000 --> 00:00:04,000\nHello\n\n\n"
        cues = parse_srt(srt)
        assert len(cues) == 1

    def test_index_not_positive_integer_raises(self):
        srt = (
            "abc\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)

    def test_index_zero_raises(self):
        srt = (
            "0\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)

    def test_index_negative_raises(self):
        srt = (
            "-1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Hello\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)

    def test_missing_arrow_raises(self):
        srt = (
            "1\n"
            "00:00:01,000 00:00:04,000\n"
            "Hello\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)

    def test_invalid_time_raises(self):
        srt = (
            "1\n"
            "99:99:99,999 --> 00:00:04,000\n"
            "Hello\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)

    def test_no_text_lines_raises(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)

    def test_no_text_lines_followed_by_blank_raises(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "\n"
            "2\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "World\n"
        )
        with pytest.raises(ValueError):
            parse_srt(srt)
