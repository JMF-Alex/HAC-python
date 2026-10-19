import sys

from core.constants import MOUSE_KEYS

if sys.platform == "win32":
    import ctypes

    import keyboard

    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040

    _MOUSE_FLAGS = {
        "mouse_left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        "mouse_right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
        "mouse_middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    }
    assert set(_MOUSE_FLAGS) == set(MOUSE_KEYS)

    class InputSimulator:
        def __init__(self, key: str):
            self.key = key.strip().lower()
            self.is_mouse = self.key in _MOUSE_FLAGS
            if not self.is_mouse:
                keyboard.key_to_scan_codes(self.key)

        def press(self):
            if self.is_mouse:
                self._mouse_event(down=True)
            else:
                keyboard.press(self.key)

        def release(self):
            if self.is_mouse:
                self._mouse_event(down=False)
            else:
                keyboard.release(self.key)

        def click(self):
            self.press()
            self.release()

        def _mouse_event(self, down: bool):
            down_flag, up_flag = _MOUSE_FLAGS[self.key]
            ctypes.windll.user32.mouse_event(down_flag if down else up_flag, 0, 0, 0, 0)

else:
    from pynput import keyboard as _pk
    from pynput import mouse as _pm

    _MOUSE_BUTTONS = {
        "mouse_left": _pm.Button.left,
        "mouse_right": _pm.Button.right,
        "mouse_middle": _pm.Button.middle,
    }
    assert set(_MOUSE_BUTTONS) == set(MOUSE_KEYS)

    _SPECIAL_KEYS = {
        "space": _pk.Key.space,
        "shift": _pk.Key.shift,
        "ctrl": _pk.Key.ctrl,
        "alt": _pk.Key.alt,
        "enter": _pk.Key.enter,
        "tab": _pk.Key.tab,
        "up": _pk.Key.up,
        "down": _pk.Key.down,
        "left": _pk.Key.left,
        "right": _pk.Key.right,
    }

    class InputSimulator:
        def __init__(self, key: str):
            self.key = key.strip().lower()
            self.is_mouse = self.key in _MOUSE_BUTTONS
            if self.is_mouse:
                self._target = _MOUSE_BUTTONS[self.key]
                self._device = _pm.Controller()
            else:
                target = _SPECIAL_KEYS.get(self.key, self.key if len(self.key) == 1 else None)
                if target is None:
                    raise ValueError(f"Unknown key: {key!r}")
                self._target = target
                self._device = _pk.Controller()

        def press(self):
            self._device.press(self._target)

        def release(self):
            self._device.release(self._target)

        def click(self):
            self.press()
            self.release()