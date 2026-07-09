from subcut import parse_srt, Cue


def test_two_cues_parsed_correctly():
    srt = "1\n00:00:01,000 --> 00:00:04,000\nHello\n\n2\n00:00:05,000 --> 00:00:08,000\nWorld"
    result = parse_srt(srt)
    assert len(result) == 2
    assert result[0] == Cue(index=1, start=1000, end=4000, text="Hello")
    assert result[1] == Cue(index=2, start=5000, end=8000, text="World")


def test_multiline_text_preserved():
    srt = "1\n00:00:01,000 --> 00:00:04,000\nLine 1\nLine 2\nLine 3"
    result = parse_srt(srt)
    assert len(result) == 1
    assert result[0].text == "Line 1\nLine 2\nLine 3"


def test_non_sequential_indices_preserved():
    srt = "5\n00:00:01,000 --> 00:00:04,000\nFirst\n\n5\n00:00:05,000 --> 00:00:08,000\nDuplicate"
    result = parse_srt(srt)
    assert len(result) == 2
    assert result[0].index == 5
    assert result[1].index == 5


def test_crlf_parses_identically_to_lf():
    srt_lf = "1\n00:00:01,000 --> 00:00:04,000\nHello"
    srt_crlf = "1\r\n00:00:01,000 --> 00:00:04,000\r\nHello"
    result_lf = parse_srt(srt_lf)
    result_crlf = parse_srt(srt_crlf)
    assert result_lf == result_crlf
    assert "\r" not in result_crlf[0].text


def test_empty_string_returns_empty_list():
    assert parse_srt("") == []


def test_whitespace_only_returns_empty_list():
    assert parse_srt("   \n  \n  ") == []


def test_leading_trailing_blank_lines_ignored():
    srt = "\n\n1\n00:00:01,000 --> 00:00:04,000\nHello\n\n"
    result = parse_srt(srt)
    assert len(result) == 1
    assert result[0].text == "Hello"


def test_inter_block_blank_lines_ignored():
    srt = "1\n00:00:01,000 --> 00:00:04,000\nHello\n\n\n\n2\n00:00:05,000 --> 00:00:08,000\nWorld"
    result = parse_srt(srt)
    assert len(result) == 2


def test_value_error_non_integer_index():
    srt = "abc\n00:00:01,000 --> 00:00:04,000\nHello"
    try:
        parse_srt(srt)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_value_error_invalid_time_line():
    srt = "1\ninvalid time\nHello"
    try:
        parse_srt(srt)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_value_error_missing_arrow():
    srt = "1\n00:00:01,000 00:00:04,000\nHello"
    try:
        parse_srt(srt)
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_value_error_block_with_no_text():
    srt = "1\n00:00:01,000 --> 00:00:04,000"
    try:
        parse_srt(srt)
        assert False, "Expected ValueError"
    except ValueError:
        pass
