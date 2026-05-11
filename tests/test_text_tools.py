from zebra_label_tool.text_tools import normalize_editor_text, transform_lines, wrap_lines


def test_normalize_editor_text_trims_and_keeps_internal_blank_lines():
    assert normalize_editor_text("  A  \n\n B  \n") == ("A", "", "B")


def test_normalize_editor_text_can_remove_empty_and_collapse_spaces():
    assert normalize_editor_text(" A   B \n\n C ", remove_empty=True, collapse_spaces=True) == ("A B", "C")


def test_transform_lines_uppercase_lowercase_titlecase():
    assert transform_lines(["abc", "DeF"], "uppercase") == ("ABC", "DEF")
    assert transform_lines(["ABC"], "lowercase") == ("abc",)
    assert transform_lines(["main rack"], "title_case") == ("Main Rack",)


def test_transform_lines_remove_empty():
    assert transform_lines([" A ", "", "B"], "remove_empty") == ("A", "B")


def test_wrap_lines_respects_limits():
    assert wrap_lines(["one two three four"], 7, max_lines=3) == ("one two", "three", "four")
