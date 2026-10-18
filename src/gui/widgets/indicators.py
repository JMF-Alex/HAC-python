import tkinter as tk

from gui import theme


class Keycap(tk.Frame):
    WAITING_TEXT = "Press a key"

    def __init__(self, parent, text: str = "-", compact: bool = False):
        super().__init__(parent, bg=theme.KEY_EDGE)
        self._label = tk.Label(
            self, text=text, font=theme.mono(9 if compact else 12, "bold"), fg=theme.TEXT, bg=theme.KEY_FACE,
            padx=7 if compact else 16, pady=1 if compact else 6, bd=0,
        )
        self._label.pack(padx=1, pady=(1, 2 if compact else 3))

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


class StatusPill(tk.Frame):
    KINDS = {
        "running": ("Running", theme.ACCENT, theme.RUNNING_TEXT, theme.RUNNING_BG, theme.RUNNING_BORDER),
        "waiting": ("Starting", theme.WARNING, theme.TEXT_SOFT, theme.SURFACE, theme.BORDER),
        "stopped": ("Stopped", theme.TEXT_MUTED, theme.TEXT_SOFT, theme.SURFACE, theme.BORDER),
        "error": ("Error", theme.WARNING, theme.ERROR_TEXT, theme.ERROR_BG, theme.ERROR_BORDER),
    }

    def __init__(self, parent):
        super().__init__(parent, highlightthickness=1)
        self._dot = tk.Label(self, text="●", font=theme.font(9))
        self._dot.pack(side="left", padx=(12, 6), pady=6)
        self._text = tk.Label(self, font=theme.font(10, "bold"), width=8, anchor="w")
        self._text.pack(side="left", padx=(0, 14), pady=6)
        self.kind = None
        self.set_kind("stopped")

    def set_kind(self, kind: str) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"Unknown status kind: {kind!r}")
        label, dot, text, background, border = self.KINDS[kind]
        self.kind = kind
        self.configure(bg=background, highlightbackground=border)
        self._dot.configure(bg=background, fg=dot)
        self._text.configure(bg=background, fg=text, text=label)

    @property
    def text(self) -> str:
        return self._text.cget("text")
