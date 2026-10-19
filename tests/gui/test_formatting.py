import pytest

from gui.formatting import clicks_text, clip, format_duration, format_interval, format_number, key_label


@pytest.mark.parametrize("seconds, text", [
    (0, "0 s"), (9.9, "9 s"), (59.9, "59 s"), (60, "1:00"), (75, "1:15"),
    (3599, "59:59"), (3600, "1:00:00"), (3725, "1:02:05"),
])
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text


@pytest.mark.parametrize("count, text", [(0, "0 clicks"), (1, "1 click"), (2, "2 clicks"), (1234567, "1,234,567 clicks")])
def test_clicks_text(count, text):
    assert clicks_text(count) == text


@pytest.mark.parametrize("value, text", [
    (100.0, "100"), (0.01, "0.01"), (2.5, "2.5"), (0, "0"), (1_000_000.0, "1000000"), (123456.5, "123456.5"),
])
def test_format_number_drops_a_useless_decimal_point(value, text):
    assert format_number(value) == text


@pytest.mark.parametrize("seconds, text", [(0.01, "10 ms"), (0.001, "1 ms"), (0.5, "500 ms"), (1, "1 s"), (2.5, "2.5 s")])
def test_format_interval(seconds, text):
    assert format_interval(seconds) == text


@pytest.mark.parametrize("key, text", [
    ("mouse_left", "Left mouse"), ("mouse_middle", "Middle mouse"), ("a", "A"), ("space", "Space"), ("up", "Up"),
])
def test_key_label(key, text):
    assert key_label(key) == text


def test_clip_leaves_short_text_alone():
    assert clip("hello", 10) == "hello"
    assert clip("x" * 10, 10) == "x" * 10


def test_clip_shortens_long_text_to_the_limit():
    clipped = clip("x" * 20, 10)
    assert clipped == "x" * 9 + "…"
    assert len(clipped) == 10
