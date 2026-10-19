from tkinter import ttk

from gui import theme
from gui.widgets.field import FieldFrame


class Dropdown(FieldFrame):
    def __init__(self, parent, values, variable, width=12):
        super().__init__(parent)
        self.combo = ttk.Combobox(
            self, values=list(values), textvariable=variable, width=width,
            state="readonly", style="Flat.TCombobox", font=theme.font(10),
        )
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self.combo.selection_clear(), add="+")
        self._attach(self.combo, theme.px(6), theme.px(5))

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.combo.configure(state="readonly" if enabled else "disabled")
        self._paint()
