import tkinter as tk

from gui import theme


class FlatEntry(tk.Entry):
    def __init__(self, parent, **kwargs):
        options = dict(
            bg=theme.SURFACE_2, fg=theme.TEXT, insertbackground=theme.TEXT, insertwidth=1,
            relief="flat", bd=6, highlightthickness=1,
            highlightbackground=theme.BORDER_STRONG, highlightcolor=theme.ACCENT,
            disabledbackground=theme.SURFACE_DISABLED, disabledforeground=theme.TEXT_DISABLED,
            selectbackground=theme.ACCENT, selectforeground=theme.ACCENT_TEXT, font=theme.font(11),
        )
        options.update(kwargs)
        super().__init__(parent, **options)

    def set_enabled(self, enabled: bool) -> None:
        self.configure(state="normal" if enabled else "disabled")

    def set_text(self, text: str) -> None:
        state = str(self.cget("state"))
        self.configure(state="normal")
        self.delete(0, "end")
        self.insert(0, text)
        self.configure(state=state)
