import tkinter as tk

from gui import theme
from gui.formatting import format_number
from gui.widgets.field import Field


class CardPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=theme.BG)
        self.grid_columnconfigure((0, 1), weight=1, uniform="cards")
        self.grid_rowconfigure((0, 1), weight=1, uniform="rows")

    @staticmethod
    def place(card, row, column, span=1):
        gap = theme.px(8)
        padx = 0 if span == 2 else ((0, gap) if column == 0 else (gap, 0))
        card.grid(row=row, column=column, columnspan=span, sticky="nsew", padx=padx,
                  pady=(0, 2 * gap) if row == 0 else 0)

    @staticmethod
    def number_row(card, value, unit):
        row = tk.Frame(card.body, bg=theme.SURFACE)
        row.pack(fill="x")
        field = Field(row, width=9, numeric=True)
        field.set_text(format_number(value))
        field.pack(side="left")
        tk.Label(row, text=unit, font=theme.font(10), fg=theme.TEXT_MUTED, bg=theme.SURFACE).pack(
            side="left", padx=(theme.px(10), 0),
        )
        return field
