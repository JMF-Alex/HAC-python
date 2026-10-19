import tkinter as tk

from gui import theme


class Keycap(tk.Frame):
    WAITING_TEXT = "Press a key"

    def __init__(self, parent, text: str = "-", compact: bool = False):
        super().__init__(parent, bg=theme.KEY_EDGE)
        self._label = tk.Label(
            self, text=text, font=theme.mono(9 if compact else 12, "bold"), fg=theme.TEXT, bg=theme.KEY_FACE,
            padx=theme.px(7 if compact else 16), pady=theme.px(1 if compact else 6), bd=0,
        )
        self._label.pack(padx=1, pady=(1, theme.px(2 if compact else 3)))

    def set_text(self, text: str) -> None:
        self._set_waiting(False)
        self._label.configure(text=text)

    def set_waiting(self) -> None:
        self._set_waiting(True)
        self._label.configure(text=self.WAITING_TEXT)

    @property
    def text(self) -> str:
        return self._label.cget("text")

    def _set_waiting(self, waiting: bool) -> None:
        self.configure(bg=theme.WARNING_EDGE if waiting else theme.KEY_EDGE)
        self._label.configure(fg=theme.WARNING if waiting else theme.TEXT)
