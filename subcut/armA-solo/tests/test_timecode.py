"""Tests for parse_timestamp and format_timestamp."""

import pytest

from subcut import format_timestamp, parse_timestamp


class TestParseTimestamp:
    def test_basic(self):
        assert parse_timestamp("00:01:23,456") == 83456

    def test_dot_separator(self):
        assert parse_timestamp("00:01:23.456") == 83456

    def test_zero(self):
        assert parse_timestamp("00:00:00,000") == 0

    def test_hours_overflow(self):
        # 100 hours = 360000000 ms
        assert parse_timestamp("100:00:00,000") == 360000000

    def test_minutes_60_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:60:00,000")

    def test_seconds_60_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:00:60,000")

    def test_minutes_single_digit_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:1:00,000")

    def test_seconds_single_digit_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:00:1,000")

    def test_hours_single_digit_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("0:01:00,000")

    def test_millis_two_digits_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:01:23,45")

    def test_millis_four_digits_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:01:23,4567")

    def test_non_numeric_field_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:01:ab,456")

    def test_wrong_number_of_fields_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("00:01,456")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp("")

    def test_not_a_string_raises(self):
        with pytest.raises(ValueError):
            parse_timestamp(123)


class TestFormatTimestamp:
    def test_basic(self):
        assert format_timestamp(83456) == "00:01:23,456"

    def test_zero(self):
        assert format_timestamp(0) == "00:00:00,000"

    def test_roundtrip_0(self):
        assert parse_timestamp(format_timestamp(0)) == 0

    def test_roundtrip_1(self):
        assert parse_timestamp(format_timestamp(1)) == 1

    def test_roundtrip_3599999(self):
        assert parse_timestamp(format_timestamp(3599999)) == 3599999

    def test_roundtrip_over_100h(self):
        ms = 100 * 3600000 + 5 * 60000 + 30 * 1000 + 123
        assert parse_timestamp(format_timestamp(ms)) == ms

    def test_hours_zero_padded_at_least_2(self):
        assert format_timestamp(0) == "00:00:00,000"

    def test_hours_3_digits(self):
        assert format_timestamp(100 * 3600000) == "100:00:00,000"

    def test_hours_no_upper_cap(self):
        ms = 9999 * 3600000
        result = format_timestamp(ms)
        assert result.startswith("9999:")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            format_timestamp(-1)

    def test_non_integer_raises(self):
        with pytest.raises(ValueError):
            format_timestamp(1.5)

    def test_bool_raises(self):
        with pytest.raises(ValueError):
            format_timestamp(True)
