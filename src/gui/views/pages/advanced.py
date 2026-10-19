import tkinter as tk

from core.constants import LIMIT_CLICKS, LIMIT_KINDS, LIMIT_NEVER, LIMIT_TIME, MODE_HOLD
from gui import theme
from gui.formatting import format_number
from gui.views.pages.base import CardPage
from gui.widgets.card import Card
from gui.widgets.field import Field
from gui.widgets.segmented import SegmentedControl

_LIMIT_HINTS = {
    LIMIT_NEVER: "Runs until you stop it",
    LIMIT_CLICKS: "Stops after this many clicks",
    LIMIT_TIME: "Stops after this many seconds",
}
_LIMIT_UNITS = {LIMIT_NEVER: "", LIMIT_CLICKS: "clicks", LIMIT_TIME: "seconds"}
HOLD_CLICKS_HINT = "Click limits only apply in Click mode"


class AdvancedPage(CardPage):
    def __init__(self, parent, settings: dict, mode_var):
        super().__init__(parent)
        self._mode_var = mode_var
        self._enabled = True

        jitter_card = Card(self, "Variation")
        self.jitter_entry = self.number_row(jitter_card, settings["jitter"], "%")
        jitter_card.add_hint("Each delay varies by up to ± this %")
        self.place(jitter_card, 0, 0)

        delay_card = Card(self, "Start delay")
        self.delay_entry = self.number_row(delay_card, settings["start_delay"], "seconds")
        delay_card.add_hint("Countdown before the first click")
        self.place(delay_card, 0, 1)

        self._limit_card = Card(self, "Stop after")
        row = tk.Frame(self._limit_card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        self.limit_var = tk.StringVar(value=settings["limit_kind"])
        self.limit_control = SegmentedControl(row, list(LIMIT_KINDS), self.limit_var)
        self.limit_control.pack(side="left")
        self.limit_entry = Field(row, width=9, numeric=True)
        self.limit_entry.set_text(format_number(settings["limit_value"]))
        self.limit_entry.pack(side="left", padx=(theme.px(16), 0))
        self._limit_unit = tk.Label(
            row, font=theme.font(10), fg=theme.TEXT_MUTED, bg=theme.SURFACE, width=7, anchor="w",
        )
        self._limit_unit.pack(side="left", padx=(theme.px(10), 0))
        self.place(self._limit_card, 1, 0, span=2)

        self.limit_var.trace_add("write", lambda *_: self.sync_limit())
        mode_var.trace_add("write", lambda *_: self.sync_limit())
        self.sync_limit()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.jitter_entry.set_enabled(enabled)
        self.delay_entry.set_enabled(enabled)
        self.limit_control.set_enabled(enabled)
        self.sync_limit()

    def sync_limit(self) -> None:
        kind = self.limit_var.get()
        self.limit_entry.set_enabled(self._enabled and kind != LIMIT_NEVER)
        self._limit_unit.configure(text=_LIMIT_UNITS.get(kind, ""))
        clicks_while_holding = kind == LIMIT_CLICKS and self._mode_var.get() == MODE_HOLD
        self._limit_card.add_hint(HOLD_CLICKS_HINT if clicks_while_holding else _LIMIT_HINTS.get(kind, ""))
