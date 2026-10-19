import tkinter as tk

from core.constants import APP_NAME
from core.storage.paths import resource_path
from gui import theme
from gui.formatting import format_number
from gui.utils import icon
from gui.views.action_bar import ActionBar
from gui.views.pages.advanced import AdvancedPage
from gui.views.pages.general import GeneralPage
from gui.views.pages.settings import SettingsPage
from gui.views.sidebar import ProfileSidebar, ProfileSummary
from gui.widgets import dialogs
from gui.widgets.buttons import Button
from gui.widgets.status_pill import StatusPill
from gui.widgets.tabs import Tabs

LOGO_SIZE = 32
TITLE_WIDTH = 380

PAGE_GENERAL = "General"
PAGE_ADVANCED = "Advanced"
PAGE_SETTINGS = "Settings"
PAGES = (PAGE_GENERAL, PAGE_ADVANCED, PAGE_SETTINGS)


def _title_font():
    return theme.font(20, "bold")


class MainWindow:
    def __init__(self, root, controller, version):
        self.root = root
        self.controller = controller
        self.version = version
        self._save_reset_id = None
        self._profiles_id = None
        self._pages = {}
        self._build()

    def _build(self):
        settings = self.controller.active_settings
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.logo = icon.load_icon_photo(resource_path("assets", "icon.ico"), theme.px(LOGO_SIZE), master=self.root)
        self.sidebar = ProfileSidebar(
            self.root, APP_NAME, self.version, logo=self.logo,
            on_select=self.controller.select_profile, on_add=self.controller.add_profile,
            on_rename=self.controller.rename_profile, on_delete=self.controller.delete_profile,
            on_duplicate=self.controller.duplicate_profile,
        )
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.set_profiles(self._summaries(self.controller.profiles), active=self.controller.active_name)
        tk.Frame(self.root, width=1, bg=theme.BORDER).grid(row=0, column=1, sticky="ns")

        main = tk.Frame(self.root, bg=theme.BG)
        main.grid(row=0, column=2, sticky="nsew")
        content = tk.Frame(main, bg=theme.BG)
        content.pack(fill="both", expand=True, padx=theme.px(36), pady=theme.px(28))

        self._build_header(content)
        self.page_var = tk.StringVar(value=PAGE_GENERAL)
        Tabs(content, PAGES, self.page_var).pack(fill="x", pady=(theme.px(20), 0))
        self.action_bar = ActionBar(content, self.controller.toggle)
        self.action_bar.pack(side="bottom", fill="x", pady=(theme.px(24), 0))
        self._build_pages(content, settings)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=theme.BG)
        header.pack(fill="x")
        titles = tk.Frame(header, bg=theme.BG)
        titles.pack(side="left")
        tk.Label(
            titles, text="ACTIVE PROFILE", font=theme.font(8, "bold"), fg=theme.TEXT_FAINT, bg=theme.BG, anchor="w",
        ).pack(fill="x")
        self.title_label = tk.Label(
            titles, font=_title_font(), fg=theme.TEXT, bg=theme.BG,
            anchor="w",
        )
        self.title_label.pack(fill="x")
        self.set_profile_title(self.controller.active_name)

        actions = tk.Frame(header, bg=theme.BG)
        actions.pack(side="right", anchor="s")
        self.status_pill = StatusPill(actions)
        self.status_pill.pack(side="right")
        self.save_button = Button(actions, "Save", command=self._on_save, variant="ghost", pady=6)
        self.save_button.pack(side="right", padx=(0, theme.px(10)))

    def _build_pages(self, parent, settings):
        host = tk.Frame(parent, bg=theme.BG)
        host.pack(fill="x", pady=(theme.px(20), 0))
        host.grid_columnconfigure(0, weight=1)
        self.general = GeneralPage(host, settings, self.controller.change_hotkey)
        self.advanced = AdvancedPage(host, settings, self.general.mode_var)
        self.settings_page = SettingsPage(host, self.controller.settings, self.controller.settings_changed)
        self._pages = {PAGE_GENERAL: self.general, PAGE_ADVANCED: self.advanced, PAGE_SETTINGS: self.settings_page}
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.root.update_idletasks()
        host.configure(
            width=max(p.winfo_reqwidth() for p in self._pages.values()),
            height=max(p.winfo_reqheight() for p in self._pages.values()),
        )
        host.grid_propagate(False)

        self.interval_entry = self.general.interval_entry
        self.mode_var = self.general.mode_var
        self.key_var = self.general.key_var
        self.jitter_entry = self.advanced.jitter_entry
        self.delay_entry = self.advanced.delay_entry
        self.limit_entry = self.advanced.limit_entry
        self.limit_var = self.advanced.limit_var

        self.page_var.trace_add("write", lambda *_: self._show_page())
        self._show_page()

    def _show_page(self):
        selected = self.page_var.get()
        for name, page in self._pages.items():
            if name == selected:
                page.grid()
            else:
                page.grid_remove()


    def show_status(self, kind: str, message=None) -> None:
        self.status_pill.set_kind("stopped" if kind == "done" else kind)
        self.action_bar.show_status(kind, message)

    def show_hotkey(self, hotkey) -> None:
        self.general.show_hotkey(hotkey)
        self.action_bar.show_hotkey(hotkey)

    def show_hotkey_waiting(self) -> None:
        self.general.show_hotkey_waiting()

    def set_profile_title(self, name: str) -> None:
        self.title_label.configure(text=theme.fit(_title_font(), name, theme.px(TITLE_WIDTH)))

    def show_number(self, entry, value) -> None:
        entry.set_text(format_number(value))

    def show_profile(self, name: str, settings: dict) -> None:
        self.set_profile_title(name)
        self.show_number(self.interval_entry, settings["interval"])
        self.show_number(self.jitter_entry, settings["jitter"])
        self.show_number(self.delay_entry, settings["start_delay"])
        self.show_number(self.limit_entry, settings["limit_value"])
        self.mode_var.set(settings["mode"])
        self.key_var.set(settings["target_key"])
        self.limit_var.set(settings["limit_kind"])
        self.show_hotkey(settings["hotkey"])

    def show_settings(self, settings: dict) -> None:
        self.settings_page.load(settings)
        self.set_always_on_top(settings["always_on_top"])

    def read_settings(self) -> dict:
        return self.settings_page.read()

    def set_always_on_top(self, enabled: bool) -> None:
        try:
            self.root.attributes("-topmost", bool(enabled))
        except tk.TclError:
            pass

    def beep(self) -> None:
        self.root.bell()

    def pointer_position(self):
        x, y = self.root.winfo_pointerxy()
        return x, y, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def show_profiles(self, profiles: dict, active: str) -> None:
        summaries = self._summaries(profiles)
        if self._profiles_id is not None:
            self.root.after_cancel(self._profiles_id)
        self._profiles_id = self.root.after_idle(lambda: self._apply_profiles(summaries, active))

    def _apply_profiles(self, summaries, active):
        self._profiles_id = None
        self.sidebar.set_profiles(summaries, active=active)

    def ask_profile_name(self, title, initial, validate, confirm_text="Save"):
        return dialogs.ask_name(self.root, title, "Profile name", initial, validate, confirm_text)

    def confirm_delete(self, name: str) -> bool:
        return dialogs.confirm(
            self.root, "Delete profile", f"Delete “{name}”? This can't be undone.",
            confirm_text="Delete", danger=True,
        )

    def show_message(self, title: str, message: str) -> None:
        dialogs.confirm(self.root, title, message, cancel_text=None)

    @staticmethod
    def _summaries(profiles: dict) -> list:
        return [ProfileSummary.from_config(name, s) for name, s in profiles.items()]

    def set_inputs_enabled(self, enabled: bool) -> None:
        self.general.set_enabled(enabled)
        self.advanced.set_enabled(enabled)

    def _on_save(self):
        self.controller.save_settings(force=True)
        if self._save_reset_id is not None:
            self.root.after_cancel(self._save_reset_id)
        self.save_button.set_text("Saved")
        self._save_reset_id = self.root.after(1400, self._reset_save_button)

    def _reset_save_button(self):
        self._save_reset_id = None
        self.save_button.set_text("Save")
