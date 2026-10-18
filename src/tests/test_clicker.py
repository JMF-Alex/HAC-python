import random
import time

import pytest

from core.clicker import Clicker, next_delay
from core.constants import (
    LIMIT_CLICKS,
    LIMIT_NEVER,
    LIMIT_TIME,
    MAX_START_DELAY,
    MIN_INTERVAL,
    MODE_CLICK,
    MODE_HOLD,
)


class FakeSimulator:
    def __init__(self, click_error=None, release_error=None, press_error=None):
        self.presses = 0
        self.releases = 0
        self.clicks = 0
        self.click_error = click_error
        self.release_error = release_error
        self.press_error = press_error

    def press(self):
        if self.press_error is not None:
            raise self.press_error
        self.presses += 1

    def release(self):
        self.releases += 1
        if self.release_error is not None:
            raise self.release_error

    def click(self):
        if self.click_error is not None:
            raise self.click_error
        self.clicks += 1


class FakeRng:
    def __init__(self, pick="low"):
        self.pick = pick
        self.calls = []

    def uniform(self, low, high):
        self.calls.append((low, high))
        return {"low": low, "high": high}[self.pick]


def wait_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


@pytest.fixture
def make_clicker():
    clickers = []

    def build(factory, **kwargs):
        clicker = Clicker(simulator_factory=factory, **kwargs)
        clickers.append(clicker)
        return clicker

    yield build
    for clicker in clickers:
        clicker.stop()


@pytest.fixture
def short_limits(monkeypatch):
    """The smallest allowed limit is 1, which would make the time tests slow."""
    monkeypatch.setattr("core.clicker.MIN_LIMIT_VALUE", 0.05)


def test_new_clicker_is_idle(make_clicker):
    clicker = make_clicker(lambda _key: FakeSimulator())
    assert not clicker.is_clicking
    assert not clicker.is_waiting
    assert clicker.last_error is None
    assert not clicker.limit_reached
    assert clicker.click_count == 0


def test_click_mode_clicks_repeatedly_until_stopped(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    assert clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left") is True
    assert clicker.is_clicking
    assert wait_until(lambda: sim.clicks >= 3)

    assert clicker.stop() is True
    assert not clicker.is_clicking
    clicks_at_stop = sim.clicks
    time.sleep(0.05)
    assert sim.clicks == clicks_at_stop
    assert sim.releases == 0
    assert not clicker.limit_reached


def test_starting_twice_keeps_the_first_run(make_clicker):
    created = []

    def factory(_key):
        created.append(FakeSimulator())
        return created[-1]

    clicker = make_clicker(factory)
    assert clicker.start(0.5, MODE_CLICK, "mouse_left") is True
    assert clicker.start(0.5, MODE_CLICK, "mouse_left") is False
    assert len(created) == 1


def test_stop_when_idle_returns_false(make_clicker):
    clicker = make_clicker(lambda _key: FakeSimulator())
    assert clicker.stop() is False


def test_stop_does_not_wait_for_the_interval(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(3600, MODE_CLICK, "mouse_left")
    assert wait_until(lambda: sim.clicks >= 1)

    started = time.monotonic()
    assert clicker.stop() is True
    assert time.monotonic() - started < 0.5


def test_hold_mode_presses_once_and_releases_on_stop(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    assert clicker.start(1, MODE_HOLD, "shift") is True
    assert clicker.is_clicking
    assert wait_until(lambda: sim.presses == 1)
    assert (sim.clicks, sim.releases) == (0, 0)

    assert clicker.stop() is True
    assert (sim.presses, sim.clicks, sim.releases) == (1, 0, 1)
    assert clicker.stop() is False


def test_failing_release_does_not_break_stop(make_clicker):
    sim = FakeSimulator(release_error=OSError("device gone"))
    clicker = make_clicker(lambda _key: sim)
    clicker.start(1, MODE_HOLD, "shift")
    assert wait_until(lambda: sim.presses == 1)

    assert clicker.stop() is True
    assert not clicker.is_clicking


def test_unknown_mode_is_rejected(make_clicker):
    clicker = make_clicker(lambda _key: FakeSimulator())
    with pytest.raises(ValueError):
        clicker.start(1, "Turbo", "mouse_left")
    assert not clicker.is_clicking


def test_unknown_limit_kind_is_rejected(make_clicker):
    clicker = make_clicker(lambda _key: FakeSimulator())
    with pytest.raises(ValueError):
        clicker.start(1, MODE_CLICK, "mouse_left", limit_kind="Forever")
    assert not clicker.is_clicking


def test_factory_errors_propagate_and_leave_the_clicker_idle(make_clicker):
    def factory(_key):
        raise ValueError("bad key")

    clicker = make_clicker(factory)
    with pytest.raises(ValueError, match="bad key"):
        clicker.start(1, MODE_CLICK, "nope")
    assert not clicker.is_clicking


def test_worker_crash_records_the_error_and_releases(make_clicker):
    sim = FakeSimulator(click_error=RuntimeError("boom"))
    clicker = make_clicker(lambda _key: sim)

    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left")
    assert wait_until(lambda: not clicker.is_clicking)

    assert clicker.last_error == "boom"
    assert sim.releases == 1


def test_worker_crash_without_a_message_falls_back_to_the_class_name(make_clicker):
    sim = FakeSimulator(click_error=ValueError())
    clicker = make_clicker(lambda _key: sim)

    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left")
    assert wait_until(lambda: not clicker.is_clicking)

    assert clicker.last_error == "ValueError"


def test_failing_press_in_hold_mode_is_reported_as_an_error(make_clicker):
    sim = FakeSimulator(press_error=OSError("no display"))
    clicker = make_clicker(lambda _key: sim)

    assert clicker.start(1, MODE_HOLD, "shift") is True
    assert wait_until(lambda: not clicker.is_clicking)

    assert clicker.last_error == "no display"
    assert not clicker.limit_reached


def test_last_error_is_cleared_by_the_next_start(make_clicker):
    sims = [FakeSimulator(click_error=RuntimeError("boom")), FakeSimulator()]
    clicker = make_clicker(lambda _key: sims.pop(0))

    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left")
    assert wait_until(lambda: not clicker.is_clicking)
    assert clicker.last_error == "boom"

    assert clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left") is True
    assert clicker.last_error is None


def test_next_delay_without_jitter_is_the_interval():
    rng = FakeRng()
    assert next_delay(0.5, 0, rng) == 0.5
    assert rng.calls == []


def test_next_delay_varies_within_the_given_percentage():
    rng = FakeRng(pick="low")
    assert next_delay(1.0, 25, rng) == pytest.approx(0.75)
    assert rng.calls == [(0.75, 1.25)]
    assert next_delay(1.0, 25, FakeRng(pick="high")) == pytest.approx(1.25)


def test_next_delay_never_drops_below_the_minimum_interval():
    assert next_delay(0.5, 100, FakeRng(pick="low")) == MIN_INTERVAL


def test_next_delay_stays_in_range_with_a_real_random_source():
    rng = random.Random(1234)
    delays = [next_delay(1.0, 30, rng) for _ in range(500)]
    assert all(0.7 <= d <= 1.3 for d in delays)
    assert len({round(d, 6) for d in delays}) > 100


def test_clicker_asks_the_random_source_only_when_jitter_is_set(make_clicker):
    rng = FakeRng(pick="low")
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim, rng=rng)
    clicker.start(0.01, MODE_CLICK, "mouse_left", jitter=0)
    assert wait_until(lambda: sim.clicks >= 3)
    clicker.stop()
    assert rng.calls == []

    sim2 = FakeSimulator()
    clicker2 = make_clicker(lambda _key: sim2, rng=rng)
    clicker2.start(0.01, MODE_CLICK, "mouse_left", jitter=50)
    assert wait_until(lambda: sim2.clicks >= 3)
    clicker2.stop()
    assert rng.calls and all(call == (0.5, 1.5) for call in rng.calls)


def test_jitter_above_one_hundred_percent_is_capped(make_clicker):
    rng = FakeRng(pick="low")
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim, rng=rng)
    clicker.start(0.01, MODE_CLICK, "mouse_left", jitter=900)
    assert wait_until(lambda: sim.clicks >= 2)
    clicker.stop()
    assert all(call == (0.0, 2.0) for call in rng.calls)


def test_click_limit_stops_after_exactly_that_many_clicks(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_CLICKS, limit_value=5)
    assert wait_until(lambda: not clicker.is_clicking)

    assert sim.clicks == 5
    assert clicker.click_count == 5
    assert clicker.limit_reached
    assert clicker.last_error is None
    assert sim.releases == 0


def test_click_limit_of_one_clicks_once(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(3600, MODE_CLICK, "mouse_left", limit_kind=LIMIT_CLICKS, limit_value=1)
    assert wait_until(lambda: not clicker.is_clicking)
    assert sim.clicks == 1
    assert clicker.limit_reached


def test_click_limit_is_rounded_to_whole_clicks(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_CLICKS, limit_value=3.6)
    assert wait_until(lambda: not clicker.is_clicking)
    assert sim.clicks == 4


def test_stopping_before_the_limit_does_not_count_as_reaching_it(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(3600, MODE_CLICK, "mouse_left", limit_kind=LIMIT_CLICKS, limit_value=10)
    assert wait_until(lambda: sim.clicks >= 1)

    clicker.stop()

    assert not clicker.limit_reached
    assert sim.clicks == 1


def test_time_limit_stops_click_mode_after_that_long(make_clicker, short_limits):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    started = time.monotonic()
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_TIME, limit_value=0.1)
    assert wait_until(lambda: not clicker.is_clicking)
    elapsed = time.monotonic() - started

    assert 0.09 <= elapsed < 1.0
    assert sim.clicks >= 1
    assert clicker.limit_reached
    clicks_at_end = sim.clicks
    time.sleep(0.05)
    assert sim.clicks == clicks_at_end


def test_time_limit_does_not_wait_for_a_long_interval(make_clicker, short_limits):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    clicker.start(3600, MODE_CLICK, "mouse_left", limit_kind=LIMIT_TIME, limit_value=0.1)
    assert wait_until(lambda: not clicker.is_clicking)

    assert sim.clicks == 1
    assert clicker.limit_reached


def test_hold_mode_releases_the_key_when_the_time_limit_passes(make_clicker, short_limits):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    clicker.start(1, MODE_HOLD, "shift", limit_kind=LIMIT_TIME, limit_value=0.1)
    assert wait_until(lambda: not clicker.is_clicking)

    assert (sim.presses, sim.clicks, sim.releases) == (1, 0, 1)
    assert clicker.limit_reached
    assert clicker.click_count == 0
    assert clicker.stop() is False
    assert sim.releases == 1


def test_click_limit_is_ignored_in_hold_mode(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    clicker.start(1, MODE_HOLD, "shift", limit_kind=LIMIT_CLICKS, limit_value=1)
    assert wait_until(lambda: sim.presses == 1)
    time.sleep(0.1)

    assert clicker.is_clicking
    assert sim.releases == 0
    assert not clicker.limit_reached


def test_starting_again_resets_the_previous_result(make_clicker):
    sims = [FakeSimulator(), FakeSimulator()]
    clicker = make_clicker(lambda _key: sims.pop(0))

    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_CLICKS, limit_value=2)
    assert wait_until(lambda: not clicker.is_clicking)
    assert clicker.limit_reached and clicker.click_count == 2

    clicker.start(3600, MODE_CLICK, "mouse_left")
    assert not clicker.limit_reached
    assert clicker.click_count in (0, 1)


def test_clear_result_forgets_the_finished_run(make_clicker):
    clicker = make_clicker(lambda _key: FakeSimulator())
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_CLICKS, limit_value=2)
    assert wait_until(lambda: not clicker.is_clicking)
    assert clicker.limit_reached

    clicker.clear_result()

    assert not clicker.limit_reached
    assert clicker.click_count == 0


def test_clear_result_does_not_touch_a_run_in_progress(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(0.01, MODE_CLICK, "mouse_left")
    assert wait_until(lambda: sim.clicks >= 2)

    clicker.clear_result()

    assert clicker.click_count >= 2


def test_never_limit_ignores_the_limit_value(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_NEVER, limit_value=1)
    assert wait_until(lambda: sim.clicks >= 5)
    assert clicker.is_clicking
    assert not clicker.limit_reached


def test_start_delay_postpones_the_first_click(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    started = time.monotonic()
    assert clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", start_delay=0.2) is True
    assert clicker.is_clicking
    assert clicker.is_waiting
    assert sim.clicks == 0

    assert wait_until(lambda: sim.clicks >= 1)
    assert time.monotonic() - started >= 0.19
    assert not clicker.is_waiting


def test_is_waiting_is_false_without_a_delay(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left")
    assert wait_until(lambda: sim.clicks >= 1)
    assert not clicker.is_waiting


def test_stopping_during_the_delay_cancels_without_clicking(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", start_delay=30)

    started = time.monotonic()
    assert clicker.stop() is True
    assert time.monotonic() - started < 0.5

    assert not clicker.is_clicking
    assert sim.clicks == 0


def test_stopping_during_the_delay_never_touches_a_held_key(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(1, MODE_HOLD, "shift", start_delay=30)

    assert clicker.stop() is True

    assert (sim.presses, sim.releases) == (0, 0)


def test_hold_mode_waits_for_the_delay_before_pressing(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(1, MODE_HOLD, "shift", start_delay=0.15)

    assert clicker.is_waiting
    assert sim.presses == 0
    assert wait_until(lambda: sim.presses == 1)
    assert not clicker.is_waiting


def test_the_time_limit_counts_from_the_end_of_the_delay(make_clicker, short_limits):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)

    started = time.monotonic()
    clicker.start(MIN_INTERVAL, MODE_CLICK, "mouse_left", limit_kind=LIMIT_TIME, limit_value=0.1, start_delay=0.2)
    assert wait_until(lambda: not clicker.is_clicking)

    assert time.monotonic() - started >= 0.29
    assert sim.clicks >= 1


def test_start_delay_is_capped(make_clicker):
    sim = FakeSimulator()
    clicker = make_clicker(lambda _key: sim)
    clicker.start(1, MODE_CLICK, "mouse_left", start_delay=10**6)

    assert clicker.is_waiting
    assert clicker._run.start_delay == MAX_START_DELAY
    assert clicker.stop() is True