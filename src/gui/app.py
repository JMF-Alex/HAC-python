import logging
import tkinter as tk

from core.constants import APP_NAME, APP_VERSION
from core.engine.clicker import Clicker
from core.storage.config import load_config
from core.storage.paths import resource_path
from core.system import timer_resolution
from gui import theme
from gui.controller import ClickerController
from gui.utils import window_chrome
from gui.views.main_window import MainWindow

logger = logging.getLogger(__name__)


class HACApp:
    WIDTH, HEIGHT = 960, 620

    def __init__(self):
        window_chrome.enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)
        self.root.configure(bg=theme.BG)
        self.root.report_callback_exception = self._log_tk_exception
        theme.init(self.root)
        self.config = load_config()
        self._timer_resolution_on = timer_resolution.begin(1)
        self.clicker = Clicker()
        self.controller = ClickerController(self.root, self.clicker, self.config)
        self.view = MainWindow(self.root, self.controller, APP_VERSION)
        self.controller.bind_view(self.view)
        self._place_window()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _place_window(self):
        self.root.update_idletasks()
        width = max(theme.px(self.WIDTH), self.root.winfo_reqwidth())
        height = max(theme.px(self.HEIGHT), self.root.winfo_reqheight())
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.resizable(False, False)

    def _set_icon(self):
        try:
            self.root.iconbitmap(resource_path("assets", "icon.ico"))
        except tk.TclError:
            if self.view.logo is not None:
                self.root.iconphoto(True, self.view.logo)
            else:
                logger.warning("Window icon not found or unsupported on this platform")

    def on_close(self):
        try:
            self.controller.shutdown()
        finally:
            if self._timer_resolution_on:
                timer_resolution.end(1)
                self._timer_resolution_on = False
            self.root.destroy()

    @staticmethod
    def _log_tk_exception(exc_type, exc, tb):
        logger.error("Unhandled error in a Tk callback", exc_info=(exc_type, exc, tb))

    def run(self):
        self._set_icon()
        self.root.deiconify()
        window_chrome.enable_dark_title_bar(self.root)
        self.root.mainloop()
