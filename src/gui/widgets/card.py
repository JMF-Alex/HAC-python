import tkinter as tk

from gui import theme
from gui.widgets.shapes import RoundedFrame


class Card(RoundedFrame):
    def __init__(self, parent, title: str):
        super().__init__(parent, fill=theme.SURFACE, outline=theme.BORDER, radius=theme.px(theme.RADIUS))
        pad = theme.px(18)
        tk.Label(
            self, text=title.upper(), font=theme.font(8, "bold"), fg=theme.TEXT_MUTED, bg=theme.SURFACE, anchor="w",
        ).pack(fill="x", padx=pad, pady=(theme.px(16), 0))
        self._hint = tk.Label(
            self, text="", font=theme.font(9), fg=theme.TEXT_FAINT, bg=theme.SURFACE, anchor="w", justify="left",
        )
        self._hint.pack(side="bottom", fill="x", padx=pad, pady=(theme.px(10), theme.px(16)))
        self.body = tk.Frame(self, bg=theme.SURFACE)
        self.body.pack(fill="x", padx=pad, pady=(theme.px(10), 0))

    def add_hint(self, text: str) -> None:
        self._hint.configure(text=text)
