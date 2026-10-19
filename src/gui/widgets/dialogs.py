import tkinter as tk

from gui import theme
from gui.utils import window_chrome
from gui.widgets.buttons import Button
from gui.widgets.field import Field


class _Dialog(tk.Toplevel):
    def __init__(self, parent, title: str, width: int = 400):
        super().__init__(parent, bg=theme.SURFACE)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result = None
        self.confirm_button = None
        self.cancel_button = None
        self._width = theme.px(width)
        self._done = False
        self.body = tk.Frame(self, bg=theme.SURFACE)
        self.body.pack(fill="both", expand=True, padx=theme.px(24), pady=(theme.px(22), theme.px(20)))
        tk.Label(
            self.body, text=title, font=theme.font(13, "bold"), fg=theme.TEXT, bg=theme.SURFACE, anchor="w",
        ).pack(fill="x", pady=(0, theme.px(14)))
        self.bind("<Escape>", lambda _e: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def add_buttons(self, confirm_text, on_confirm, cancel_text="Cancel", danger=False):
        row = tk.Frame(self.body, bg=theme.SURFACE)
        row.pack(fill="x", pady=(theme.px(20), 0))
        self.confirm_button = Button(
            row, confirm_text, command=on_confirm, variant="danger" if danger else "primary", padx=18,
        )
        self.confirm_button.pack(side="right")
        if cancel_text:
            self.cancel_button = Button(row, cancel_text, command=self.cancel, variant="ghost")
            self.cancel_button.pack(side="right", padx=(0, theme.px(8)))

    def finish(self, result) -> None:
        if self._done:
            return
        self._done = True
        self.result = result
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def cancel(self) -> None:
        self.finish(None)

    def show(self, focus=None):
        self.update_idletasks()
        parent = self.master.winfo_toplevel()
        width, height = max(self._width, self.winfo_reqwidth()), self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        window_chrome.enable_dark_title_bar(self, theme.SURFACE)
        self.deiconify()
        self.lift()
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        (focus or self).focus_set()
        self.wait_window()
        return self.result


def ask_name(parent, title, label, initial="", validate=None, confirm_text="Save"):
    dialog = _Dialog(parent, title)
    tk.Label(
        dialog.body, text=label.upper(), font=theme.font(8, "bold"), fg=theme.TEXT_MUTED, bg=theme.SURFACE, anchor="w",
    ).pack(fill="x")
    field = Field(dialog.body)
    field.pack(fill="x", pady=(theme.px(8), 0))
    entry = field.entry
    entry.insert(0, initial)
    entry.select_range(0, "end")
    error = tk.Label(dialog.body, text="", font=theme.font(9), fg=theme.WARNING, bg=theme.SURFACE, anchor="w")
    error.pack(fill="x", pady=(theme.px(8), 0))

    def submit(_event=None):
        value = entry.get().strip()
        message = validate(value) if validate else None
        if message:
            error.configure(text=message)
            return
        dialog.finish(value)

    entry.bind("<Return>", submit)
    entry.bind("<Key>", lambda _e: error.configure(text=""), add="+")
    dialog.add_buttons(confirm_text, submit)
    return dialog.show(focus=entry)


def confirm(parent, title, message, confirm_text="OK", cancel_text="Cancel", danger=False) -> bool:
    dialog = _Dialog(parent, title)
    tk.Label(
        dialog.body, text=message, font=theme.font(10), fg=theme.TEXT_SOFT, bg=theme.SURFACE,
        anchor="w", justify="left", wraplength=theme.px(350),
    ).pack(fill="x")
    dialog.add_buttons(confirm_text, lambda: dialog.finish(True), cancel_text=cancel_text, danger=danger)
    if danger and dialog.cancel_button is not None:
        focus = dialog.cancel_button
    else:
        focus = dialog.confirm_button
        dialog.bind("<Return>", lambda _e: dialog.finish(True))
    return bool(dialog.show(focus=focus))
