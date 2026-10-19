import tkinter as tk

from gui import theme


class Tabs(tk.Frame):
    def __init__(self, parent, options, variable):
        bg = parent.cget("bg")
        super().__init__(parent, bg=bg)
        self._bg = bg
        self._variable = variable
        self._hovered = None
        self._tabs = {}
        row = tk.Frame(self, bg=bg)
        row.pack(fill="x")
        for option in options:
            tab = tk.Frame(row, bg=bg, cursor="hand2")
            tab.pack(side="left", padx=(0, theme.px(24)))
            label = tk.Label(tab, text=option, font=theme.font(10, "bold"), bg=bg, bd=0, cursor="hand2")
            label.pack(pady=(0, theme.px(9)))
            bar = tk.Frame(tab, height=theme.px(2), bg=bg)
            bar.pack(fill="x")
            for widget in (tab, label):
                widget.bind("<Enter>", lambda _e, o=option: self._set_hover(o))
                widget.bind("<Leave>", lambda _e: self._set_hover(None))
                widget.bind("<ButtonRelease-1>", lambda _e, o=option: variable.set(o))
            self._tabs[option] = (label, bar)
        tk.Frame(self, height=1, bg=theme.BORDER).pack(fill="x")
        self._trace_id = variable.trace_add("write", lambda *_: self._paint())
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._paint()

    def _on_destroy(self, event):
        if event.widget is self:
            try:
                self._variable.trace_remove("write", self._trace_id)
            except Exception:
                pass

    def _set_hover(self, option):
        self._hovered = option
        self._paint()

    def _paint(self):
        selected = self._variable.get()
        for option, (label, bar) in self._tabs.items():
            if option == selected:
                fg, line = theme.TEXT, theme.ACCENT
            else:
                fg, line = (theme.TEXT_SOFT if option == self._hovered else theme.TEXT_MUTED), self._bg
            label.configure(fg=fg)
            bar.configure(bg=line)
