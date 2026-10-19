import tkinter as tk

from core.constants import FAILSAFE_CHOICES
from gui import theme
from gui.views.pages.base import CardPage
from gui.widgets.card import Card
from gui.widgets.segmented import SegmentedControl
from gui.widgets.switch import Switch


class SettingsPage(CardPage):
    def __init__(self, parent, settings: dict, on_change):
        super().__init__(parent)
        self._on_change = on_change
        self._loading = False

        failsafe_card = Card(self, "Fail-safe corner")
        self.failsafe_var = tk.StringVar(value=settings["failsafe"])
        SegmentedControl(failsafe_card.body, list(FAILSAFE_CHOICES), self.failsafe_var,
                         font=theme.font(9, "bold"), padx=10).pack(fill="x")
        failsafe_card.add_hint("Stops clicking as soon as the mouse reaches that corner of the screen")
        self.place(failsafe_card, 0, 0, span=2)

        self.topmost_var = tk.BooleanVar(value=settings["always_on_top"])
        self._switch_card("Always on top", self.topmost_var, "Keeps this window above the others", 0)

        self.sound_var = tk.BooleanVar(value=settings["sound"])
        self._switch_card("Sound", self.sound_var, "Beeps when clicking starts or stops", 1)

        for variable in (self.failsafe_var, self.topmost_var, self.sound_var):
            variable.trace_add("write", lambda *_: self._edited())

    def _switch_card(self, title, variable, hint, column):
        card = Card(self, title)
        Switch(card.body, variable).pack(anchor="w")
        card.add_hint(hint)
        self.place(card, 1, column)

    def load(self, settings: dict) -> None:
        self._loading = True
        try:
            self.failsafe_var.set(settings["failsafe"])
            self.topmost_var.set(bool(settings["always_on_top"]))
            self.sound_var.set(bool(settings["sound"]))
        finally:
            self._loading = False

    def read(self) -> dict:
        return {
            "failsafe": self.failsafe_var.get(),
            "always_on_top": bool(self.topmost_var.get()),
            "sound": bool(self.sound_var.get()),
        }

    def _edited(self) -> None:
        if not self._loading:
            self._on_change()
