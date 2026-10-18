import logging
import threading

from core import hotkeys

from core.config import (
    CONFIG_VERSION,
    default_profile,
    name_error,
    save_config,
    suggest_hotkey,
    unique_name,
)
from core.constants import (
    DEFAULT_INTERVAL,
    DEFAULT_JITTER,
    DEFAULT_LIMIT_VALUE,
    DEFAULT_START_DELAY,
    LIMIT_CLICKS,
    LIMIT_NEVER,
    MAX_INTERVAL,
    MAX_JITTER,
    MAX_LIMIT_VALUE,
    MAX_START_DELAY,
    MIN_INTERVAL,
    MIN_JITTER,
    MIN_LIMIT_VALUE,
    MIN_START_DELAY,
)

logger = logging.getLogger(__name__)


class ClickerController:
    STATUS_POLL_MS = 200

    def __init__(self, root, clicker, config):
        self.root = root
        self.clicker = clicker
        self.view = None
        self.hotkey_waiting = False
        self._profiles = {name: dict(s) for name, s in config["profiles"].items()}
        self._active = config["active_profile"]
        self._hotkey_handles = {}
        self._last_saved = self._snapshot()
        self._error = None
        self._shown_status = None
        self._poll_id = None
        self._dialog_open = False


    @property
    def active_name(self) -> str:
        return self._active

    @property
    def active_settings(self) -> dict:
        return dict(self._profiles[self._active])

    @property
    def profiles(self) -> dict:
        return {name: dict(s) for name, s in self._profiles.items()}

    @property
    def current_hotkey(self) -> str:
        return self._profiles[self._active]["hotkey"]

    def bind_view(self, view):
        self.view = view
        for settings in self._profiles.values():
            if settings["hotkey"] and not self._register_hotkey(settings["hotkey"]):
                settings["hotkey"] = ""
        self.view.show_hotkey(self.current_hotkey)
        self._refresh_status()
        self._poll_id = self.root.after(self.STATUS_POLL_MS, self._poll)


    def toggle(self):
        if self.clicker.is_clicking:
            self.stop()
        else:
            self.start()

    def start(self):
        settings = self.collect_settings(fix=True)
        try:
            self.clicker.start(
                settings["interval"], settings["mode"], settings["target_key"],
                jitter=settings["jitter"], limit_kind=settings["limit_kind"],
                limit_value=settings["limit_value"], start_delay=settings["start_delay"],
            )
        except Exception as exc:
            logger.exception("Could not start clicking")
            self._error = str(exc) or exc.__class__.__name__
        else:
            self._error = None
            self.save_settings()
        self._refresh_status()

    def stop(self):
        self.clicker.stop()
        self._refresh_status()


    def select_profile(self, name):
        if self._blocked() or name == self._active or name not in self._profiles:
            return
        self.clicker.stop()
        self._activate(name)
        self.save_settings(refresh=False)

    def add_profile(self):
        if self._blocked():
            return
        name = self._ask(
            self.view.ask_profile_name, "New profile", unique_name("Profile", self._profiles),
            lambda n: name_error(n, self._profiles), "Create",
        )
        if name is None:
            return
        self.clicker.stop()
        self._commit_view()
        settings = default_profile()
        settings["hotkey"] = suggest_hotkey(self._taken_hotkeys())
        if settings["hotkey"] and not self._register_hotkey(settings["hotkey"]):
            settings["hotkey"] = ""
        self._profiles[name] = settings
        self._activate(name, commit=False)
        self.save_settings(refresh=False)

    def rename_profile(self, name):
        if self._blocked() or name not in self._profiles:
            return
        new = self._ask(
            self.view.ask_profile_name, "Rename profile", name,
            lambda n: name_error(n, self._profiles, ignore=name), "Save",
        )
        if new is None or new == name or name not in self._profiles:
            return
        self._profiles = {(new if k == name else k): v for k, v in self._profiles.items()}
        if self._active == name:
            self._active = new
            self.view.set_profile_title(new)
        self.save_settings()

    def delete_profile(self, name):
        if self._blocked() or name not in self._profiles:
            return
        if len(self._profiles) == 1:
            self._ask(self.view.show_message, "Can't delete", "You need at least one profile.")
            return
        if not self._ask(self.view.confirm_delete, name) or name not in self._profiles:
            return
        names = list(self._profiles)
        index = names.index(name)
        was_active = name == self._active
        if was_active:
            self.clicker.stop()
        self._release_hotkey(self._profiles.pop(name)["hotkey"])
        if was_active:
            names.remove(name)
            self._activate(names[min(index, len(names) - 1)], commit=False)
        self.save_settings()

    def _activate(self, name, commit=True):
        if commit:
            self._commit_view()
        self._active = name
        self._error = None
        self.clicker.clear_result()
        self.view.show_profile(name, self._profiles[name])
        self._push_profiles()
        self._refresh_status()

    def _blocked(self) -> bool:
        return self.hotkey_waiting or self._dialog_open

    def _ask(self, fn, *args):
        self._dialog_open = True
        try:
            return fn(*args)
        finally:
            self._dialog_open = False

    def _taken_hotkeys(self):
        return [s["hotkey"] for s in self._profiles.values()]

    def _profile_for_hotkey(self, hotkey):
        wanted = hotkey.lower()
        for name, settings in self._profiles.items():
            if settings["hotkey"] and settings["hotkey"].lower() == wanted:
                return name
        return None

    def _commit_view(self):
        self._profiles[self._active].update(self.collect_settings())

    def _push_profiles(self):
        self.view.show_profiles(self._profiles, self._active)


    def _on_hotkey(self, hotkey):
        try:
            self.root.after(0, lambda: self._toggle_for_hotkey(hotkey))
        except RuntimeError:
            pass

    def _toggle_for_hotkey(self, hotkey):
        if self._blocked():
            return
        name = self._profile_for_hotkey(hotkey)
        if name is None:
            return
        if name == self._active:
            self.toggle()
            return
        self.clicker.stop()
        self._activate(name)
        self.start()

    def _register_hotkey(self, hotkey) -> bool:
        if hotkey in self._hotkey_handles:
            return True
        try:
            handle = hotkeys.add_hotkey(hotkey, self._on_hotkey, args=(hotkey,))
        except (ValueError, KeyError):
            logger.exception("Invalid hotkey %r", hotkey)
            self._error = f"Invalid hotkey: {hotkey}"
            return False
        self._hotkey_handles[hotkey] = handle
        return True

    def _release_hotkey(self, hotkey):
        handle = self._hotkey_handles.pop(hotkey, None)
        if handle is None:
            return
        try:
            hotkeys.remove_hotkey(handle)
        except (KeyError, ValueError):
            pass

    def change_hotkey(self):
        if self._blocked():
            return
        self.hotkey_waiting = True
        self.view.show_hotkey_waiting()
        captured = threading.Event()

        def on_key(event):
            if event.event_type != "down" or captured.is_set():
                return
            captured.set()
            hotkeys.unhook(on_key)
            new_key = event.name.upper()
            try:
                self.root.after(0, lambda: self._apply_new_hotkey(new_key))
            except RuntimeError:
                pass

        hotkeys.hook(on_key)

    def _apply_new_hotkey(self, new_key):
        self.hotkey_waiting = False
        owner = self._profile_for_hotkey(new_key)
        previous = self.current_hotkey
        if owner is not None and owner != self._active:
            self._error = f"{new_key} is already used by '{owner}'"
        elif self._register_hotkey(new_key):
            self._profiles[self._active]["hotkey"] = new_key
            if previous and previous != new_key:
                self._release_hotkey(previous)
            self._error = None
            self.save_settings()
        self.view.show_hotkey(self.current_hotkey)
        self._refresh_status()


    def _read_number(self, entry, default, low, high, fix=False, whole=False) -> float:
        raw = entry.get().strip().replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            value, corrected = default, True
        else:
            clamped = min(high, max(low, value))
            if whole:
                clamped = float(int(clamped + 0.5))
            value, corrected = clamped, clamped != value
        if corrected and fix:
            self.view.show_number(entry, value)
        return value

    def collect_settings(self, fix=False) -> dict:
        view = self.view
        limit_kind = view.limit_var.get()
        return {
            "interval": self._read_number(view.interval_entry, DEFAULT_INTERVAL, MIN_INTERVAL, MAX_INTERVAL, fix),
            "mode": view.mode_var.get(),
            "target_key": view.key_var.get(),
            "jitter": self._read_number(view.jitter_entry, DEFAULT_JITTER, MIN_JITTER, MAX_JITTER, fix),
            "limit_kind": limit_kind,
            "limit_value": self._read_number(
                view.limit_entry, DEFAULT_LIMIT_VALUE, MIN_LIMIT_VALUE, MAX_LIMIT_VALUE,
                fix and limit_kind != LIMIT_NEVER, whole=limit_kind == LIMIT_CLICKS,
            ),
            "start_delay": self._read_number(
                view.delay_entry, DEFAULT_START_DELAY, MIN_START_DELAY, MAX_START_DELAY, fix,
            ),
        }

    def _snapshot(self) -> dict:
        return {
            "version": CONFIG_VERSION,
            "active_profile": self._active,
            "profiles": {name: dict(s) for name, s in self._profiles.items()},
        }

    def save_settings(self, force=False, refresh=True):
        self._commit_view()
        if refresh:
            self._push_profiles()
        snapshot = self._snapshot()
        if not force and snapshot == self._last_saved:
            return
        save_config(snapshot)
        self._last_saved = snapshot


    def _poll(self):
        self._refresh_status()
        self._poll_id = self.root.after(self.STATUS_POLL_MS, self._poll)

    def _done_message(self):
        if not self.clicker.limit_reached:
            return None
        clicks = self.clicker.click_count
        if clicks:
            return f"Finished after {clicks:,} clicks"
        return "Finished · time limit reached"

    def _refresh_status(self):
        running = self.clicker.is_clicking
        waiting = running and self.clicker.is_waiting
        error = None if running else (self._error or self.clicker.last_error)
        done = None if (running or error) else self._done_message()
        state = (running, waiting, error, done)
        if state == self._shown_status:
            return
        self._shown_status = state

        if waiting:
            self.view.show_status("waiting")
        elif running:
            self.view.show_status("running")
        elif error:
            self.view.show_status("error", error)
        elif done:
            self.view.show_status("done", done)
        else:
            self.view.show_status("stopped")
        self.view.set_inputs_enabled(not running)


    def shutdown(self):
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None
        self.clicker.stop()
        self.save_settings(refresh=False)
        for hotkey in list(self._hotkey_handles):
            self._release_hotkey(hotkey)
        try:
            hotkeys.unhook_all()
        except Exception:
            logger.exception("Could not unhook keyboard")