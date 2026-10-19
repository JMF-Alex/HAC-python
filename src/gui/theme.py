from functools import lru_cache
from tkinter import font as tkfont
from tkinter import ttk

BG = "#0B0D12"
SIDEBAR = "#0F1218"
SURFACE = "#151922"
SURFACE_2 = "#1C212C"
SURFACE_HOVER = "#252B38"
SURFACE_DISABLED = "#13161D"

BORDER = "#222835"
BORDER_STRONG = "#2F3646"

TEXT = "#ECEEF4"
TEXT_SOFT = "#C7CCD7"
TEXT_MUTED = "#8C95A8"
TEXT_FAINT = "#7B849A"
TEXT_DISABLED = "#4B5262"

ACCENT = "#6A5AF0"
ACCENT_HOVER = "#7B6CFF"
ACCENT_ACTIVE = "#5949DC"
ACCENT_TEXT = "#FFFFFF"
ACCENT_SOFT = "#1B1A35"
ACCENT_BADGE = "#2B2763"
ACCENT_BADGE_TEXT = "#C9C2FF"
ACCENT_DISABLED = "#2A2752"
ACCENT_DISABLED_TEXT = "#8E88C4"

DANGER = "#E5484D"
DANGER_HOVER = "#F05A5F"
DANGER_ACTIVE = "#CC3D42"
DANGER_SOFT = "#2A1618"
DANGER_TEXT = "#F2777B"
WARNING = "#F5A524"
WARNING_EDGE = "#7A5410"

RUNNING_BG = "#0E2A22"
RUNNING_BORDER = "#1B4D3E"
RUNNING_DOT = "#34D399"
RUNNING_TEXT = "#6EE7B7"
WAITING_BG = "#2A2010"
WAITING_BORDER = "#5A4116"
ERROR_BG = "#2A1618"
ERROR_BORDER = "#5C2A2D"
ERROR_TEXT = "#F2777B"

KEY_FACE = "#252B38"
KEY_EDGE = "#06070A"

RADIUS = 12
RADIUS_SM = 8

FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"

_scale = 1.0


def px(value: float) -> int:
    return int(round(value * _scale))


def font(size: int = 10, weight: str = "normal"):
    return (FONT_FAMILY, size, weight)


def mono(size: int = 11, weight: str = "bold"):
    return (MONO_FAMILY, size, weight)


@lru_cache(maxsize=None)
def _font_object(spec):
    return tkfont.Font(font=spec)


def measure(spec, text: str) -> int:
    return _font_object(spec).measure(text)


def line_height(spec) -> int:
    return _font_object(spec).metrics("linespace")


def fit(spec, text: str, width: int) -> str:
    if measure(spec, text) <= width:
        return text
    while text and measure(spec, text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _pick_font(installed, candidates, fallback):
    return next((installed[c.lower()] for c in candidates if c.lower() in installed), fallback)


def _resolve_fonts(root) -> None:
    global FONT_FAMILY, MONO_FAMILY
    installed = {name.lower(): name for name in tkfont.families(root)}
    FONT_FAMILY = _pick_font(
        installed, ("Segoe UI Variable Text", "Segoe UI", "Inter", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans"),
        "Helvetica",
    )
    MONO_FAMILY = _pick_font(
        installed, ("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Ubuntu Mono", "Liberation Mono"), "Courier",
    )


def init(root) -> None:
    global _scale
    _scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
    _resolve_fonts(root)
    _font_object.cache_clear()
    _apply_ttk_styles(root)


def _apply_ttk_styles(root) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Flat.TCombobox",
        fieldbackground=SURFACE_2, background=SURFACE_2, foreground=TEXT, arrowcolor=TEXT_MUTED,
        bordercolor=SURFACE_2, lightcolor=SURFACE_2, darkcolor=SURFACE_2, borderwidth=0, relief="flat",
        padding=(2, 2), arrowsize=px(12), selectbackground=SURFACE_2, selectforeground=TEXT,
    )
    style.map(
        "Flat.TCombobox",
        fieldbackground=[("disabled", SURFACE_DISABLED), ("readonly", SURFACE_2)],
        foreground=[("disabled", TEXT_DISABLED)],
        background=[("disabled", SURFACE_DISABLED), ("active", SURFACE_2)],
        bordercolor=[("disabled", SURFACE_DISABLED)],
        lightcolor=[("disabled", SURFACE_DISABLED)],
        darkcolor=[("disabled", SURFACE_DISABLED)],
        arrowcolor=[("disabled", TEXT_DISABLED), ("active", TEXT)],
        selectbackground=[("readonly", SURFACE_2)],
        selectforeground=[("readonly", TEXT)],
    )
    style.layout("Thin.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
        ]}),
    ])
    style.configure(
        "Thin.Vertical.TScrollbar",
        background=BORDER_STRONG, troughcolor=SIDEBAR, bordercolor=SIDEBAR,
        lightcolor=BORDER_STRONG, darkcolor=BORDER_STRONG, relief="flat", width=px(6), arrowsize=0,
    )
    style.map(
        "Thin.Vertical.TScrollbar",
        background=[("pressed", TEXT_MUTED), ("active", TEXT_FAINT)],
        lightcolor=[("pressed", TEXT_MUTED), ("active", TEXT_FAINT)],
        darkcolor=[("pressed", TEXT_MUTED), ("active", TEXT_FAINT)],
    )
    root.option_add("*TCombobox*Listbox.background", SURFACE_2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_TEXT)
    root.option_add("*TCombobox*Listbox.font", font(10))
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.highlightThickness", 0)
