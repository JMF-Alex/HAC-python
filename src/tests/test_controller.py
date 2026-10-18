import pytest

from core import config
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
)
from gui.controller import ClickerController


class FakeRoot:
    def after(self, _ms, _callback=None):
        return "after-id"

    def after_cancel(self, _id):
        pass


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
        self.statuses = []
        self.inputs_enabled = []

    def show_number(self, entry, value):
        entry.text = str(value)

    def show_status(self, kind, message=None):
        self.statuses.append((kind, message))

    def set_inputs_enabled(self, enabled):
        self.inputs_enabled.append(enabled)

    def show_profile(self, name, settings):
        pass

    def show_profiles(self, profiles, active):
        pass


class FakeClicker:
    def __init__(self):
        self.is_clicking = False
        self.is_waiting = False
        self.last_error = None
        self.limit_reached = False
        self.click_count = 0
        self.started_with = None
        self.start_error = None
        self.cleared = 0

    def start(self, interval, mode, key, **options):
        if self.start_error is not None:
            raise self.start_error
        self.started_with = (interval, mode, key, options)
        self.is_clicking = True
        return True

    def stop(self):
        self.is_clicking = False
        return True

    def clear_result(self):
        self.cleared += 1


@pytest.fixture
def setup():
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

    clicker.is_clicking, clicker.is_waiting = True, True
    controller._refresh_status()
    assert view.statuses[-1] == ("waiting", None)
    assert view.inputs_enabled[-1] is False

    clicker.is_waiting = False
    controller._refresh_status()
    assert view.statuses[-1] == ("running", None)
    assert view.inputs_enabled[-1] is False


def test_status_reports_a_run_that_reached_its_click_limit(setup):
    controller, view, clicker = setup
    clicker.limit_reached, clicker.click_count = True, 1234

    controller._refresh_status()

    assert view.statuses[-1] == ("done", "Finished after 1,234 clicks")
    assert view.inputs_enabled[-1] is True


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