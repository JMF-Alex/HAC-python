import os
import sys

from core.constants import APP_NAME

# src/core/storage/paths.py -> src/
SOURCE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def user_data_dir() -> str:
    override = os.environ.get("HAC_CONFIG_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override

    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")

    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def resource_path(*parts: str) -> str:
    return os.path.join(getattr(sys, "_MEIPASS", SOURCE_ROOT), *parts)
