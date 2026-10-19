import tkinter as tk

from gui import theme
from gui.formatting import clip
from gui.widgets.buttons import Button
from gui.widgets.keycap import Keycap

MAX_MESSAGE_CHARS = 70
_BUTTON_TEXT = {"running": "Stop clicking", "waiting": "Cancel start"}
START_TEXT = "Start clicking"


class ActionBar(tk.Frame):
    def __init__(self, parent, on_toggle):
        super().__init__(parent, bg=parent.cget("bg"))
        self._hotkey = None
        self._error_text = None
        self._note_text = None
        self._hint_mode = None

        self.toggle_button = Button(
            self, START_TEXT, command=on_toggle, variant="primary",
            font=theme.font(12, "bold"), pady=14, radius=theme.RADIUS,
        )
        self.toggle_button.pack(fill="x")

        hint = tk.Frame(self, bg=self.cget("bg"))
        hint.pack(pady=(theme.px(14), 0))
        self._hint_prefix = tk.Label(hint, text="Press", font=theme.font(9), fg=theme.TEXT_MUTED, bg=self.cget("bg"))
        self._hint_key = Keycap(hint, compact=True)
        self.hint_label = tk.Label(hint, font=theme.font(9), fg=theme.TEXT_MUTED, bg=self.cget("bg"))
        self._render_hint()

    def show_status(self, kind: str, message=None) -> None:
        running = kind in ("running", "waiting")
        self.toggle_button.set_text(_BUTTON_TEXT.get(kind, START_TEXT))
        self.toggle_button.set_variant("danger" if running else "primary")
        self._error_text = message if kind == "error" else None
        self._note_text = message if kind in ("done", "running", "waiting") else None
        self._render_hint()

    def show_hotkey(self, hotkey) -> None:
        self._hotkey = hotkey
        self._render_hint()

    def _render_hint(self):
        if self._error_text:
            mode, text, color = "text", clip(self._error_text, MAX_MESSAGE_CHARS), theme.WARNING
        elif self._note_text:
            mode, text, color = "text", clip(self._note_text, MAX_MESSAGE_CHARS), theme.TEXT_SOFT
        elif self._hotkey:
            mode, text, color = "keyed", "from any window to start or stop", theme.TEXT_MUTED
        else:
            mode, text, color = "text", "No hotkey set · use Change to pick one", theme.TEXT_MUTED
        self.hint_label.configure(text=text, fg=color)
        if mode == "keyed":
            self._hint_key.set_text(self._hotkey)
        if mode == self._hint_mode:
            return
        self._hint_mode = mode
        for widget in (self._hint_prefix, self._hint_key, self.hint_label):
            widget.pack_forget()
        if mode == "keyed":
            self._hint_prefix.pack(side="left")
            self._hint_key.pack(side="left", padx=theme.px(6))
        self.hint_label.pack(side="left")
