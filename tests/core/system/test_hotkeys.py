import pytest

from core.system import hotkeys


@pytest.fixture(autouse=True)
def fake_backend(monkeypatch):
    state = {"started": 0, "stopped": 0}

    def start():
        state["started"] += 1
        return lambda: state.__setitem__("stopped", state["stopped"] + 1)

    monkeypatch.setattr(hotkeys, "_start_backend", start)
    monkeypatch.setattr(hotkeys, "_validate", lambda name: None)
    hotkeys.unhook_all()
    yield state
    hotkeys.unhook_all()


def press(name):
    hotkeys._dispatch("down", name)


def release(name):
    hotkeys._dispatch("up", name)


def test_a_hotkey_fires_once_per_press():
    calls = []
    hotkeys.add_hotkey("F6", calls.append, args=("F6",))

    press("f6")
    release("f6")

    assert calls == ["F6"]


def test_auto_repeat_while_held_does_not_fire_again():
    calls = []
    hotkeys.add_hotkey("F6", lambda: calls.append(1))

    for _ in range(5):
        press("f6")
    release("f6")
    press("f6")

    assert calls == [1, 1]


def test_names_are_matched_case_insensitively():
    calls = []
    hotkeys.add_hotkey("f8", lambda: calls.append(1))

    press("F8")

    assert calls == [1]


def test_other_keys_do_not_fire():
    calls = []
    hotkeys.add_hotkey("F6", lambda: calls.append(1))

    press("f7")
    press("a")

    assert calls == []


def test_events_without_a_name_are_ignored():
    seen = []
    hotkeys.hook(seen.append)

    press(None)
    press("")

    assert seen == []


def test_hooks_see_presses_and_releases():
    seen = []
    hotkeys.hook(lambda event: seen.append((event.event_type, event.name)))

    press("a")
    release("a")

    assert seen == [("down", "a"), ("up", "a")]


def test_a_hook_can_consume_the_press_so_the_hotkey_stays_quiet():
    calls = []
    hotkeys.add_hotkey("F6", lambda: calls.append(1))
    hotkeys.hook(lambda event: True)

    press("f6")

    assert calls == []


def test_a_hook_that_does_not_consume_lets_the_hotkey_fire():
    calls = []
    hotkeys.add_hotkey("F6", lambda: calls.append(1))
    hotkeys.hook(lambda event: None)

    press("f6")

    assert calls == [1]


def test_a_failing_callback_does_not_stop_the_others():
    calls = []

    def boom():
        raise RuntimeError("boom")

    hotkeys.add_hotkey("F6", boom)
    hotkeys.add_hotkey("F6", lambda: calls.append(1))

    press("f6")

    assert calls == [1]


def test_removed_hotkeys_stop_firing():
    calls = []
    handle = hotkeys.add_hotkey("F6", lambda: calls.append(1))

    hotkeys.remove_hotkey(handle)
    press("f6")

    assert calls == []


def test_removing_an_unknown_handle_raises_key_error():
    with pytest.raises(KeyError):
        hotkeys.remove_hotkey(("f6", lambda: None))


def test_unhook_removes_a_hook():
    seen = []
    hotkeys.hook(seen.append)

    hotkeys.unhook(seen.append)
    hotkeys.unhook(seen.append)
    press("a")

    assert seen == []


def test_empty_hotkeys_are_rejected():
    with pytest.raises(ValueError):
        hotkeys.add_hotkey("   ", lambda: None)


def test_the_listener_starts_once_and_stops_on_unhook_all(fake_backend):
    hotkeys.add_hotkey("F6", lambda: None)
    hotkeys.add_hotkey("F7", lambda: None)
    hotkeys.hook(lambda event: None)
    assert fake_backend["started"] == 1

    hotkeys.unhook_all()

    assert fake_backend["stopped"] == 1


def test_unhook_all_forgets_held_keys():
    calls = []
    press("f6")
    hotkeys.unhook_all()
    hotkeys.add_hotkey("F6", lambda: calls.append(1))

    press("f6")

    assert calls == [1]
