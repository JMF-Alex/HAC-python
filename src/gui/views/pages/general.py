import tkinter as tk

from core.constants import KEY_CHOICES, MODES
from gui import theme
from gui.views.pages.base import CardPage
from gui.widgets.buttons import Button
from gui.widgets.card import Card
from gui.widgets.dropdown import Dropdown
from gui.widgets.keycap import Keycap
from gui.widgets.segmented import SegmentedControl

HOTKEY_HINT = "Works from any window"
HOTKEY_WAITING_HINT = "Press Esc to keep the current one"


class GeneralPage(CardPage):
    def __init__(self, parent, settings: dict, on_change_hotkey):
        super().__init__(parent)

        interval_card = Card(self, "Interval")
        self.interval_entry = self.number_row(interval_card, settings["interval"], "seconds")
        interval_card.add_hint("Delay between clicks · minimum 0.001")
        self.place(interval_card, 0, 0)

        mode_card = Card(self, "Mode")
        self.mode_var = tk.StringVar(value=settings["mode"])
        self.mode_control = SegmentedControl(mode_card.body, list(MODES), self.mode_var)
        self.mode_control.pack(fill="x")
        mode_card.add_hint("Click repeats · Hold keeps it pressed")
        self.place(mode_card, 0, 1)

        key_card = Card(self, "Key / button")
        self.key_var = tk.StringVar(value=settings["target_key"])
        self.key_combo = Dropdown(key_card.body, KEY_CHOICES, self.key_var)
        self.key_combo.pack(fill="x")
        key_card.add_hint("Mouse buttons start with mouse_")
        self.place(key_card, 1, 0)

        self._hotkey_card = Card(self, "Hotkey")
        row = tk.Frame(self._hotkey_card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        self.hotkey_keycap = Keycap(row, settings["hotkey"] or "-")
        self.hotkey_keycap.pack(side="left")
        self.change_hotkey_button = Button(row, "Change", command=on_change_hotkey, variant="ghost", pady=6)
        self.change_hotkey_button.pack(side="right")
        self._hotkey_card.add_hint(HOTKEY_HINT)
        self.place(self._hotkey_card, 1, 1)

    def set_enabled(self, enabled: bool) -> None:
        self.interval_entry.set_enabled(enabled)
        self.mode_control.set_enabled(enabled)
        self.key_combo.set_enabled(enabled)

    def show_hotkey(self, hotkey) -> None:
        self.hotkey_keycap.set_text(hotkey or "-")
        self._hotkey_card.add_hint(HOTKEY_HINT)

    def show_hotkey_waiting(self) -> None:
        self.hotkey_keycap.set_waiting()
        self._hotkey_card.add_hint(HOTKEY_WAITING_HINT)
