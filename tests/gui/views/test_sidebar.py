from core.storage.config import default_profile
from gui.views.sidebar import ProfileSummary


def test_summary_reads_the_profile_settings():
    settings = {**default_profile(), "hotkey": "F7", "interval": 0.25, "mode": "Hold", "target_key": "space"}
    summary = ProfileSummary.from_config("Gaming", settings)
    assert summary == ProfileSummary("Gaming", "F7", 0.25, "Hold", "space")


def test_a_profile_without_hotkey_shows_a_dash():
    summary = ProfileSummary.from_config("Quiet", {**default_profile(), "hotkey": ""})
    assert summary.hotkey == "-"


def test_subtitle_is_readable():
    summary = ProfileSummary("P", "F6", 0.01, "Click", "mouse_left")
    assert summary.subtitle == "Click · Left mouse · 10 ms"


def test_summaries_compare_by_value_so_unchanged_lists_are_not_rebuilt():
    assert [ProfileSummary("P", "F6", 1.0, "Click", "a")] == [ProfileSummary("P", "F6", 1.0, "Click", "a")]
