import logging
import random
import threading
import time
from dataclasses import dataclass, field

from core.constants import (
    LIMIT_CLICKS,
    LIMIT_KINDS,
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
from core.system.input_simulator import InputSimulator

logger = logging.getLogger(__name__)

PHASE_WAITING = "waiting"
PHASE_RUNNING = "running"


def next_delay(interval: float, jitter: float, rng) -> float:
    if jitter <= 0:
        return interval
    spread = jitter / 100.0
    return max(MIN_INTERVAL, interval * rng.uniform(1.0 - spread, 1.0 + spread))


def _clamp(value, low: float, high: float) -> float:
    return min(high, max(low, float(value)))


@dataclass
class _Run:
    simulator: object
    mode: str
    interval: float
    jitter: float
    limit_kind: str
    limit_value: float
    start_delay: float
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread = None
    phase: str = PHASE_WAITING
    pressed: bool = False
    created_at: float = field(default_factory=time.monotonic)
    started_at: float = 0.0


class Clicker:
    def __init__(self, simulator_factory=InputSimulator, rng=None):
        self._simulator_factory = simulator_factory
        self._rng = rng or random.Random()
        self._lock = threading.Lock()
        self._run = None
        self._last_error = None
        self._limit_reached = False
        self._click_count = 0

    @property
    def is_clicking(self) -> bool:
        return self._run is not None

    @property
    def is_waiting(self) -> bool:
        run = self._run
        return run is not None and run.phase == PHASE_WAITING

    @property
    def mode(self):
        run = self._run
        return run.mode if run is not None else None

    @property
    def elapsed(self) -> float:
        run = self._run
        if run is None or run.phase != PHASE_RUNNING:
            return 0.0
        return time.monotonic() - run.started_at

    @property
    def delay_remaining(self) -> float:
        run = self._run
        if run is None or run.phase != PHASE_WAITING:
            return 0.0
        return max(0.0, run.start_delay - (time.monotonic() - run.created_at))

    @property
    def last_error(self):
        return self._last_error

    @property
    def limit_reached(self) -> bool:
        return self._limit_reached

    @property
    def click_count(self) -> int:
        return self._click_count

    def start(
        self,
        interval: float,
        mode: str,
        key: str,
        *,
        jitter: float = 0.0,
        limit_kind: str = LIMIT_NEVER,
        limit_value: float = 0.0,
        start_delay: float = 0.0,
    ) -> bool:
        if mode not in (MODE_CLICK, MODE_HOLD):
            raise ValueError(f"Unknown mode: {mode!r}")
        if limit_kind not in LIMIT_KINDS:
            raise ValueError(f"Unknown limit: {limit_kind!r}")
        if limit_kind == LIMIT_CLICKS and mode == MODE_HOLD:
            limit_kind = LIMIT_NEVER
        if limit_kind == LIMIT_CLICKS:
            limit_value = round(_clamp(limit_value, MIN_LIMIT_VALUE, MAX_LIMIT_VALUE))
        elif limit_kind == LIMIT_TIME:
            limit_value = _clamp(limit_value, MIN_LIMIT_VALUE, MAX_LIMIT_VALUE)

        with self._lock:
            if self._run is not None:
                return False
            simulator = self._simulator_factory(key)
            run = _Run(
                simulator=simulator,
                mode=mode,
                interval=_clamp(interval, MIN_INTERVAL, MAX_INTERVAL),
                jitter=_clamp(jitter, 0.0, MAX_JITTER),
                limit_kind=limit_kind,
                limit_value=float(limit_value),
                start_delay=_clamp(start_delay, 0.0, MAX_START_DELAY),
            )
            run.thread = threading.Thread(target=self._work, args=(run,), name="hac-clicker", daemon=True)
            self._last_error = None
            self._limit_reached = False
            self._click_count = 0
            self._run = run
            run.thread.start()
            return True

    def stop(self) -> bool:
        with self._lock:
            run = self._run
            if run is None:
                return False
            self._run = None

        run.stop_event.set()
        if run.thread is not threading.current_thread():
            run.thread.join(timeout=1.0)
        if run.mode == MODE_HOLD and run.pressed:
            self._safe_release(run.simulator)
        return True

    def clear_result(self) -> None:
        with self._lock:
            if self._run is None:
                self._limit_reached = False
                self._click_count = 0

    def _work(self, run: _Run) -> None:
        try:
            if run.start_delay > 0 and run.stop_event.wait(run.start_delay):
                return
            with self._lock:
                if self._run is not run:
                    return
                run.started_at = time.monotonic()
                run.phase = PHASE_RUNNING
            reached = self._hold(run) if run.mode == MODE_HOLD else self._click_loop(run)
        except Exception as exc:
            logger.exception("Clicker worker crashed")
            self._safe_release(run.simulator)
            self._finish(run, error=str(exc) or exc.__class__.__name__)
            return
        if reached:
            self._finish(run, reached=True)

    def _click_loop(self, run: _Run) -> bool:
        max_clicks = int(run.limit_value) if run.limit_kind == LIMIT_CLICKS else None
        deadline = time.monotonic() + run.limit_value if run.limit_kind == LIMIT_TIME else None
        clicks = 0
        while not run.stop_event.is_set():
            run.simulator.click()
            clicks += 1
            self._click_count = clicks
            if max_clicks is not None and clicks >= max_clicks:
                return True
            delay = next_delay(run.interval, run.jitter, self._rng)
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return True
                if delay >= remaining:
                    return not run.stop_event.wait(remaining)
            if run.stop_event.wait(delay):
                return False
        return False

    def _hold(self, run: _Run) -> bool:
        run.simulator.press()
        run.pressed = True
        timeout = run.limit_value if run.limit_kind == LIMIT_TIME else None
        return not run.stop_event.wait(timeout)

    def _finish(self, run: _Run, reached: bool = False, error=None) -> None:
        with self._lock:
            if self._run is not run:
                return
            if reached and run.mode == MODE_HOLD and run.pressed:
                self._safe_release(run.simulator)
            if error:
                self._last_error = error
            if reached:
                self._limit_reached = True
            self._run = None

    @staticmethod
    def _safe_release(simulator) -> None:
        try:
            simulator.release()
        except Exception:
            logger.exception("Could not release key")
