import re
import tkinter as tk

from gui import theme
from gui.widgets.shapes import RoundedFrame

_NUMBER_RE = re.compile(r"^\d*[.,]?\d*$")


class FieldFrame(RoundedFrame):
    def __init__(self, parent):
        super().__init__(parent, fill=theme.SURFACE_2, outline=theme.BORDER_STRONG, radius=theme.px(theme.RADIUS_SM))
        self._focused = False
        self._enabled = True

    def _attach(self, widget, padx, pady):
        widget.pack(fill="x", padx=padx, pady=pady)
        widget.bind("<FocusIn>", lambda _e: self._set_focus(True), add="+")
        widget.bind("<FocusOut>", lambda _e: self._set_focus(False), add="+")
        self.canvas.bind("<Button-1>", lambda _e: self._enabled and widget.focus_set())

    def _set_focus(self, focused):
        self._focused = focused
        self._paint()

    def _paint(self):
        fill = theme.SURFACE_2 if self._enabled else theme.SURFACE_DISABLED
        outline = theme.ACCENT if self._focused and self._enabled else (theme.BORDER_STRONG if self._enabled else theme.BORDER)
        self.configure(bg=fill)
        self.set_colors(fill=fill, outline=outline)


class Field(FieldFrame):
    def __init__(self, parent, width=10, numeric=False, font=None):
        super().__init__(parent)
        self.entry = tk.Entry(
            self, width=width, bg=theme.SURFACE_2, fg=theme.TEXT, insertbackground=theme.TEXT, insertwidth=1,
            relief="flat", bd=0, highlightthickness=0,
            disabledbackground=theme.SURFACE_DISABLED, disabledforeground=theme.TEXT_DISABLED,
            selectbackground=theme.ACCENT, selectforeground=theme.ACCENT_TEXT, font=font or theme.font(11),
        )
        if numeric:
            check = self.register(lambda proposed: _NUMBER_RE.match(proposed) is not None)
            self.entry.configure(validate="key", validatecommand=(check, "%P"))
        self._attach(self.entry, theme.px(11), theme.px(8))

    def get(self) -> str:
        return self.entry.get()

    def set_text(self, text: str) -> None:
        state = str(self.entry.cget("state"))
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.entry.configure(state=state)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self.entry.configure(state="normal" if enabled else "disabled")
        self._paint()
