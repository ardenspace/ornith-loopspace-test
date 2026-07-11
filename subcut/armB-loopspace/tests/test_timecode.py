from subcut.timecode import parse_timestamp, format_timestamp


def test_parse_comma_separator():
    assert parse_timestamp("00:01:23,456") == 83456


def test_parse_dot_separator():
    assert parse_timestamp("00:01:23.456") == 83456


def test_format_basic():
    assert format_timestamp(83456) == "00:01:23,456"


def test_roundtrip_zero():
    assert parse_timestamp(format_timestamp(0)) == 0


def test_roundtrip_one():
    assert parse_timestamp(format_timestamp(1)) == 1


def test_roundtrip_just_under_one_hour():
    assert parse_timestamp(format_timestamp(3599999)) == 3599999


def test_roundtrip_over_100_hours():
    ms = 100 * 3600 * 1000 + 123 * 3600 + 45 * 60 * 1000 + 678
    assert parse_timestamp(format_timestamp(ms)) == ms


def test_format_hours_zero_padded_at_least_two():
    assert format_timestamp(0) == "00:00:00,000"


def test_format_hours_exceeds_100_gives_three_digits():
    ms = 123 * 3600 * 1000
    assert format_timestamp(ms) == "123:00:00,000"


def test_parse_minutes_ge_60_raises():
    try:
        parse_timestamp("00:60:00,000")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_seconds_ge_60_raises():
    try:
        parse_timestamp("00:00:60,000")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_minutes_not_two_digits_raises():
    try:
        parse_timestamp("00:1:00,000")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_seconds_not_two_digits_raises():
    try:
        parse_timestamp("00:00:1,000")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_non_numeric_field_raises():
    try:
        parse_timestamp("00:0a:00,000")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_milliseconds_not_three_digits_raises():
    try:
        parse_timestamp("00:00:00,00")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_hours_fewer_than_two_digits_raises():
    try:
        parse_timestamp("0:00:00,000")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_parse_wrong_number_of_fields_raises():
    try:
        parse_timestamp("00:00:00,000:extra")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_format_negative_raises():
    try:
        format_timestamp(-1)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_format_float_raises():
    try:
        format_timestamp(1.5)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_format_string_raises():
    try:
        format_timestamp("100")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
