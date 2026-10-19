"""Global single-key hotkeys on top of one raw keyboard listener.

Both platforms feed key events into `_dispatch`, which drops OS auto-repeat
(holding a hotkey must not toggle the clicker over and over) and lets a hook
consume an event so it does not also fire a hotkey.
"""
import logging
import sys
import threading
from types import SimpleNamespace

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import keyboard as _kb

    def _start_backend():
        def forward(event):
            _dispatch(event.event_type, event.name)

        _kb.hook(forward)
        return _kb.unhook_all

    def _validate(name):
        _kb.key_to_scan_codes(name)

else:
    from pynput import keyboard as _pk

    def _start_backend():
        listener = _pk.Listener(
            on_press=lambda key: _dispatch("down", _key_name(key)),
            on_release=lambda key: _dispatch("up", _key_name(key)),
        )
        listener.daemon = True
        listener.start()
        return listener.stop

    def _validate(name):
        if len(name) != 1 and name not in _pk.Key.__members__:
            raise ValueError(f"Unknown hotkey: {name!r}")

    def _key_name(key):
        if isinstance(key, _pk.Key):
            return key.name
        return getattr(key, "char", None)


_lock = threading.RLock()
_stop_backend = None
_hotkeys = {}
_hooks = []
_down = set()


def _normalize(hotkey):
    name = hotkey.strip().lower()
    if not name:
        raise ValueError("Empty hotkey")
    _validate(name)
    return name


def _call(fn, *args):
    try:
        return fn(*args)
    except Exception:
        logger.exception("Hotkey callback failed")
        return None


def _dispatch(event_type, name):
    if not name:
        return
    name = name.lower()
    with _lock:
        if event_type == "down":
            if name in _down:
                return
            _down.add(name)
        else:
            _down.discard(name)
        hooks = list(_hooks)
        handles = list(_hotkeys.get(name, ())) if event_type == "down" else []
    event = SimpleNamespace(event_type=event_type, name=name)
    consumed = False
    for fn in hooks:
        consumed = bool(_call(fn, event)) or consumed
    if consumed:
        return
    for _name, fn in handles:
        _call(fn)


def _ensure_listener():
    global _stop_backend
    with _lock:
        if _stop_backend is None:
            _stop_backend = _start_backend()


def add_hotkey(hotkey, callback, args=()):
    name = _normalize(hotkey)
    handle = (name, lambda: callback(*args))
    with _lock:
        _hotkeys.setdefault(name, []).append(handle)
    _ensure_listener()
    return handle


def remove_hotkey(handle):
    name = handle[0]
    with _lock:
        handles = _hotkeys.get(name, [])
        if handle not in handles:
            raise KeyError(handle)
        handles.remove(handle)
        if not handles:
            del _hotkeys[name]


def hook(callback):
    """Call `callback(event)` for every key event; a truthy return consumes it."""
    with _lock:
        _hooks.append(callback)
    _ensure_listener()
    return callback


def unhook(callback):
    with _lock:
        try:
            _hooks.remove(callback)
        except ValueError:
            pass


def unhook_all():
    global _stop_backend
    with _lock:
        _hotkeys.clear()
        _hooks.clear()
        _down.clear()
        stop, _stop_backend = _stop_backend, None
    if stop is not None:
        stop()
