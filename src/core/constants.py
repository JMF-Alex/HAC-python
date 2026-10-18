APP_NAME = "HAutoClicker"

MODE_CLICK = "Click"
MODE_HOLD = "Hold"
MODES = (MODE_CLICK, MODE_HOLD)

DEFAULT_INTERVAL = 0.01
MIN_INTERVAL = 0.001
MAX_INTERVAL = 3600.0

DEFAULT_JITTER = 0.0
MIN_JITTER = 0.0
MAX_JITTER = 100.0

LIMIT_NEVER = "Never"
LIMIT_CLICKS = "Clicks"
LIMIT_TIME = "Time"
LIMIT_KINDS = (LIMIT_NEVER, LIMIT_CLICKS, LIMIT_TIME)
DEFAULT_LIMIT_VALUE = 100.0
MIN_LIMIT_VALUE = 1.0
MAX_LIMIT_VALUE = 1_000_000.0

DEFAULT_START_DELAY = 0.0
MIN_START_DELAY = 0.0
MAX_START_DELAY = 60.0

DEFAULT_HOTKEY = "F6"
DEFAULT_TARGET_KEY = "mouse_left"

MOUSE_KEYS = ("mouse_left", "mouse_right", "mouse_middle")

KEY_CHOICES = (
    *MOUSE_KEYS,
    "space", "shift", "ctrl", "alt", "enter", "tab",
    "up", "down", "left", "right",
    *(chr(i) for i in range(ord("a"), ord("z") + 1)),
)