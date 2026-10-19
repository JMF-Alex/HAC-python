import json
import os

import pytest

from core.storage import config
from core.constants import (
    DEFAULT_INTERVAL,
    DEFAULT_JITTER,
    DEFAULT_LIMIT_VALUE,
    DEFAULT_START_DELAY,
    DEFAULT_TARGET_KEY,
    LIMIT_CLICKS,
    LIMIT_NEVER,
    LIMIT_TIME,
    MAX_INTERVAL,
    MAX_JITTER,
    MAX_LIMIT_VALUE,
    MAX_START_DELAY,
    MIN_INTERVAL,
    MIN_LIMIT_VALUE,
    MODE_CLICK,
    MODE_HOLD,
)


def write_config(data):
    with open(config.config_path(), "w", encoding="utf-8") as f:
        json.dump(data, f)


def write_legacy(data):
    with open(config.LEGACY_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def sanitized_profile(settings):
    return config._sanitize({"profiles": {"P": settings}})["profiles"]["P"]


def test_load_returns_defaults_when_no_file_exists():
    cfg = config.load_config()
    assert cfg["version"] == config.CONFIG_VERSION
    assert cfg["active_profile"] == config.DEFAULT_PROFILE_NAME
    assert cfg["profiles"] == {config.DEFAULT_PROFILE_NAME: config.default_profile()}


def test_save_then_load_roundtrip():
    cfg = {
        "version": config.CONFIG_VERSION,
        "active_profile": "Fast",
        "profiles": {
            "Fast": {**config.default_profile(), "interval": 0.05, "hotkey": "F7", "mode": MODE_HOLD, "target_key": "space"},
            "Slow": {
                **config.default_profile(), "interval": 2.0, "hotkey": "F8", "mode": MODE_CLICK,
                "target_key": "mouse_right", "jitter": 25.0, "limit_kind": LIMIT_CLICKS,
                "limit_value": 500.0, "start_delay": 3.0,
            },
        },
        "settings": {"failsafe": "Top-left", "always_on_top": True, "sound": True},
    }
    config.save_config(cfg)
    assert config.load_config() == cfg


def test_save_leaves_no_temp_file_behind():
    config.save_config(config.load_config())
    assert os.listdir(os.path.dirname(config.config_path())) == [config.CONFIG_FILENAME]


def test_save_returns_the_sanitized_config():
    saved = config.save_config({"profiles": {"A": {"interval": -1}}})
    assert saved["profiles"]["A"]["interval"] == MIN_INTERVAL


@pytest.mark.parametrize("content", ["{not json", "[]", "42", ""])
def test_unreadable_config_falls_back_to_defaults(content):
    with open(config.config_path(), "w", encoding="utf-8") as f:
        f.write(content)
    assert config.load_config()["profiles"] == {config.DEFAULT_PROFILE_NAME: config.default_profile()}


def test_migrates_v1_legacy_file_into_a_default_profile():
    write_legacy({"interval": 0.5, "hotkey": "F7", "mode": "Hold", "target_key": "left"})
    cfg = config.load_config()
    assert cfg["active_profile"] == config.DEFAULT_PROFILE_NAME
    assert cfg["profiles"][config.DEFAULT_PROFILE_NAME] == {
        **config.default_profile(), "interval": 0.5, "hotkey": "F7", "mode": "Hold", "target_key": "mouse_left",
    }


@pytest.mark.parametrize("old, new", [
    ("middle", "mouse_middle"),
    ("right", "mouse_right"),
    ("left_arrow", "left"),
    ("right_arrow", "right"),
])
def test_v1_target_keys_are_renamed(old, new):
    write_legacy({"target_key": old})
    profile = config.load_config()["profiles"][config.DEFAULT_PROFILE_NAME]
    assert profile["target_key"] == new


def test_migrates_v2_flat_config_into_a_default_profile():
    write_config({"version": 2, "interval": 0.2, "hotkey": "F9", "mode": "Click", "target_key": "mouse_right"})
    cfg = config.load_config()
    assert cfg["version"] == config.CONFIG_VERSION
    assert cfg["profiles"][config.DEFAULT_PROFILE_NAME] == {
        **config.default_profile(), "interval": 0.2, "hotkey": "F9", "mode": "Click", "target_key": "mouse_right",
    }


def test_current_config_takes_priority_over_legacy_file():
    write_legacy({"hotkey": "F12"})
    write_config({
        "version": config.CONFIG_VERSION,
        "active_profile": "Main",
        "profiles": {"Main": {"hotkey": "F7"}},
    })
    cfg = config.load_config()
    assert list(cfg["profiles"]) == ["Main"]
    assert cfg["profiles"]["Main"]["hotkey"] == "F7"


@pytest.mark.parametrize("raw, expected", [
    (0.25, 0.25),
    (0, MIN_INTERVAL),
    (-5, MIN_INTERVAL),
    (1e9, MAX_INTERVAL),
    ("fast", DEFAULT_INTERVAL),
    (True, DEFAULT_INTERVAL),
    (None, DEFAULT_INTERVAL),
    (float("nan"), DEFAULT_INTERVAL),
    (float("inf"), DEFAULT_INTERVAL),
])
def test_interval_is_clamped_or_defaulted(raw, expected):
    assert sanitized_profile({"interval": raw})["interval"] == expected


def test_invalid_mode_and_key_fall_back_to_defaults():
    profile = sanitized_profile({"mode": "Turbo", "target_key": "f13"})
    assert profile["mode"] == MODE_CLICK
    assert profile["target_key"] == DEFAULT_TARGET_KEY


def test_hotkey_is_stripped():
    assert sanitized_profile({"hotkey": "  F8 "})["hotkey"] == "F8"


def test_duplicate_hotkeys_are_cleared_case_insensitively():
    cfg = config._sanitize({"profiles": {"A": {"hotkey": "F6"}, "B": {"hotkey": "f6"}, "C": {"hotkey": "F7"}}})
    hotkeys = {name: p["hotkey"] for name, p in cfg["profiles"].items()}
    assert hotkeys == {"A": "F6", "B": "", "C": "F7"}


def test_profile_names_are_trimmed_truncated_and_deduplicated():
    cfg = config._sanitize({"profiles": {
        "  Padded  ": {},
        "padded": {},
        "   ": {},
        "x" * 30: {},
        "Broken": "not a dict",
    }})
    assert list(cfg["profiles"]) == ["Padded", "x" * config.MAX_PROFILE_NAME]


def test_config_without_valid_profiles_gets_a_default_one():
    cfg = config._sanitize({"profiles": {"Broken": "nope"}})
    assert list(cfg["profiles"]) == [config.DEFAULT_PROFILE_NAME]


def test_unknown_active_profile_falls_back_to_the_first():
    cfg = config._sanitize({"active_profile": "Ghost", "profiles": {"One": {}, "Two": {}}})
    assert cfg["active_profile"] == "One"


def test_default_profile_has_no_variation_limit_or_delay():
    profile = config.default_profile()
    assert profile["jitter"] == DEFAULT_JITTER == 0
    assert profile["limit_kind"] == LIMIT_NEVER
    assert profile["limit_value"] == DEFAULT_LIMIT_VALUE
    assert profile["start_delay"] == DEFAULT_START_DELAY == 0


def test_v3_config_loads_with_defaults_for_the_new_fields():
    write_config({
        "version": 3,
        "active_profile": "Main",
        "profiles": {"Main": {"interval": 0.3, "hotkey": "F7", "mode": "Hold", "target_key": "space"}},
    })
    cfg = config.load_config()
    assert cfg["version"] == config.CONFIG_VERSION
    assert cfg["profiles"]["Main"] == {
        **config.default_profile(), "interval": 0.3, "hotkey": "F7", "mode": "Hold", "target_key": "space",
    }
    assert cfg["settings"] == config.default_settings()


@pytest.mark.parametrize("raw, expected", [
    (25, 25.0),
    (-10, 0.0),
    (250, MAX_JITTER),
    ("lots", DEFAULT_JITTER),
    (True, DEFAULT_JITTER),
    (float("nan"), DEFAULT_JITTER),
])
def test_jitter_is_clamped_to_a_percentage(raw, expected):
    assert sanitized_profile({"jitter": raw})["jitter"] == expected


@pytest.mark.parametrize("raw, expected", [
    (3, 3.0),
    (-1, 0.0),
    (9999, MAX_START_DELAY),
    (None, DEFAULT_START_DELAY),
    (float("inf"), DEFAULT_START_DELAY),
])
def test_start_delay_is_clamped(raw, expected):
    assert sanitized_profile({"start_delay": raw})["start_delay"] == expected


@pytest.mark.parametrize("raw, expected", [
    (500, 500.0),
    (0, MIN_LIMIT_VALUE),
    (10**9, MAX_LIMIT_VALUE),
    ("many", DEFAULT_LIMIT_VALUE),
])
def test_limit_value_is_clamped(raw, expected):
    assert sanitized_profile({"limit_value": raw})["limit_value"] == expected


@pytest.mark.parametrize("kind", [LIMIT_NEVER, LIMIT_CLICKS, LIMIT_TIME])
def test_known_limit_kinds_are_kept(kind):
    assert sanitized_profile({"limit_kind": kind})["limit_kind"] == kind


@pytest.mark.parametrize("kind", ["Forever", "clicks", "", None, 3])
def test_unknown_limit_kinds_fall_back_to_never(kind):
    assert sanitized_profile({"limit_kind": kind})["limit_kind"] == LIMIT_NEVER


def test_default_settings_are_all_off():
    assert config.default_settings() == {"failsafe": "Off", "always_on_top": False, "sound": False}


def test_v4_config_without_settings_gets_the_defaults():
    write_config({
        "version": 4,
        "active_profile": "Main",
        "profiles": {"Main": {"hotkey": "F7"}},
    })
    cfg = config.load_config()
    assert cfg["version"] == config.CONFIG_VERSION == 5
    assert cfg["settings"] == config.default_settings()
    assert cfg["profiles"]["Main"]["hotkey"] == "F7"


def test_settings_survive_saving_and_loading():
    cfg = config.load_config()
    cfg["settings"] = {"failsafe": "Bottom-right", "always_on_top": True, "sound": True}
    config.save_config(cfg)
    assert config.load_config()["settings"] == {"failsafe": "Bottom-right", "always_on_top": True, "sound": True}


@pytest.mark.parametrize("corner", ["Off", "Top-left", "Top-right", "Bottom-left", "Bottom-right"])
def test_every_failsafe_choice_is_kept(corner):
    assert config._sanitize_settings({"failsafe": corner})["failsafe"] == corner


@pytest.mark.parametrize("corner", ["Middle", "top-left", "", None, 3, True])
def test_unknown_failsafe_choices_fall_back_to_off(corner):
    assert config._sanitize_settings({"failsafe": corner})["failsafe"] == "Off"


@pytest.mark.parametrize("raw", ["yes", 1, 0, None, []])
def test_toggles_must_be_real_booleans(raw):
    settings = config._sanitize_settings({"always_on_top": raw, "sound": raw})
    assert settings["always_on_top"] is False
    assert settings["sound"] is False


@pytest.mark.parametrize("raw", [None, [], "nope", 5])
def test_settings_that_are_not_a_dict_give_the_defaults(raw):
    assert config._sanitize_settings(raw) == config.default_settings()


def test_settings_are_kept_apart_from_profile_data():
    cfg = config._sanitize({"profiles": {"A": {}}, "settings": {"sound": True}})
    assert cfg["settings"]["sound"] is True
    assert "sound" not in cfg["profiles"]["A"]


@pytest.mark.parametrize("version", ["5", None, 2.5, True, [5]])
def test_a_damaged_version_keeps_the_profiles(version):
    write_config({"version": version, "active_profile": "Main", "profiles": {"Main": {"hotkey": "F7"}}})
    cfg = config.load_config()
    assert list(cfg["profiles"]) == ["Main"]
    assert cfg["profiles"]["Main"]["hotkey"] == "F7"


def test_a_damaged_version_on_a_flat_file_is_migrated_like_v1():
    write_config({"version": "old", "interval": 0.5, "target_key": "left"})
    profile = config.load_config()["profiles"][config.DEFAULT_PROFILE_NAME]
    assert profile["interval"] == 0.5
    assert profile["target_key"] == "mouse_left"


def test_a_failed_save_removes_its_temp_file(monkeypatch):
    def broken_replace(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr(config.os, "replace", broken_replace)
    config.save_config(config.load_config())
    assert not os.path.exists(config.config_path() + ".tmp")
