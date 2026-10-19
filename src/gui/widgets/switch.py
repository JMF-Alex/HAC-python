from gui import theme
from gui.widgets.shapes import CanvasWidget, rounded_rect


class Switch(CanvasWidget):
    def __init__(self, parent, variable):
        self._variable = variable
        self._hover = False
        self._focused = False
        super().__init__(parent, theme.px(42), theme.px(24), takefocus=1, cursor="hand2")
        self.bind("<Enter>", lambda _e: self._set(hover=True))
        self.bind("<Leave>", lambda _e: self._set(hover=False))
        self.bind("<ButtonRelease-1>", lambda _e: self._toggle())
        self.bind("<Key-space>", lambda _e: self._toggle())
        self.bind("<Key-Return>", lambda _e: self._toggle())
        self.bind("<FocusIn>", lambda _e: self._set(focused=True))
        self.bind("<FocusOut>", lambda _e: self._set(focused=False))
        self._trace_id = variable.trace_add("write", lambda *_: self.redraw())
        self.bind("<Destroy>", self._on_destroy, add="+")

    def _on_destroy(self, event):
        if event.widget is self:
            try:
                self._variable.trace_remove("write", self._trace_id)
            except Exception:
                pass

    def _set(self, hover=None, focused=None):
        if hover is not None:
            self._hover = hover
        if focused is not None:
            self._focused = focused
        self.redraw()

    def _toggle(self):
        self._variable.set(not self._variable.get())
        return "break"

    def draw(self, width, height):
        on = bool(self._variable.get())
        if on:
            track = theme.ACCENT_HOVER if self._hover else theme.ACCENT
        else:
            track = theme.SURFACE_HOVER if self._hover else theme.BORDER_STRONG
        outline = theme.TEXT_SOFT if self._focused else track
        rounded_rect(self, 0, 0, width - 1, height - 1, height / 2, fill=track, outline=outline)
        gap = theme.px(3)
        knob = height - 2 * gap
        x = width - gap - knob if on else gap
        self.create_oval(x, gap, x + knob - 1, gap + knob - 1, fill="#FFFFFF", outline="")
