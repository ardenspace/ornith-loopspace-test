from subcut.cue import Cue
from subcut.shift import shift_cues


def test_cue_holds_index_start_end_text():
    c = Cue(index=3, start=1000, end=2000, text="hello")
    assert c.index == 3
    assert c.start == 1000
    assert c.end == 2000
    assert c.text == "hello"


def test_shift_cues_positive_delta():
    cues = [Cue(index=0, start=1000, end=2000, text="a")]
    result = shift_cues(cues, 500)
    assert result[0].start == 1500
    assert result[0].end == 2500


def test_shift_cues_negative_delta_clamps_to_zero():
    cues = [Cue(index=0, start=200, end=500, text="a")]
    result = shift_cues(cues, -500)
    assert result[0].start == 0
    assert result[0].end == 0


def test_shift_cues_independent_clamping():
    cues = [Cue(index=0, start=200, end=800, text="a")]
    result = shift_cues(cues, -500)
    assert result[0].start == 0
    assert result[0].end == 300


def test_shift_cues_returns_new_list():
    cues = [Cue(index=0, start=1000, end=2000, text="a")]
    result = shift_cues(cues, 500)
    assert result is not cues
    assert len(result) == len(cues)


def test_shift_cues_does_not_mutate_input_cues():
    original = [Cue(index=0, start=1000, end=2000, text="a")]
    shift_cues(original, 500)
    assert original[0].start == 1000
    assert original[0].end == 2000


def test_shift_cues_does_not_mutate_input_list():
    original = [Cue(index=0, start=1000, end=2000, text="a")]
    result = shift_cues(original, 500)
    assert len(original) == 1
    assert result is not original


def test_shift_cues_empty_list():
    assert shift_cues([], 500) == []


def test_shift_cues_delta_zero():
    cues = [Cue(index=0, start=1000, end=2000, text="a")]
    result = shift_cues(cues, 0)
    assert result[0].start == 1000
    assert result[0].end == 2000
    assert result is not cues
