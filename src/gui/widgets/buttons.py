from gui import theme
from gui.widgets.shapes import CanvasWidget, rounded_rect

_STYLES = {
    "primary": dict(bg=theme.ACCENT, hover=theme.ACCENT_HOVER, active=theme.ACCENT_ACTIVE, fg=theme.ACCENT_TEXT, border=None),
    "danger": dict(bg=theme.DANGER, hover=theme.DANGER_HOVER, active=theme.DANGER_ACTIVE, fg="#FFFFFF", border=None),
    "ghost": dict(bg=None, hover=theme.SURFACE_HOVER, active=theme.SURFACE_2, fg=theme.TEXT, border=theme.BORDER_STRONG),
    "subtle": dict(bg=theme.SURFACE_2, hover=theme.SURFACE_HOVER, active=theme.SURFACE, fg=theme.TEXT_SOFT, hover_fg=theme.TEXT, border=None),
    "quiet": dict(bg=None, hover=theme.SURFACE_HOVER, active=theme.SURFACE_2, fg=theme.TEXT_MUTED, hover_fg=theme.TEXT, border=None),
    "quiet_danger": dict(bg=None, hover=theme.DANGER_SOFT, active=theme.DANGER_SOFT, fg=theme.TEXT_MUTED, hover_fg=theme.DANGER_TEXT, border=None),
}


class Button(CanvasWidget):
    def __init__(self, parent, text, command=None, variant="ghost", font=None, padx=14, pady=7, radius=None):
        if variant not in _STYLES:
            raise ValueError(f"Unknown button variant: {variant!r}")
        self.command = command
        self._text = text
        self._variant = variant
        self._font = font or theme.font(10, "bold")
        self._padx, self._pady = theme.px(padx), theme.px(pady)
        self._radius = theme.px(radius if radius is not None else theme.RADIUS_SM)
        self._enabled = True
        self._hover = False
        self._pressed = False
        self._focused = False
        width, height = self._natural_size()
        super().__init__(parent, width, height, takefocus=1, cursor="hand2")
        self._base_bg = parent.cget("bg")
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Key-space>", self._on_key)
        self.bind("<Key-Return>", self._on_key)
        self.bind("<FocusIn>", lambda _e: self._set_focus(True))
        self.bind("<FocusOut>", lambda _e: self._set_focus(False))

    @property
    def text(self) -> str:
        return self._text

    def set_text(self, text: str) -> None:
        if text == self._text:
            return
        self._text = text
        width, _ = self._natural_size()
        self.configure(width=max(width, int(self.cget("width"))))
        self.redraw()

    def set_variant(self, variant: str) -> None:
        if variant not in _STYLES:
            raise ValueError(f"Unknown button variant: {variant!r}")
        if variant != self._variant:
            self._variant = variant
            self.redraw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if not self._enabled:
            self._hover = self._pressed = False
        self.configure(takefocus=1 if self._enabled else 0, cursor="hand2" if self._enabled else "arrow")
        self.redraw()

    def _natural_size(self):
        return (
            theme.measure(self._font, self._text) + 2 * self._padx,
            theme.line_height(self._font) + 2 * self._pady,
        )

    def _set_focus(self, focused):
        self._focused = focused
        self.redraw()

    def _on_enter(self, _event):
        self._hover = True
        self.redraw()

    def _on_leave(self, _event):
        self._hover = False
        self.redraw()

    def _on_press(self, _event):
        if self._enabled:
            self._pressed = True
            self.redraw()

    def _on_release(self, _event):
        fire = self._pressed and self._hover and self._enabled
        self._pressed = False
        self.redraw()
        if fire:
            self._invoke()

    def _on_key(self, _event):
        if self._enabled:
            self._invoke()
        return "break"

    def _invoke(self):
        if self.command is not None:
            self.command()

    def _colors(self):
        style = _STYLES[self._variant]
        base = style["bg"] or self._base_bg
        if not self._enabled:
            flat = style["bg"] is None and style["border"] is None
            return (base if flat else theme.SURFACE_2), theme.TEXT_DISABLED, (None if flat else theme.BORDER)
        if self._pressed and self._hover:
            bg = style["active"]
        elif self._hover:
            bg = style["hover"]
        else:
            bg = base
        fg = style.get("hover_fg", style["fg"]) if self._hover else style["fg"]
        return bg, fg, style["border"]

    def draw(self, width, height):
        bg, fg, border = self._colors()
        if self._focused:
            border = theme.TEXT_SOFT
        rounded_rect(self, 0, 0, width - 1, height - 1, self._radius, fill=bg, outline=border or bg)
        self.create_text(width / 2, height / 2, text=self._text, font=self._font, fill=fg)
