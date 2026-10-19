from gui import theme
from gui.widgets.shapes import CanvasWidget, rounded_rect


class SegmentedControl(CanvasWidget):
    def __init__(self, parent, options, variable, font=None, padx=14, pady=6):
        self._choices = list(options)
        self._variable = variable
        self._font = font or theme.font(10, "bold")
        self._enabled = True
        self._hovered = None
        self._focused = False
        self._inset = theme.px(3)
        segment = max(theme.measure(self._font, o) for o in self._choices) + 2 * theme.px(padx)
        width = segment * len(self._choices) + 2 * self._inset
        height = theme.line_height(self._font) + 2 * theme.px(pady) + 2 * self._inset
        super().__init__(parent, width, height, takefocus=1, cursor="hand2")
        self.bind("<Motion>", lambda e: self._set_hover(self._option_at(e.x)))
        self.bind("<Leave>", lambda _e: self._set_hover(None))
        self.bind("<ButtonRelease-1>", lambda e: self._choose(self._option_at(e.x)))
        self.bind("<Left>", lambda _e: self._step(-1))
        self.bind("<Right>", lambda _e: self._step(1))
        self.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self.bind("<FocusOut>", lambda _e: self._set_focus(False))
        self._trace_id = variable.trace_add("write", lambda *_: self.redraw())
        self.bind("<Destroy>", self._on_destroy, add="+")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self._hovered = None
        self.configure(cursor="hand2" if self._enabled else "arrow", takefocus=1 if self._enabled else 0)
        self.redraw()

    def _on_destroy(self, event):
        if event.widget is self:
            try:
                self._variable.trace_remove("write", self._trace_id)
            except Exception:
                pass

    def _option_at(self, x):
        width = max(1, self.winfo_width() - 2 * self._inset)
        index = int((x - self._inset) * len(self._choices) / width)
        return self._choices[min(len(self._choices) - 1, max(0, index))]

    def _set_hover(self, option):
        if option != self._hovered:
            self._hovered = option
            self.redraw()

    def _set_focus(self, focused):
        self._focused = focused
        self.redraw()

    def _choose(self, option):
        if self._enabled:
            self._variable.set(option)

    def _step(self, delta):
        current = self._variable.get()
        index = self._choices.index(current) if current in self._choices else 0
        self._choose(self._choices[(index + delta) % len(self._choices)])
        return "break"

    def draw(self, width, height):
        inset = self._inset
        radius = theme.px(theme.RADIUS_SM)
        border = theme.TEXT_SOFT if self._focused and self._enabled else theme.BORDER_STRONG
        rounded_rect(self, 0, 0, width - 1, height - 1, radius, fill=theme.SURFACE_2, outline=border)
        segment = (width - 2 * inset) / len(self._choices)
        selected = self._variable.get()
        for index, option in enumerate(self._choices):
            x1 = inset + index * segment
            x2 = x1 + segment
            if option == selected:
                bg = theme.ACCENT if self._enabled else theme.ACCENT_DISABLED
                fg = theme.ACCENT_TEXT if self._enabled else theme.ACCENT_DISABLED_TEXT
            elif not self._enabled:
                bg, fg = None, theme.TEXT_DISABLED
            elif option == self._hovered:
                bg, fg = theme.SURFACE_HOVER, theme.TEXT
            else:
                bg, fg = None, theme.TEXT_MUTED
            if bg is not None:
                rounded_rect(self, x1, inset, x2 - 1, height - 1 - inset, radius - inset, fill=bg, outline=bg)
            self.create_text((x1 + x2) / 2, height / 2, text=option, font=self._font, fill=fg)
