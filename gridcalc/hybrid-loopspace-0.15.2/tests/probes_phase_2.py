from gridcalc import Sheet


def test_string_literal_error_text_is_type_error_before_later_division_error():
    """R5 lines 149-157; R6 lines 158-163; spec lines 32-37."""
    sheet = Sheet()
    sheet.set("A1", "#DIV!")
    sheet.set("B1", "=A1+1/0")

    assert sheet.get("B1") == "#TYPE!"


def test_reference_values_feed_left_associative_comparison_and_truncating_division():
    """R3 lines 116-125; R4 lines 146-148; R6 lines 158-163."""
    sheet = Sheet()
    sheet.set("A1", 7)
    sheet.set("B1", -2)
    sheet.set("C1", "=A1/B1<-3=0")

    assert sheet.get("C1") == 1


def test_invalid_reference_token_evaluates_to_ref_before_later_type_error():
    """R5 lines 149-157; R6 lines 158-166; R3 lines 131-132."""
    sheet = Sheet()
    sheet.set("A1", "text")
    sheet.set("B1", "=A100+A1")

    assert sheet.get("B1") == "#REF!"
