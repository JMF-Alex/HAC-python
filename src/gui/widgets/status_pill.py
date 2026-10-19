import tkinter as tk

from gui import theme
from gui.widgets.shapes import RoundedFrame


class StatusPill(RoundedFrame):
    KINDS = {
        "running": ("Running", theme.RUNNING_DOT, theme.RUNNING_TEXT, theme.RUNNING_BG, theme.RUNNING_BORDER),
        "waiting": ("Starting", theme.WARNING, theme.WARNING, theme.WAITING_BG, theme.WAITING_BORDER),
        "stopped": ("Idle", theme.TEXT_MUTED, theme.TEXT_SOFT, theme.SURFACE, theme.BORDER),
        "error": ("Error", theme.DANGER, theme.ERROR_TEXT, theme.ERROR_BG, theme.ERROR_BORDER),
    }

    def __init__(self, parent):
        super().__init__(parent, fill=theme.SURFACE, outline=theme.BORDER, radius=theme.px(15))
        self._dot = tk.Label(self, text="●", font=theme.font(9), bd=0)
        self._dot.pack(side="left", padx=(theme.px(12), theme.px(6)), pady=theme.px(5))
        width = max(len(label) for label, *_ in self.KINDS.values())
        self._text = tk.Label(self, font=theme.font(10, "bold"), width=width, anchor="w", bd=0)
        self._text.pack(side="left", padx=(0, theme.px(12)), pady=theme.px(5))
        self.kind = None
        self.set_kind("stopped")

    def set_kind(self, kind: str) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"Unknown status kind: {kind!r}")
        if kind == self.kind:
            return
        label, dot, text, background, border = self.KINDS[kind]
        self.kind = kind
        self.configure(bg=background)
        self.set_colors(fill=background, outline=border)
        self._dot.configure(bg=background, fg=dot)
        self._text.configure(bg=background, fg=text, text=label)

    @property
    def text(self) -> str:
        return self._text.cget("text")
