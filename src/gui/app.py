import logging
import tkinter as tk

from core import timer_resolution
from core.clicker import Clicker
from core.config import load_config
from core.paths import resource_path
from gui import theme, window_chrome
from gui.controller import ClickerController
from gui.layout import LayoutManager

logger = logging.getLogger(__name__)


class HACApp:
    VERSION = "v0.8.0"
    WIDTH, HEIGHT = 900, 560

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HAutoClicker")
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=theme.BG)
        self.root.report_callback_exception = self._log_tk_exception
        theme.apply_ttk_styles(self.root)
        self.config = load_config()
        self._timer_resolution_on = timer_resolution.begin(1)
        self.clicker = Clicker()
        self.controller = None
        self.layout = None
        self.init_app()

    def init_app(self):
        self.controller = ClickerController(self.root, self.clicker, self.config)
        self.layout = LayoutManager(self.root, self.controller, self.VERSION)
        self.controller.bind_view(self.layout)

        self.center_window()
        window_chrome.enable_dark_title_bar(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.WIDTH // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.HEIGHT // 2)
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def on_close(self):
        self.controller.shutdown()
        if self._timer_resolution_on:
            timer_resolution.end(1)
            self._timer_resolution_on = False
        self.root.destroy()

    def _set_icon(self):
        try:
            self.root.iconbitmap(resource_path("assets", "icon.ico"))
        except tk.TclError:
            logo = getattr(self.layout, "logo", None)
            if logo is not None:
                self.root.iconphoto(True, logo)
            else:
                logger.warning("Window icon not found or unsupported on this platform")

    @staticmethod
    def _log_tk_exception(exc_type, exc, tb):
        logger.error("Unhandled error in a Tk callback", exc_info=(exc_type, exc, tb))

    def run(self):
        self._set_icon()
        self.root.mainloop()