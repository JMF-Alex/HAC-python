import tkinter as tk
from dataclasses import dataclass

from gui import theme
from gui.formatting import format_interval, key_label
from gui.widgets.buttons import Button
from gui.widgets.scroll_frame import ScrollFrame
from gui.widgets.shapes import CanvasWidget, rounded_rect


@dataclass(frozen=True)
class ProfileSummary:
    name: str
    hotkey: str
    interval: float
    mode: str
    key: str

    @classmethod
    def from_config(cls, name: str, config: dict) -> "ProfileSummary":
        return cls(name, config["hotkey"] or "-", config["interval"], config["mode"], config["target_key"])

    @property
    def subtitle(self) -> str:
        return " · ".join((self.mode, key_label(self.key), format_interval(self.interval)))


class ProfileRow(CanvasWidget):
    def __init__(self, parent, summary: ProfileSummary, selected: bool, on_click):
        self.summary = summary
        self.selected = selected
        self._on_click = on_click
        self._hover = False
        self._pressed = False
        self._name_font = theme.font(10, "bold")
        self._sub_font = theme.font(9)
        self._badge_font = theme.mono(8, "bold")
        self._pad = theme.px(11)
        height = theme.line_height(self._name_font) + theme.line_height(self._sub_font) + theme.px(2) + 2 * self._pad
        super().__init__(parent, theme.px(200), height, cursor="hand2")
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def set_selected(self, selected: bool) -> None:
        if selected != self.selected:
            self.selected = selected
            self.redraw()

    def _set_hover(self, hover):
        self._hover = hover
        self.redraw()

    def _on_press(self, _event):
        self._pressed = True

    def _on_release(self, _event):
        fire = self._pressed and self._hover
        self._pressed = False
        if fire and self._on_click is not None:
            self._on_click(self.summary.name)

    def draw(self, width, height):
        if self.selected:
            bg, name_fg, sub_fg = theme.ACCENT_SOFT, theme.TEXT, theme.TEXT_MUTED
            badge_bg, badge_fg = theme.ACCENT_BADGE, theme.ACCENT_BADGE_TEXT
        elif self._hover:
            bg, name_fg, sub_fg = theme.SURFACE, theme.TEXT, theme.TEXT_MUTED
            badge_bg, badge_fg = theme.SURFACE_HOVER, theme.TEXT_SOFT
        else:
            bg, name_fg, sub_fg = None, theme.TEXT_SOFT, theme.TEXT_FAINT
            badge_bg, badge_fg = theme.SURFACE_2, theme.TEXT_MUTED
        if bg is not None:
            rounded_rect(self, 0, 0, width - 1, height - 1, theme.px(theme.RADIUS_SM), fill=bg, outline=bg)
        if self.selected:
            rounded_rect(self, 0, self._pad, theme.px(3), height - self._pad, theme.px(2),
                         fill=theme.ACCENT, outline=theme.ACCENT)

        left = theme.px(14)
        name_h = theme.line_height(self._name_font)
        badge_text = self.summary.hotkey
        badge_w = theme.measure(self._badge_font, badge_text) + theme.px(12)
        badge_h = theme.line_height(self._badge_font) + theme.px(2)
        badge_x2 = width - theme.px(10)
        badge_y = self._pad + (name_h - badge_h) / 2
        rounded_rect(self, badge_x2 - badge_w, badge_y, badge_x2, badge_y + badge_h, theme.px(5), fill=badge_bg, outline=badge_bg)
        self.create_text(badge_x2 - badge_w / 2, badge_y + badge_h / 2, text=badge_text, font=self._badge_font, fill=badge_fg)

        name_room = badge_x2 - badge_w - theme.px(8) - left
        self.create_text(left, self._pad, anchor="nw", fill=name_fg, font=self._name_font, text=theme.fit(self._name_font, self.summary.name, name_room))
        self.create_text(left, self._pad + name_h + theme.px(2), anchor="nw", fill=sub_fg, font=self._sub_font, text=theme.fit(self._sub_font, self.summary.subtitle, width - left - theme.px(10)))


class ProfileSidebar(tk.Frame):
    WIDTH = 256

    def __init__(self, parent, app_name: str, version: str, logo=None, on_select=None, on_add=None, on_rename=None, on_delete=None, on_duplicate=None):
        super().__init__(parent, bg=theme.SIDEBAR, width=theme.px(self.WIDTH))
        self.pack_propagate(False)
        self._logo = logo
        self._on_select = on_select
        self._on_add = on_add
        self._on_rename = on_rename
        self._on_delete = on_delete
        self._on_duplicate = on_duplicate
        self._active = None
        self._summaries = []
        self._items = {}

        self._build_header(app_name, version)
        self._build_caption()
        self._build_footer()

        self._list = ScrollFrame(self, bg=theme.SIDEBAR)
        self._list.pack(fill="both", expand=True, padx=(theme.px(10), theme.px(8)))
        self._empty = tk.Label(
            self._list.inner, text="No profiles yet", font=theme.font(9), fg=theme.TEXT_FAINT,
            bg=theme.SIDEBAR, anchor="w",
        )

    @property
    def profile_names(self):
        return list(self._items)

    @property
    def active(self):
        return self._active

    def set_profiles(self, profiles, active=None) -> None:
        profiles = list(profiles)
        if profiles != self._summaries:
            self._summaries = profiles
            for item in self._items.values():
                item.destroy()
            self._items = {}
            self._empty.pack_forget()
            for profile in profiles:
                item = ProfileRow(self._list.inner, profile, False, self._handle_select)
                item.pack(fill="x", pady=(0, theme.px(2)))
                self._items[profile.name] = item
            if not profiles:
                self._empty.pack(fill="x", padx=theme.px(12), pady=theme.px(8))
            self._count.configure(text=str(len(profiles)))
        self.set_active(active)

    def set_active(self, name) -> None:
        self._active = name if name in self._items else None
        for item_name, item in self._items.items():
            item.set_selected(item_name == self._active)
        if self._active is not None:
            self._list.scroll_to(self._items[self._active])
        self._sync_footer()

    def _build_header(self, app_name, version):
        header = tk.Frame(self, bg=theme.SIDEBAR)
        header.pack(fill="x", padx=theme.px(20), pady=(theme.px(24), theme.px(22)))
        if self._logo is not None:
            tk.Label(header, image=self._logo, bg=theme.SIDEBAR, bd=0).pack(side="left")
        else:
            tk.Label(
                header, text="H", font=theme.font(14, "bold"), fg=theme.ACCENT_TEXT, bg=theme.ACCENT,
                width=2, pady=theme.px(3),
            ).pack(side="left")
        titles = tk.Frame(header, bg=theme.SIDEBAR)
        titles.pack(side="left", padx=(theme.px(12), 0))
        tk.Label(titles, text=app_name, font=theme.font(12, "bold"), fg=theme.TEXT, bg=theme.SIDEBAR,
                 anchor="w").pack(fill="x")
        tk.Label(titles, text=version, font=theme.font(8), fg=theme.TEXT_FAINT, bg=theme.SIDEBAR,
                 anchor="w").pack(fill="x")

    def _build_caption(self):
        caption = tk.Frame(self, bg=theme.SIDEBAR)
        caption.pack(fill="x", padx=theme.px(24), pady=(0, theme.px(8)))
        tk.Label(caption, text="PROFILES", font=theme.font(8, "bold"), fg=theme.TEXT_MUTED, bg=theme.SIDEBAR).pack(side="left")
        self._count = tk.Label(caption, text="0", font=theme.font(8, "bold"), fg=theme.TEXT_FAINT, bg=theme.SIDEBAR)
        self._count.pack(side="right")

    def _build_footer(self):
        footer = tk.Frame(self, bg=theme.SIDEBAR)
        footer.pack(side="bottom", fill="x")
        tk.Frame(footer, height=1, bg=theme.BORDER).pack(fill="x")
        self.add_button = Button(footer, "+  New profile", command=self._handle_add, variant="subtle", pady=8)
        self.add_button.pack(fill="x", padx=theme.px(14), pady=(theme.px(14), theme.px(6)))
        buttons = tk.Frame(footer, bg=theme.SIDEBAR)
        buttons.pack(fill="x", padx=theme.px(14), pady=(0, theme.px(12)))
        buttons.grid_columnconfigure((0, 1, 2), weight=1, uniform="actions")
        self.rename_button = Button(buttons, "Rename", command=self._handle_rename, variant="quiet", padx=6, pady=6)
        self.rename_button.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.duplicate_button = Button(buttons, "Duplicate", command=self._handle_duplicate, variant="quiet", padx=6, pady=6)
        self.duplicate_button.grid(row=0, column=1, sticky="ew", padx=2)
        self.delete_button = Button(buttons, "Delete", command=self._handle_delete, variant="quiet_danger", padx=6, pady=6)
        self.delete_button.grid(row=0, column=2, sticky="ew", padx=(2, 0))

    def _sync_footer(self):
        has_selection = self._active is not None
        self.rename_button.set_enabled(has_selection)
        self.duplicate_button.set_enabled(has_selection)
        self.delete_button.set_enabled(has_selection)

    def _handle_select(self, name):
        if self._on_select is not None:
            self._on_select(name)

    def _handle_add(self):
        if self._on_add is not None:
            self._on_add()

    def _handle_rename(self):
        if self._on_rename is not None and self._active is not None:
            self._on_rename(self._active)

    def _handle_duplicate(self):
        if self._on_duplicate is not None and self._active is not None:
            self._on_duplicate(self._active)

    def _handle_delete(self):
        if self._on_delete is not None and self._active is not None:
            self._on_delete(self._active)
