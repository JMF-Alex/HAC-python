import tkinter as tk
from types import SimpleNamespace

import pytest

from core.storage import config
from core.constants import (
    DEFAULT_INTERVAL,
    DEFAULT_JITTER,
    DEFAULT_LIMIT_VALUE,
    DEFAULT_START_DELAY,
    LIMIT_CLICKS,
    LIMIT_NEVER,
    LIMIT_TIME,
    MAX_JITTER,
    MAX_LIMIT_VALUE,
    MAX_START_DELAY,
    MIN_INTERVAL,
    MIN_LIMIT_VALUE,
    MODE_CLICK,
    MODE_HOLD,
)
from gui.controller import ClickerController


class FakeRoot:
    def __init__(self):
        self.scheduled = []
        self.cancelled = []

    def after(self, ms, _callback=None):
        self.scheduled.append(ms)
        return f"after-{len(self.scheduled)}"

    def after_cancel(self, after_id):
        self.cancelled.append(after_id)


class FakeEntry:
    def __init__(self, text=""):
        self.text = text

    def get(self):
        return self.text


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeView:
    def __init__(self):
        self.interval_entry = FakeEntry("0.5")
        self.jitter_entry = FakeEntry("0")
        self.delay_entry = FakeEntry("0")
        self.limit_entry = FakeEntry("100")
        self.mode_var = FakeVar(MODE_CLICK)
        self.key_var = FakeVar("mouse_left")
        self.limit_var = FakeVar(LIMIT_NEVER)
        self.app_settings = config.default_settings()
        self.pointer = (500, 500, 1920, 1080)
        self.pointer_error = None
        self.statuses = []
        self.inputs_enabled = []
        self.topmost_calls = []
        self.shown_profiles = []
        self.shown_settings = []
        self.beeps = 0
        self.hotkeys_shown = []
        self.waiting_shown = 0

    def show_number(self, entry, value):
        entry.text = str(value)

    def show_status(self, kind, message=None):
        self.statuses.append((kind, message))

    def set_inputs_enabled(self, enabled):
        self.inputs_enabled.append(enabled)

    def show_profile(self, name, settings):
        self.shown_profiles.append(name)

    def show_profiles(self, profiles, active):
        pass

    def show_hotkey(self, hotkey):
        self.hotkeys_shown.append(hotkey)

    def show_hotkey_waiting(self):
        self.waiting_shown += 1

    def show_settings(self, settings):
        self.shown_settings.append(dict(settings))

    def read_settings(self):
        return dict(self.app_settings)

    def set_always_on_top(self, enabled):
        self.topmost_calls.append(enabled)

    def beep(self):
        self.beeps += 1

    def pointer_position(self):
        if self.pointer_error is not None:
            raise self.pointer_error
        return self.pointer


class FakeClicker:
    def __init__(self):
        self.is_clicking = False
        self.is_waiting = False
        self.last_error = None
        self.limit_reached = False
        self.click_count = 0
        self.mode = MODE_CLICK
        self.elapsed = 0.0
        self.delay_remaining = 0.0
        self.started_with = None
        self.start_error = None
        self.cleared = 0
        self.stops = 0

    def start(self, interval, mode, key, **options):
        if self.start_error is not None:
            raise self.start_error
        self.started_with = (interval, mode, key, options)
        self.is_clicking = True
        return True

    def stop(self):
        self.stops += 1
        self.is_clicking = False
        self.is_waiting = False
        return True

    def clear_result(self):
        self.cleared += 1


@pytest.fixture
def hotkey_log(monkeypatch):
    log = {"added": [], "removed": [], "hooks": []}

    def add(hotkey, callback, args=()):
        log["added"].append(hotkey)
        return ("handle", hotkey)

    def remove(handle):
        log["removed"].append(handle[1])

    monkeypatch.setattr("core.system.hotkeys.add_hotkey", add)
    monkeypatch.setattr("core.system.hotkeys.remove_hotkey", remove)
    monkeypatch.setattr("core.system.hotkeys.unhook_all", lambda: None)
    monkeypatch.setattr("core.system.hotkeys.hook", log["hooks"].append)
    monkeypatch.setattr("core.system.hotkeys.unhook", log["hooks"].remove)
    return log


@pytest.fixture
def setup(hotkey_log):
    clicker = FakeClicker()
    controller = ClickerController(FakeRoot(), clicker, config.load_config())
    view = FakeView()
    controller.view = view
    return controller, view, clicker


def test_collect_settings_reads_every_field(setup):
    controller, view, _ = setup
    view.interval_entry.text = "0.25"
    view.jitter_entry.text = "30"
    view.delay_entry.text = "3"
    view.limit_entry.text = "500"
    view.limit_var.value = LIMIT_CLICKS
    view.mode_var.value = MODE_CLICK
    view.key_var.value = "space"

    assert controller.collect_settings() == {
        "interval": 0.25, "mode": MODE_CLICK, "target_key": "space", "jitter": 30.0,
        "limit_kind": LIMIT_CLICKS, "limit_value": 500.0, "start_delay": 3.0,
    }


def test_out_of_range_values_are_clamped(setup):
    controller, view, _ = setup
    view.interval_entry.text = "0"
    view.jitter_entry.text = "250"
    view.delay_entry.text = "999"
    view.limit_entry.text = "99999999"
    view.limit_var.value = LIMIT_TIME

    settings = controller.collect_settings()

    assert settings["interval"] == MIN_INTERVAL
    assert settings["jitter"] == MAX_JITTER
    assert settings["start_delay"] == MAX_START_DELAY
    assert settings["limit_value"] == MAX_LIMIT_VALUE


def test_limit_below_one_is_raised_to_the_minimum(setup):
    controller, view, _ = setup
    view.limit_entry.text = "0"
    view.limit_var.value = LIMIT_TIME
    assert controller.collect_settings()["limit_value"] == MIN_LIMIT_VALUE


@pytest.mark.parametrize("text", ["", ".", "abc"])
def test_empty_or_unreadable_numbers_fall_back_to_defaults(setup, text):
    controller, view, _ = setup
    for entry in (view.interval_entry, view.jitter_entry, view.delay_entry, view.limit_entry):
        entry.text = text
    view.limit_var.value = LIMIT_TIME

    settings = controller.collect_settings()

    assert settings["interval"] == DEFAULT_INTERVAL
    assert settings["jitter"] == DEFAULT_JITTER
    assert settings["start_delay"] == DEFAULT_START_DELAY
    assert settings["limit_value"] == DEFAULT_LIMIT_VALUE


def test_decimal_comma_is_accepted(setup):
    controller, view, _ = setup
    view.interval_entry.text = "0,25"
    assert controller.collect_settings()["interval"] == 0.25


def test_click_limit_is_rounded_to_a_whole_number(setup):
    controller, view, _ = setup
    view.limit_entry.text = "2.6"
    view.limit_var.value = LIMIT_CLICKS
    assert controller.collect_settings()["limit_value"] == 3.0


def test_time_limit_keeps_its_decimals(setup):
    controller, view, _ = setup
    view.limit_entry.text = "2.5"
    view.limit_var.value = LIMIT_TIME
    assert controller.collect_settings()["limit_value"] == 2.5


def test_corrections_are_written_back_only_when_asked(setup):
    controller, view, _ = setup
    view.jitter_entry.text = "250"

    controller.collect_settings()
    assert view.jitter_entry.text == "250"

    controller.collect_settings(fix=True)
    assert view.jitter_entry.text == str(MAX_JITTER)


def test_valid_values_are_not_rewritten(setup):
    controller, view, _ = setup
    view.interval_entry.text = "0.50"

    controller.collect_settings(fix=True)

    assert view.interval_entry.text == "0.50"


def test_the_limit_field_is_left_alone_while_the_limit_is_off(setup):
    controller, view, _ = setup
    view.limit_entry.text = ""
    view.limit_var.value = LIMIT_NEVER

    settings = controller.collect_settings(fix=True)

    assert view.limit_entry.text == ""
    assert settings["limit_value"] == DEFAULT_LIMIT_VALUE


def test_start_hands_every_setting_to_the_clicker(setup):
    controller, view, clicker = setup
    view.interval_entry.text = "0.2"
    view.jitter_entry.text = "15"
    view.delay_entry.text = "2"
    view.limit_entry.text = "40"
    view.limit_var.value = LIMIT_CLICKS
    view.key_var.value = "space"

    controller.start()

    assert clicker.started_with == (
        0.2, MODE_CLICK, "space",
        {"jitter": 15.0, "limit_kind": LIMIT_CLICKS, "limit_value": 40.0, "start_delay": 2.0},
    )


def test_start_saves_the_new_settings_into_the_profile(setup):
    controller, view, _ = setup
    view.jitter_entry.text = "15"
    view.limit_var.value = LIMIT_TIME
    view.limit_entry.text = "30"

    controller.start()

    profile = controller.active_settings
    assert profile["jitter"] == 15.0
    assert profile["limit_kind"] == LIMIT_TIME
    assert profile["limit_value"] == 30.0


def test_start_corrects_out_of_range_fields_on_screen(setup):
    controller, view, clicker = setup
    view.delay_entry.text = "999"

    controller.start()

    assert view.delay_entry.text == str(MAX_START_DELAY)
    assert clicker.started_with[3]["start_delay"] == MAX_START_DELAY


def test_start_failure_is_shown_as_an_error(setup):
    controller, view, clicker = setup
    clicker.start_error = ValueError("bad key")

    controller.start()

    assert view.statuses[-1] == ("error", "bad key")


def test_switching_profile_forgets_the_finished_run(setup):
    controller, _, clicker = setup

    controller._activate(controller.active_name, commit=False)

    assert clicker.cleared == 1


def test_status_follows_the_clicker_state(setup):
    controller, view, clicker = setup

    controller._refresh_status()
    assert view.statuses[-1] == ("stopped", None)
    assert view.inputs_enabled[-1] is True

    clicker.is_clicking, clicker.is_waiting, clicker.delay_remaining = True, True, 2.34
    controller._refresh_status()
    assert view.statuses[-1] == ("waiting", "Starting in 2.3 s")
    assert view.inputs_enabled[-1] is False

    clicker.is_waiting = False
    controller._refresh_status()
    assert view.statuses[-1] == ("running", "0 clicks")
    assert view.inputs_enabled[-1] is False


def test_inputs_are_only_toggled_when_running_changes(setup):
    controller, view, clicker = setup
    clicker.is_clicking = True

    for clicks in range(1, 6):
        clicker.click_count = clicks
        controller._refresh_status()

    assert view.inputs_enabled == [False]


def test_status_reports_a_run_that_reached_its_click_limit(setup):
    controller, view, clicker = setup
    clicker.limit_reached, clicker.click_count = True, 1234

    controller._refresh_status()

    assert view.statuses[-1] == ("done", "Finished after 1,234 clicks")
    assert view.inputs_enabled[-1] is True


def test_status_says_click_in_the_singular(setup):
    controller, view, clicker = setup
    clicker.limit_reached, clicker.click_count = True, 1

    controller._refresh_status()

    assert view.statuses[-1] == ("done", "Finished after 1 click")


def test_status_reports_a_hold_that_reached_its_time_limit(setup):
    controller, view, clicker = setup
    clicker.limit_reached, clicker.click_count = True, 0

    controller._refresh_status()

    assert view.statuses[-1] == ("done", "Finished · time limit reached")


def test_an_error_takes_priority_over_a_finished_note(setup):
    controller, view, clicker = setup
    clicker.limit_reached, clicker.click_count = True, 10
    clicker.last_error = "boom"

    controller._refresh_status()

    assert view.statuses[-1] == ("error", "boom")


def test_status_is_only_pushed_when_something_changed(setup):
    controller, view, _ = setup

    controller._refresh_status()
    controller._refresh_status()
    controller._refresh_status()

    assert len(view.statuses) == 1


def test_the_finished_note_disappears_once_the_result_is_cleared(setup):
    controller, view, clicker = setup
    clicker.limit_reached, clicker.click_count = True, 5
    controller._refresh_status()
    assert view.statuses[-1][0] == "done"

    clicker.limit_reached = False
    controller._refresh_status()

    assert view.statuses[-1] == ("stopped", None)


def test_running_status_shows_a_live_click_counter_with_the_rate(setup):
    controller, view, clicker = setup
    clicker.is_clicking = True
    clicker.click_count, clicker.elapsed = 1234, 10.0

    controller._refresh_status()

    assert view.statuses[-1] == ("running", "1,234 clicks · 123.4/s")


def test_the_rate_is_left_out_until_there_is_a_second_of_data(setup):
    controller, view, clicker = setup
    clicker.is_clicking = True
    clicker.click_count, clicker.elapsed = 5, 0.4

    controller._refresh_status()

    assert view.statuses[-1] == ("running", "5 clicks")


def test_a_single_click_is_singular_and_has_no_rate(setup):
    controller, view, clicker = setup
    clicker.is_clicking = True
    clicker.click_count, clicker.elapsed = 1, 3.0

    controller._refresh_status()

    assert view.statuses[-1] == ("running", "1 click")


def test_holding_shows_how_long_the_key_has_been_down(setup):
    controller, view, clicker = setup
    clicker.is_clicking, clicker.mode, clicker.elapsed = True, MODE_HOLD, 75.2

    controller._refresh_status()

    assert view.statuses[-1] == ("running", "Holding for 1:15")


def test_the_status_line_updates_as_the_counter_moves(setup):
    controller, view, clicker = setup
    clicker.is_clicking = True

    for clicks in (1, 2, 3):
        clicker.click_count = clicks
        controller._refresh_status()

    assert [message for _, message in view.statuses] == ["1 click", "2 clicks", "3 clicks"]


def test_countdown_updates_as_it_runs_down(setup):
    controller, view, clicker = setup
    clicker.is_clicking, clicker.is_waiting = True, True

    for remaining in (3.0, 2.5):
        clicker.delay_remaining = remaining
        controller._refresh_status()

    assert [message for _, message in view.statuses] == ["Starting in 3.0 s", "Starting in 2.5 s"]


def test_duplicate_creates_a_copy_with_the_same_settings(setup, hotkey_log):
    controller, view, _ = setup
    view.interval_entry.text = "0.25"
    view.jitter_entry.text = "20"
    view.limit_var.value = LIMIT_CLICKS
    view.limit_entry.text = "50"
    view.key_var.value = "space"

    controller.duplicate_profile("Default")

    profiles = controller.profiles
    assert list(profiles) == ["Default", "Default copy"]
    copy = profiles["Default copy"]
    for key in ("interval", "jitter", "limit_kind", "limit_value", "target_key", "mode", "start_delay"):
        assert copy[key] == profiles["Default"][key]
    assert copy["interval"] == 0.25 and copy["target_key"] == "space"
    assert controller.active_name == "Default copy"
    assert view.shown_profiles[-1] == "Default copy"


def test_the_copy_gets_its_own_free_hotkey(setup, hotkey_log):
    controller, _, _ = setup

    controller.duplicate_profile("Default")

    profiles = controller.profiles
    assert profiles["Default"]["hotkey"] == "F6"
    assert profiles["Default copy"]["hotkey"] == "F7"
    assert "F7" in hotkey_log["added"]


def test_the_copy_has_no_hotkey_when_the_backend_refuses_it(setup, monkeypatch):
    controller, _, _ = setup

    def refuse(hotkey, callback, args=()):
        raise ValueError("unknown key")

    monkeypatch.setattr("core.system.hotkeys.add_hotkey", refuse)

    controller.duplicate_profile("Default")

    assert controller.profiles["Default copy"]["hotkey"] == ""


def test_duplicating_twice_numbers_the_copies(setup):
    controller, _, _ = setup

    controller.duplicate_profile("Default")
    controller.duplicate_profile("Default")

    assert list(controller.profiles) == ["Default", "Default copy", "Default copy 2"]


def test_the_copy_is_saved_to_disk(setup):
    controller, _, _ = setup

    controller.duplicate_profile("Default")

    saved = config.load_config()
    assert "Default copy" in saved["profiles"]
    assert saved["active_profile"] == "Default copy"


def test_duplicate_stops_a_running_clicker(setup):
    controller, _, clicker = setup
    clicker.is_clicking = True

    controller.duplicate_profile("Default")

    assert clicker.stops == 1


def test_duplicate_is_ignored_while_a_dialog_or_hotkey_capture_is_open(setup):
    controller, _, _ = setup
    controller._dialog_open = True
    controller.duplicate_profile("Default")
    controller._dialog_open = False
    controller.hotkey_waiting = True
    controller.duplicate_profile("Default")

    assert list(controller.profiles) == ["Default"]


def test_duplicating_an_unknown_profile_does_nothing(setup):
    controller, _, _ = setup
    controller.duplicate_profile("Ghost")
    assert list(controller.profiles) == ["Default"]


def test_settings_start_with_the_saved_values(hotkey_log):
    saved = config.load_config()
    saved["settings"] = {"failsafe": "Top-right", "always_on_top": True, "sound": True}
    controller = ClickerController(FakeRoot(), FakeClicker(), saved)

    assert controller.settings == {"failsafe": "Top-right", "always_on_top": True, "sound": True}


def test_binding_the_view_shows_the_saved_settings_and_starts_the_fail_safe_loop(hotkey_log):
    root = FakeRoot()
    controller = ClickerController(root, FakeClicker(), config.load_config())
    view = FakeView()

    controller.bind_view(view)

    assert view.shown_settings == [config.default_settings()]
    assert ClickerController.STATUS_POLL_MS in root.scheduled
    assert ClickerController.FAILSAFE_POLL_MS in root.scheduled


def test_changing_settings_applies_the_window_option_and_saves(setup):
    controller, view, _ = setup
    view.app_settings = {"failsafe": "Bottom-left", "always_on_top": True, "sound": True}

    controller.settings_changed()

    assert view.topmost_calls == [True]
    assert controller.settings == {"failsafe": "Bottom-left", "always_on_top": True, "sound": True}
    assert config.load_config()["settings"] == {"failsafe": "Bottom-left", "always_on_top": True, "sound": True}


def test_saving_the_profile_keeps_the_app_settings(setup):
    controller, view, _ = setup
    view.app_settings = {"failsafe": "Top-left", "always_on_top": False, "sound": True}
    controller.settings_changed()

    controller.save_settings(force=True)

    assert config.load_config()["settings"]["failsafe"] == "Top-left"
    assert controller._snapshot()["settings"] == controller.settings


def enable_failsafe(controller, view, corner="Top-left"):
    view.app_settings = {**config.default_settings(), "failsafe": corner}
    controller.settings_changed()


def test_reaching_the_corner_stops_the_clicker_and_says_why(setup):
    controller, view, clicker = setup
    enable_failsafe(controller, view, "Top-left")
    clicker.is_clicking = True
    view.pointer = (0, 0, 1920, 1080)

    controller._check_failsafe()

    assert clicker.stops == 1
    assert not clicker.is_clicking
    assert view.statuses[-1] == ("done", "Stopped · mouse reached the top-left corner")


@pytest.mark.parametrize("corner, pointer", [
    ("Top-right", (1919, 0)),
    ("Bottom-left", (0, 1079)),
    ("Bottom-right", (1919, 1079)),
])
def test_every_corner_can_be_the_fail_safe(setup, corner, pointer):
    controller, view, clicker = setup
    enable_failsafe(controller, view, corner)
    clicker.is_clicking = True
    view.pointer = (*pointer, 1920, 1080)

    controller._check_failsafe()

    assert clicker.stops == 1


def test_a_different_corner_does_not_stop_it(setup):
    controller, view, clicker = setup
    enable_failsafe(controller, view, "Top-left")
    clicker.is_clicking = True
    view.pointer = (1919, 1079, 1920, 1080)

    controller._check_failsafe()

    assert clicker.stops == 0
    assert clicker.is_clicking


def test_the_fail_safe_is_ignored_when_it_is_off(setup):
    controller, view, clicker = setup
    clicker.is_clicking = True
    view.pointer = (0, 0, 1920, 1080)

    controller._check_failsafe()

    assert clicker.stops == 0


def test_the_fail_safe_does_nothing_while_idle(setup):
    controller, view, clicker = setup
    enable_failsafe(controller, view)
    view.pointer = (0, 0, 1920, 1080)

    controller._check_failsafe()

    assert clicker.stops == 0
    assert view.statuses == []


def test_the_fail_safe_waits_for_the_countdown_to_finish(setup):
    controller, view, clicker = setup
    enable_failsafe(controller, view)
    clicker.is_clicking, clicker.is_waiting = True, True
    view.pointer = (0, 0, 1920, 1080)

    controller._check_failsafe()

    assert clicker.stops == 0


def test_an_unreadable_pointer_position_is_survived(setup):
    controller, view, clicker = setup
    enable_failsafe(controller, view)
    clicker.is_clicking = True
    view.pointer_error = RuntimeError("display gone")

    controller._check_failsafe()

    assert clicker.stops == 0


def test_the_fail_safe_note_goes_away_on_the_next_start(setup):
    controller, view, clicker = setup
    enable_failsafe(controller, view)
    clicker.is_clicking = True
    view.pointer = (0, 0, 1920, 1080)
    controller._check_failsafe()
    assert view.statuses[-1][0] == "done"

    view.pointer = (500, 500, 1920, 1080)
    controller.start()
    clicker.is_clicking = False
    controller._refresh_status()

    assert view.statuses[-1] == ("stopped", None)


def test_the_fail_safe_poll_reschedules_itself(setup):
    controller, _, _ = setup
    controller._failsafe_poll()
    assert controller.root.scheduled[-1] == ClickerController.FAILSAFE_POLL_MS


def enable_sound(controller, view):
    view.app_settings = {**config.default_settings(), "sound": True}
    controller.settings_changed()


def test_sound_beeps_when_clicking_starts_and_when_it_stops(setup):
    controller, view, clicker = setup
    enable_sound(controller, view)

    clicker.is_clicking = True
    controller._refresh_status()
    assert view.beeps == 1

    clicker.click_count = 4
    controller._refresh_status()
    assert view.beeps == 1

    clicker.is_clicking = False
    controller._refresh_status()
    assert view.beeps == 2


def test_sound_waits_for_the_countdown_before_beeping(setup):
    controller, view, clicker = setup
    enable_sound(controller, view)

    clicker.is_clicking, clicker.is_waiting = True, True
    controller._refresh_status()
    assert view.beeps == 0

    clicker.is_waiting = False
    controller._refresh_status()
    assert view.beeps == 1


def test_cancelling_the_countdown_does_not_beep(setup):
    controller, view, clicker = setup
    enable_sound(controller, view)
    clicker.is_clicking, clicker.is_waiting = True, True
    controller._refresh_status()

    clicker.is_clicking, clicker.is_waiting = False, False
    controller._refresh_status()

    assert view.beeps == 0


def test_no_sound_when_it_is_off(setup):
    controller, view, clicker = setup

    clicker.is_clicking = True
    controller._refresh_status()
    clicker.is_clicking = False
    controller._refresh_status()

    assert view.beeps == 0


def test_the_fail_safe_stop_beeps_like_any_other_stop(setup):
    controller, view, clicker = setup
    view.app_settings = {"failsafe": "Top-left", "always_on_top": False, "sound": True}
    controller.settings_changed()
    clicker.is_clicking = True
    controller._refresh_status()
    view.pointer = (0, 0, 1920, 1080)

    controller._check_failsafe()

    assert view.beeps == 2


def test_shutdown_cancels_both_polling_loops(hotkey_log):
    root = FakeRoot()
    controller = ClickerController(root, FakeClicker(), config.load_config())
    controller.bind_view(FakeView())

    controller.shutdown()

    assert len(root.cancelled) == 2

class ImmediateRoot(FakeRoot):
    def after(self, ms, callback=None):
        if ms == 0 and callback is not None:
            callback()
            return "now"
        return super().after(ms, callback)


def key_down(name):
    return SimpleNamespace(event_type="down", name=name)


@pytest.fixture
def capture(setup, hotkey_log):
    controller, view, clicker = setup
    controller.root = ImmediateRoot()
    controller.bind_view(view)
    controller.change_hotkey()
    return controller, view, hotkey_log


def test_changing_the_hotkey_waits_for_a_key(capture):
    controller, view, log = capture
    assert controller.hotkey_waiting
    assert view.waiting_shown == 1
    assert len(log["hooks"]) == 1


def test_the_pressed_key_becomes_the_new_hotkey(capture):
    controller, view, log = capture

    consumed = log["hooks"][0](key_down("f9"))

    assert consumed is True
    assert not controller.hotkey_waiting
    assert controller.current_hotkey == "F9"
    assert "F9" in log["added"]
    assert "F6" in log["removed"]
    assert view.hotkeys_shown[-1] == "F9"
    assert log["hooks"] == []
    assert config.load_config()["profiles"]["Default"]["hotkey"] == "F9"


def test_escape_cancels_and_keeps_the_old_hotkey(capture):
    controller, view, log = capture

    log["hooks"][0](key_down("esc"))

    assert not controller.hotkey_waiting
    assert controller.current_hotkey == "F6"
    assert "ESC" not in log["added"]
    assert log["removed"] == []
    assert view.hotkeys_shown[-1] == "F6"


def test_key_releases_are_not_captured(capture):
    controller, _, log = capture

    consumed = log["hooks"][0](SimpleNamespace(event_type="up", name="f9"))

    assert consumed is False
    assert controller.hotkey_waiting


def test_a_hotkey_owned_by_another_profile_is_refused(capture):
    controller, view, log = capture
    controller.hotkey_waiting = False
    controller.duplicate_profile("Default")
    controller.change_hotkey()

    log["hooks"][-1](key_down("f6"))

    assert controller.current_hotkey == "F7"
    assert view.statuses[-1] == ("error", "F6 is already used by 'Default'")


def test_profiles_cannot_be_switched_while_capturing_a_hotkey(capture):
    controller, _, _ = capture
    controller.hotkey_waiting = False
    controller.duplicate_profile("Default")
    controller.change_hotkey()

    controller.select_profile("Default")

    assert controller.active_name == "Default copy"


def test_a_hotkey_that_fires_while_the_window_closes_is_ignored(setup):
    controller, _, _ = setup

    class ClosedRoot(FakeRoot):
        def after(self, ms, callback=None):
            raise tk.TclError("application has been destroyed")

    controller.root = ClosedRoot()
    controller._on_hotkey("F6")


def test_the_hotkey_toggles_the_active_profile(setup):
    controller, _, clicker = setup
    controller.root = ImmediateRoot()

    controller._on_hotkey("F6")
    assert clicker.is_clicking

    controller._on_hotkey("F6")
    assert not clicker.is_clicking


def test_another_profiles_hotkey_switches_to_it_and_starts(setup):
    controller, view, clicker = setup
    controller.duplicate_profile("Default")
    controller.select_profile("Default")
    controller.root = ImmediateRoot()

    controller._on_hotkey("F7")

    assert controller.active_name == "Default copy"
    assert clicker.is_clicking
