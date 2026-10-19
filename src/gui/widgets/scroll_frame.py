import sys
import tkinter as tk
from tkinter import ttk


class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, yscrollincrement=1)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", style="Thin.Vertical.TScrollbar", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_scroll)
        self._canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._window = self._canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._window, width=e.width))
        for widget in (self, self._canvas, self.inner):
            widget.bind("<Enter>", self._bind_wheel, add="+")
            widget.bind("<Leave>", self._unbind_wheel, add="+")

    def _on_scroll(self, first, last):
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._scrollbar.pack_forget()
        elif not self._scrollbar.winfo_ismapped():
            self._scrollbar.pack(side="right", fill="y", padx=(2, 0))
        self._scrollbar.set(first, last)

    def _bind_wheel(self, _event=None):
        if sys.platform.startswith("linux"):
            self.bind_all("<Button-4>", lambda _e: self._scroll(-1))
            self.bind_all("<Button-5>", lambda _e: self._scroll(1))
        else:
            self.bind_all("<MouseWheel>", lambda e: self._scroll(-1 if e.delta > 0 else 1))

    def _unbind_wheel(self, _event=None):
        try:
            under = self.winfo_containing(*self.winfo_pointerxy())
        except (tk.TclError, KeyError):
            under = None
        if under is not None and (under is self or str(under).startswith(str(self) + ".")):
            return
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(sequence)

    def _scroll(self, direction):
        first, last = self._canvas.yview()
        if first > 0.0 or last < 1.0:
            self._canvas.yview_scroll(direction * 40, "units")

    def scroll_to(self, widget) -> None:
        self.update_idletasks()
        total = self.inner.winfo_height()
        if total <= 0:
            return
        top, bottom = widget.winfo_y(), widget.winfo_y() + widget.winfo_height()
        view_top, view_bottom = (f * total for f in self._canvas.yview())
        if top < view_top:
            self._canvas.yview_moveto(top / total)
        elif bottom > view_bottom:
            self._canvas.yview_moveto((bottom - (view_bottom - view_top)) / total)
