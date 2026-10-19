import re
import tkinter as tk

from core.constants import (
    FAILSAFE_CHOICES,
    KEY_CHOICES,
    LIMIT_CLICKS,
    LIMIT_KINDS,
    LIMIT_NEVER,
    LIMIT_TIME,
    MODE_HOLD,
    MODES,
)
from core.paths import resource_path
from gui import icon, theme
from gui.widgets import dialogs
from gui.widgets.buttons import FlatButton
from gui.widgets.cards import Card
from gui.widgets.comboboxes import FlatCombobox
from gui.widgets.entries import FlatEntry
from gui.widgets.indicators import Keycap, StatusPill
from gui.widgets.profile_sidebar import ProfileSidebar, ProfileSummary
from gui.widgets.segmented import SegmentedControl

_INTERVAL_RE = re.compile(r"^\d*[.,]?\d*$")
MAX_MESSAGE_CHARS = 70
LOGO_SIZE = 32
CARD_HEIGHT = 128

PAGE_BASIC = "Basic"
PAGE_ADVANCED = "Advanced"
PAGE_SETTINGS = "Settings"
PAGES = (PAGE_BASIC, PAGE_ADVANCED, PAGE_SETTINGS)

ON, OFF = "On", "Off"

_LIMIT_HINTS = {
    LIMIT_NEVER: "Runs until you stop it",
    LIMIT_CLICKS: "Stops after this many clicks",
    LIMIT_TIME: "Stops after this many seconds",
}
_LIMIT_UNITS = {LIMIT_NEVER: "", LIMIT_CLICKS: "clicks", LIMIT_TIME: "seconds"}
HOLD_CLICKS_HINT = "Click limits only apply in Click mode"

_BUTTON_TEXT = {"running": "Stop clicking", "waiting": "Cancel start"}


def format_number(value) -> str:
    value = float(value)
    return str(int(value)) if value.is_integer() else str(value)


def _clip(text: str) -> str:
    return text if len(text) <= MAX_MESSAGE_CHARS else text[:MAX_MESSAGE_CHARS - 1] + "…"


class LayoutManager:
    APP_NAME = "HAutoClicker"

    def __init__(self, root, controller, version):
        self.root = root
        self.controller = controller
        self.settings = controller.active_settings
        self.version = version
        self._hotkey = None
        self._error_text = None
        self._note_text = None
        self._save_reset_id = None
        self._inputs_enabled = True
        self._loading_settings = False
        self._hint_mode = None
        self._pages = {}
        self.setup_layout()

    @staticmethod
    def _is_valid_interval(proposed: str) -> bool:
        return _INTERVAL_RE.match(proposed) is not None


    def setup_layout(self):
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._number_check = (self.root.register(self._is_valid_interval), "%P")

        self.logo = icon.load_icon_photo(resource_path("assets", "icon.ico"), LOGO_SIZE, master=self.root)
        self.sidebar = ProfileSidebar(
            self.root, self.APP_NAME, self.version, logo=self.logo,
            on_select=self.controller.select_profile, on_add=self.controller.add_profile,
            on_rename=self.controller.rename_profile, on_delete=self.controller.delete_profile,
            on_duplicate=self.controller.duplicate_profile,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.set_profiles(self._summaries(self.controller.profiles), active=self.controller.active_name)
        tk.Frame(self.root, width=1, bg=theme.BORDER).grid(row=0, column=1, sticky="ns")

        main = tk.Frame(self.root, bg=theme.BG)
        main.grid(row=0, column=2, sticky="nsew")
        content = tk.Frame(main, bg=theme.BG)
        content.pack(fill="both", expand=True, padx=36, pady=(30, 28))

        self._build_header(content)
        self._build_pages(content)
        self._build_action(content)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=theme.BG)
        header.pack(fill="x")
        titles = tk.Frame(header, bg=theme.BG)
        titles.pack(side="left")
        self.title_label = tk.Label(
            titles, text=self.controller.active_name, font=theme.font(20, "bold"), fg=theme.TEXT, bg=theme.BG, anchor="w",
        )
        self.title_label.pack(fill="x")
        self.page_var = tk.StringVar(value=PAGE_BASIC)
        self.page_control = SegmentedControl(titles, list(PAGES), self.page_var, font=theme.font(9, "bold"))
        self.page_control.pack(anchor="w", pady=(6, 0))

        actions = tk.Frame(header, bg=theme.BG)
        actions.pack(side="right")
        self.status_pill = StatusPill(actions)
        self.status_pill.pack(side="right")
        self.save_button = FlatButton(actions, "Save", command=self._on_save, variant="ghost", pady=6)
        self.save_button.pack(side="right", padx=(0, 10))

    def _build_pages(self, parent):
        host = tk.Frame(parent, bg=theme.BG)
        host.pack(fill="x", pady=(20, 0))
        host.grid_columnconfigure(0, weight=1)
        self._pages = {
            PAGE_BASIC: self._build_basic(host),
            PAGE_ADVANCED: self._build_advanced(host),
            PAGE_SETTINGS: self._build_settings(host),
        }
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.page_var.trace_add("write", lambda *_: self._show_page())
        self._show_page()

    def _show_page(self):
        selected = self.page_var.get()
        for name, page in self._pages.items():
            if name == selected:
                page.grid()
            else:
                page.grid_remove()

    @staticmethod
    def _make_grid(parent):
        grid = tk.Frame(parent, bg=theme.BG)
        grid.grid_columnconfigure((0, 1), weight=1, uniform="cards")
        grid.grid_rowconfigure((0, 1), weight=1, uniform="rows")
        return grid

    @staticmethod
    def _place(card, row, column, span=1):
        if span == 2:
            padx = 0
        else:
            padx = (0, 8) if column == 0 else (8, 0)
        card.grid(
            row=row, column=column, columnspan=span, sticky="nsew",
            padx=padx, pady=(0, 16) if row == 0 else 0,
        )
        card.configure(height=CARD_HEIGHT)
        card.pack_propagate(False)

    def _number_entry(self, parent, value):
        entry = FlatEntry(parent, width=9)
        entry.insert(0, format_number(value))
        entry.configure(validate="key", validatecommand=self._number_check)
        return entry

    def _entry_row(self, card, value, unit):
        row = tk.Frame(card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        entry = self._number_entry(row, value)
        entry.pack(side="left")
        tk.Label(row, text=unit, font=theme.font(10), fg=theme.TEXT_MUTED, bg=theme.SURFACE).pack(side="left", padx=(10, 0))
        return entry

    def _build_basic(self, parent):
        grid = self._make_grid(parent)

        interval_card = Card(grid, "Interval")
        self.interval_entry = self._entry_row(interval_card, self.settings["interval"], "seconds")
        interval_card.add_hint("Delay between clicks · minimum 0.001")
        self._place(interval_card, 0, 0)

        mode_card = Card(grid, "Mode")
        self.mode_var = tk.StringVar(value=self.settings["mode"])
        self.mode_control = SegmentedControl(mode_card.body, list(MODES), self.mode_var)
        self.mode_control.pack(fill="x")
        mode_card.add_hint("Click repeats · Hold keeps it pressed")
        self._place(mode_card, 0, 1)

        key_card = Card(grid, "Key / button")
        self.key_var = tk.StringVar(value=self.settings["target_key"])
        self.key_combo = FlatCombobox(key_card.body, KEY_CHOICES, self.key_var)
        self.key_combo.pack(fill="x")
        key_card.add_hint("Mouse buttons start with mouse_")
        self._place(key_card, 1, 0)

        hotkey_card = Card(grid, "Hotkey")
        row = tk.Frame(hotkey_card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        self.hotkey_keycap = Keycap(row, self.settings["hotkey"] or "-")
        self.hotkey_keycap.pack(side="left")
        self.change_hotkey_button = FlatButton(
            row, "Change", command=self.controller.change_hotkey, variant="ghost", pady=6,
        )
        self.change_hotkey_button.pack(side="right")
        hotkey_card.add_hint("Works from any window")
        self._place(hotkey_card, 1, 1)
        return grid

    def _build_advanced(self, parent):
        grid = self._make_grid(parent)

        jitter_card = Card(grid, "Variation")
        self.jitter_entry = self._entry_row(jitter_card, self.settings["jitter"], "%")
        jitter_card.add_hint("Each delay varies by up to ± this %")
        self._place(jitter_card, 0, 0)

        delay_card = Card(grid, "Start delay")
        self.delay_entry = self._entry_row(delay_card, self.settings["start_delay"], "seconds")
        delay_card.add_hint("Countdown before the first click")
        self._place(delay_card, 0, 1)

        self.limit_card = Card(grid, "Stop after")
        row = tk.Frame(self.limit_card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        self.limit_var = tk.StringVar(value=self.settings["limit_kind"])
        self.limit_control = SegmentedControl(row, list(LIMIT_KINDS), self.limit_var)
        self.limit_control.pack(side="left")
        self.limit_entry = self._number_entry(row, self.settings["limit_value"])
        self.limit_entry.pack(side="left", padx=(16, 0))
        self.limit_unit = tk.Label(
            row, font=theme.font(10), fg=theme.TEXT_MUTED, bg=theme.SURFACE, width=7, anchor="w",
        )
        self.limit_unit.pack(side="left", padx=(10, 0))
        self._place(self.limit_card, 1, 0, span=2)

        self.limit_var.trace_add("write", lambda *_: self._sync_limit())
        self.mode_var.trace_add("write", lambda *_: self._sync_limit())
        self._sync_limit()
        return grid

    def _build_settings(self, parent):
        grid = self._make_grid(parent)
        defaults = self.controller.settings

        failsafe_card = Card(grid, "Fail-safe")
        self.failsafe_var = tk.StringVar(value=defaults["failsafe"])
        SegmentedControl(failsafe_card.body, list(FAILSAFE_CHOICES), self.failsafe_var).pack(anchor="w")
        failsafe_card.add_hint("Stops clicking as soon as the mouse reaches that corner of the screen")
        self._place(failsafe_card, 0, 0, span=2)

        topmost_card = Card(grid, "Always on top")
        self.topmost_var = tk.StringVar(value=ON if defaults["always_on_top"] else OFF)
        SegmentedControl(topmost_card.body, [OFF, ON], self.topmost_var).pack(fill="x")
        topmost_card.add_hint("Keeps this window above the others")
        self._place(topmost_card, 1, 0)

        sound_card = Card(grid, "Sound")
        self.sound_var = tk.StringVar(value=ON if defaults["sound"] else OFF)
        SegmentedControl(sound_card.body, [OFF, ON], self.sound_var).pack(fill="x")
        sound_card.add_hint("Beeps when clicking starts or stops")
        self._place(sound_card, 1, 1)

        for variable in (self.failsafe_var, self.topmost_var, self.sound_var):
            variable.trace_add("write", lambda *_: self._on_settings_edited())
        return grid

    def _build_action(self, parent):
        self.toggle_button = FlatButton(
            parent, "Start clicking", command=self.controller.toggle, variant="primary",
            font=theme.font(12, "bold"), pady=15,
        )
        self.toggle_button.pack(fill="x", pady=(26, 0))

        hint = tk.Frame(parent, bg=theme.BG)
        hint.pack(pady=(14, 0))
        self._hint_prefix = tk.Label(hint, text="Press", font=theme.font(9), fg=theme.TEXT_MUTED, bg=theme.BG)
        self._hint_key = Keycap(hint, compact=True)
        self.hint_label = tk.Label(hint, font=theme.font(9), fg=theme.TEXT_MUTED, bg=theme.BG)
        self._render_hint()


    def show_status(self, kind: str, message=None) -> None:
        running = kind in ("running", "waiting")
        self.status_pill.set_kind("stopped" if kind == "done" else kind)
        self.toggle_button.set_text(_BUTTON_TEXT.get(kind, "Start clicking"))
        self.toggle_button.set_variant("danger" if running else "primary")
        self._error_text = message if kind == "error" else None
        self._note_text = message if kind in ("done", "running", "waiting") else None
        self._render_hint()

    def show_hotkey(self, hotkey) -> None:
        self._hotkey = hotkey
        self.hotkey_keycap.set_text(hotkey or "-")
        self._render_hint()

    def show_hotkey_waiting(self) -> None:
        self.hotkey_keycap.set_waiting()

    def set_profile_title(self, name: str) -> None:
        self.title_label.configure(text=name)

    def show_number(self, entry, value) -> None:
        entry.set_text(format_number(value))

    def show_profile(self, name: str, settings: dict) -> None:
        self.set_profile_title(name)
        self.show_number(self.interval_entry, settings["interval"])
        self.show_number(self.jitter_entry, settings["jitter"])
        self.show_number(self.delay_entry, settings["start_delay"])
        self.show_number(self.limit_entry, settings["limit_value"])
        self.mode_var.set(settings["mode"])
        self.key_var.set(settings["target_key"])
        self.limit_var.set(settings["limit_kind"])
        self.show_hotkey(settings["hotkey"])

    def show_settings(self, settings: dict) -> None:
        self._loading_settings = True
        try:
            self.failsafe_var.set(settings["failsafe"])
            self.topmost_var.set(ON if settings["always_on_top"] else OFF)
            self.sound_var.set(ON if settings["sound"] else OFF)
        finally:
            self._loading_settings = False
        self.set_always_on_top(settings["always_on_top"])

    def read_settings(self) -> dict:
        return {
            "failsafe": self.failsafe_var.get(),
            "always_on_top": self.topmost_var.get() == ON,
            "sound": self.sound_var.get() == ON,
        }

    def _on_settings_edited(self) -> None:
        if not self._loading_settings:
            self.controller.settings_changed()

    def set_always_on_top(self, enabled: bool) -> None:
        try:
            self.root.attributes("-topmost", bool(enabled))
        except tk.TclError:
            pass

    def beep(self) -> None:
        self.root.bell()

    def pointer_position(self):
        x, y = self.root.winfo_pointerxy()
        return x, y, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def show_profiles(self, profiles: dict, active: str) -> None:
        summaries = self._summaries(profiles)
        self.root.after_idle(lambda: self.sidebar.set_profiles(summaries, active=active))

    def ask_profile_name(self, title, initial, validate, confirm_text="Save"):
        return dialogs.ask_name(self.root, title, "Profile name", initial, validate, confirm_text)

    def confirm_delete(self, name: str) -> bool:
        return dialogs.confirm(
            self.root, "Delete profile", f"Delete “{name}”? This can't be undone.",
            confirm_text="Delete", danger=True,
        )

    def show_message(self, title: str, message: str) -> None:
        dialogs.confirm(self.root, title, message, cancel_text=None)

    @staticmethod
    def _summaries(profiles: dict) -> list:
        return [
            ProfileSummary(name, s["hotkey"] or "-", s["interval"], s["mode"], s["target_key"])
            for name, s in profiles.items()
        ]

    def set_inputs_enabled(self, enabled: bool) -> None:
        self._inputs_enabled = bool(enabled)
        self.interval_entry.set_enabled(enabled)
        self.mode_control.set_enabled(enabled)
        self.key_combo.set_enabled(enabled)
        self.jitter_entry.set_enabled(enabled)
        self.delay_entry.set_enabled(enabled)
        self.limit_control.set_enabled(enabled)
        self._sync_limit()

    def _sync_limit(self) -> None:
        kind = self.limit_var.get()
        self.limit_entry.set_enabled(self._inputs_enabled and kind != LIMIT_NEVER)
        self.limit_unit.configure(text=_LIMIT_UNITS.get(kind, ""))
        clicks_while_holding = kind == LIMIT_CLICKS and self.mode_var.get() == MODE_HOLD
        self.limit_card.add_hint(HOLD_CLICKS_HINT if clicks_while_holding else _LIMIT_HINTS.get(kind, ""))

    @property
    def hint_text(self) -> str:
        parts = []
        if self._hint_prefix.winfo_manager():
            parts += [self._hint_prefix.cget("text"), self._hint_key.text]
        parts.append(self.hint_label.cget("text"))
        return " ".join(parts)


    def _render_hint(self):
        if self._error_text:
            mode, text, color = "text", _clip(self._error_text), theme.WARNING
        elif self._note_text:
            mode, text, color = "text", _clip(self._note_text), theme.TEXT_MUTED
        elif self._hotkey:
            mode, text, color = "keyed", "from any window to start or stop", theme.TEXT_MUTED
        else:
            mode, text, color = "text", "No hotkey set. Use Change to pick one", theme.TEXT_MUTED
        self.hint_label.configure(text=text, fg=color)
        if mode == "text" and self._hint_mode == "text":
            return 
        self._hint_mode = mode
        for widget in (self._hint_prefix, self._hint_key, self.hint_label):
            widget.pack_forget()
        if mode == "keyed":
            self._hint_key.set_text(self._hotkey)
            self._hint_prefix.pack(side="left")
            self._hint_key.pack(side="left", padx=6)
        self.hint_label.pack(side="left")

    def _on_save(self):
        self.controller.save_settings(force=True)
        if self._save_reset_id is not None:
            self.root.after_cancel(self._save_reset_id)
        self.save_button.set_text("Saved")
        self._save_reset_id = self.root.after(1400, self._reset_save_button)

    def _reset_save_button(self):
        self._save_reset_id = None
        self.save_button.set_text("Save")