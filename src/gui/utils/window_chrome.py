import ctypes
import logging
import sys
from ctypes import wintypes

from gui import theme

logger = logging.getLogger(__name__)

DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19  # Windows 10 1809 - 1903
DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10 2004+ and Windows 11
DWMWA_CAPTION_COLOR = 35  # Windows 11 only
PROCESS_SYSTEM_DPI_AWARE = 1


def _colorref(hex_color: str) -> int:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return r | (g << 8) | (b << 16)


def enable_dpi_awareness() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_SYSTEM_DPI_AWARE) == 0
    except (AttributeError, OSError):
        try:
            return bool(ctypes.windll.user32.SetProcessDPIAware())
        except (AttributeError, OSError):
            logger.warning("Could not enable DPI awareness", exc_info=True)
            return False


def enable_dark_title_bar(window, caption_color: str = theme.BG) -> bool:
    if sys.platform != "win32":
        return False
    try:
        window.update_idletasks()
        user32, dwm = ctypes.windll.user32, ctypes.windll.dwmapi
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.LPCVOID, wintypes.DWORD]
        hwnd = user32.GetParent(window.winfo_id())

        def set_attr(attribute: int, value: int) -> bool:
            data = ctypes.c_int(value)
            return dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data)) == 0

        dark = set_attr(DWMWA_USE_IMMERSIVE_DARK_MODE, 1) or set_attr(DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 1)
        set_attr(DWMWA_CAPTION_COLOR, _colorref(caption_color))
        return dark
    except Exception:
        logger.exception("Could not style the title bar")
        return False
