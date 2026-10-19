import pytest

from core.constants import FAILSAFE_CORNERS, FAILSAFE_OFF
from core.engine.failsafe import corner_hit

WIDTH, HEIGHT = 1920, 1080

CORNER_POINTS = {
    "Top-left": (0, 0),
    "Top-right": (WIDTH - 1, 0),
    "Bottom-left": (0, HEIGHT - 1),
    "Bottom-right": (WIDTH - 1, HEIGHT - 1),
}


@pytest.mark.parametrize("corner", FAILSAFE_CORNERS)
def test_each_corner_is_detected(corner):
    x, y = CORNER_POINTS[corner]
    assert corner_hit(corner, x, y, WIDTH, HEIGHT)


@pytest.mark.parametrize("corner", FAILSAFE_CORNERS)
def test_only_the_chosen_corner_matches(corner):
    for other, (x, y) in CORNER_POINTS.items():
        assert corner_hit(corner, x, y, WIDTH, HEIGHT) == (other == corner)


@pytest.mark.parametrize("corner", FAILSAFE_CORNERS)
def test_the_middle_of_the_screen_never_matches(corner):
    assert not corner_hit(corner, WIDTH // 2, HEIGHT // 2, WIDTH, HEIGHT)


@pytest.mark.parametrize("corner", FAILSAFE_CORNERS)
def test_the_middle_of_an_edge_is_not_a_corner(corner):
    assert not corner_hit(corner, WIDTH // 2, 0, WIDTH, HEIGHT)
    assert not corner_hit(corner, 0, HEIGHT // 2, WIDTH, HEIGHT)
    assert not corner_hit(corner, WIDTH - 1, HEIGHT // 2, WIDTH, HEIGHT)
    assert not corner_hit(corner, WIDTH // 2, HEIGHT - 1, WIDTH, HEIGHT)


def test_a_couple_of_pixels_of_slack_count_as_the_corner():
    assert corner_hit("Top-left", 2, 2, WIDTH, HEIGHT)
    assert not corner_hit("Top-left", 3, 2, WIDTH, HEIGHT)
    assert not corner_hit("Top-left", 2, 3, WIDTH, HEIGHT)
    assert corner_hit("Bottom-right", WIDTH - 3, HEIGHT - 3, WIDTH, HEIGHT)
    assert not corner_hit("Bottom-right", WIDTH - 4, HEIGHT - 3, WIDTH, HEIGHT)


def test_a_custom_margin_is_respected():
    assert corner_hit("Top-left", 10, 10, WIDTH, HEIGHT, margin=10)
    assert not corner_hit("Top-left", 11, 10, WIDTH, HEIGHT, margin=10)


def test_another_monitor_to_the_left_does_not_trigger_the_top_left_corner():
    assert not corner_hit("Top-left", -1500, 0, WIDTH, HEIGHT)
    assert not corner_hit("Top-left", -3, 0, WIDTH, HEIGHT)


def test_pointer_past_the_primary_screen_is_not_the_corner():
    assert not corner_hit("Bottom-right", WIDTH + 500, HEIGHT + 500, WIDTH, HEIGHT)
    assert not corner_hit("Top-right", WIDTH + 500, 0, WIDTH, HEIGHT)


@pytest.mark.parametrize("corner", [FAILSAFE_OFF, "Middle", "", "top-left"])
def test_off_or_unknown_choices_never_match(corner):
    for x, y in CORNER_POINTS.values():
        assert not corner_hit(corner, x, y, WIDTH, HEIGHT)