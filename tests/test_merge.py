from subcut.cue import Cue
from subcut.merge import merge_overlapping


def _c(index, start, end, text):
    return Cue(index=index, start=start, end=end, text=text)


def test_two_overlapping_cues_merge_into_one():
    cues = [_c(1, 0, 5000, "A"), _c(2, 3000, 8000, "B")]
    result = merge_overlapping(cues)
    assert len(result) == 1
    assert result[0].start == 0
    assert result[0].end == 8000
    assert result[0].text == "A\nB"


def test_touching_cues_stay_separate():
    cues = [_c(1, 0, 5000, "A"), _c(2, 5000, 10000, "B")]
    result = merge_overlapping(cues)
    assert len(result) == 2
    assert result[0].start == 0
    assert result[0].end == 5000
    assert result[1].start == 5000
    assert result[1].end == 10000


def test_chained_overlaps_collapse_into_single_cue():
    cues = [_c(1, 0, 5000, "A"), _c(2, 3000, 8000, "B"), _c(3, 7000, 12000, "C")]
    result = merge_overlapping(cues)
    assert len(result) == 1
    assert result[0].start == 0
    assert result[0].end == 12000
    assert result[0].text == "A\nB\nC"


def test_unsorted_input_stable_sorted_equal_start_preserves_order():
    cues = [_c(3, 5000, 6000, "C"), _c(1, 0, 1000, "A"), _c(2, 0, 2000, "B")]
    result = merge_overlapping(cues)
    assert len(result) == 2
    assert result[0].start == 0
    assert result[0].end == 2000
    assert result[0].text == "A\nB"
    assert result[0].index == 1
    assert result[1].start == 5000
    assert result[1].end == 6000
    assert result[1].text == "C"
    assert result[1].index == 3


def test_merged_cue_index_is_earliest_constituent():
    cues = [_c(5, 0, 5000, "A"), _c(3, 2000, 8000, "B")]
    result = merge_overlapping(cues)
    assert len(result) == 1
    assert result[0].index == 5


def test_merged_cue_index_ties_broken_by_input_order():
    cues = [_c(5, 0, 5000, "A"), _c(3, 0, 8000, "B")]
    result = merge_overlapping(cues)
    assert len(result) == 1
    assert result[0].index == 5


def test_input_not_mutated():
    original = [_c(1, 0, 5000, "A"), _c(2, 3000, 8000, "B")]
    result = merge_overlapping(original)
    assert len(original) == 2
    assert original[0].end == 5000
    assert original[1].start == 3000
    assert result is not original
    assert result[0] is not original[0]
    assert result[0] is not original[1]


def test_all_exports_importable_from_package_root():
    from subcut import (
        parse_timestamp,
        format_timestamp,
        shift_cues,
        parse_srt,
        merge_overlapping,
        Cue,
    )
    assert callable(parse_timestamp)
    assert callable(format_timestamp)
    assert callable(shift_cues)
    assert callable(parse_srt)
    assert callable(merge_overlapping)
    assert Cue is Cue
