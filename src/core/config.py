import json
import logging
import math
import os

from core.constants import (
    DEFAULT_HOTKEY,
    DEFAULT_INTERVAL,
    DEFAULT_JITTER,
    DEFAULT_LIMIT_VALUE,
    DEFAULT_START_DELAY,
    DEFAULT_TARGET_KEY,
    FAILSAFE_CHOICES,
    FAILSAFE_OFF,
    KEY_CHOICES,
    LIMIT_KINDS,
    LIMIT_NEVER,
    MAX_INTERVAL,
    MAX_JITTER,
    MAX_LIMIT_VALUE,
    MAX_START_DELAY,
    MIN_INTERVAL,
    MIN_JITTER,
    MIN_LIMIT_VALUE,
    MIN_START_DELAY,
    MODE_CLICK,
    MODES,
)
from core.paths import user_data_dir

logger = logging.getLogger(__name__)

CONFIG_VERSION = 5
CONFIG_FILENAME = "config.json"
LEGACY_CONFIG_PATH = os.path.join(os.path.expanduser("~"), "hac_config.json")

DEFAULT_PROFILE_NAME = "Default"
MAX_PROFILE_NAME = 24
SETTING_KEYS = ("interval", "hotkey", "mode", "target_key")
_HOTKEY_CANDIDATES = tuple(f"F{n}" for n in range(6, 13))


def default_profile() -> dict:
    return {
        "interval": DEFAULT_INTERVAL,
        "hotkey": DEFAULT_HOTKEY,
        "mode": MODE_CLICK,
        "target_key": DEFAULT_TARGET_KEY,
        "jitter": DEFAULT_JITTER,
        "limit_kind": LIMIT_NEVER,
        "limit_value": DEFAULT_LIMIT_VALUE,
        "start_delay": DEFAULT_START_DELAY,
    }


def default_settings() -> dict:
    return {"failsafe": FAILSAFE_OFF, "always_on_top": False, "sound": False}


def config_path() -> str:
    return os.path.join(user_data_dir(), CONFIG_FILENAME)


def name_error(name: str, existing, ignore=None):
    name = name.strip()
    if not name:
        return "Enter a name"
    if len(name) > MAX_PROFILE_NAME:
        return f"Use at most {MAX_PROFILE_NAME} characters"
    taken = {n.lower() for n in existing if n != ignore}
    if name.lower() in taken:
        return "A profile with that name already exists"
    return None


def copy_name(name: str, existing) -> str:
    for number in range(1, 1000):
        suffix = " copy" if number == 1 else f" copy {number}"
        candidate = name.strip()[:MAX_PROFILE_NAME - len(suffix)].rstrip() + suffix
        if name_error(candidate, existing) is None:
            return candidate
    return unique_name("Profile", existing)


def unique_name(base: str, existing) -> str:
    taken = {n.lower() for n in existing}
    if base.lower() not in taken:
        return base
    index = 2
    while f"{base} {index}".lower() in taken:
        index += 1
    return f"{base} {index}"


def suggest_hotkey(taken) -> str:
    used = {h.lower() for h in taken if h}
    return next((h for h in _HOTKEY_CANDIDATES if h.lower() not in used), "")


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _migrate(data: dict) -> dict:
    data = dict(data)
    version = data.get("version", 1)
    if version < 2:
        key = data.get("target_key")
        if key in ("left", "right", "middle"):
            data["target_key"] = f"mouse_{key}"
        elif key in ("left_arrow", "right_arrow"):
            data["target_key"] = key.split("_")[0]
    if version < 3:
        data = {
            "profiles": {DEFAULT_PROFILE_NAME: {k: data[k] for k in SETTING_KEYS if k in data}},
            "active_profile": DEFAULT_PROFILE_NAME,
        }
    data["version"] = CONFIG_VERSION
    return data


def _clamped_number(value, low: float, high: float):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return min(high, max(low, float(value)))


def _sanitize_profile(data: dict) -> dict:
    cfg = default_profile()

    for key, low, high in (
        ("interval", MIN_INTERVAL, MAX_INTERVAL),
        ("jitter", MIN_JITTER, MAX_JITTER),
        ("limit_value", MIN_LIMIT_VALUE, MAX_LIMIT_VALUE),
        ("start_delay", MIN_START_DELAY, MAX_START_DELAY),
    ):
        number = _clamped_number(data.get(key), low, high)
        if number is not None:
            cfg[key] = number

    if data.get("limit_kind") in LIMIT_KINDS:
        cfg["limit_kind"] = data["limit_kind"]

    if data.get("mode") in MODES:
        cfg["mode"] = data["mode"]

    hotkey = data.get("hotkey")
    if isinstance(hotkey, str):
        cfg["hotkey"] = hotkey.strip()

    if data.get("target_key") in KEY_CHOICES:
        cfg["target_key"] = data["target_key"]

    return cfg


def _sanitize_settings(data) -> dict:
    settings = default_settings()
    if not isinstance(data, dict):
        return settings
    if data.get("failsafe") in FAILSAFE_CHOICES:
        settings["failsafe"] = data["failsafe"]
    for key in ("always_on_top", "sound"):
        if isinstance(data.get(key), bool):
            settings[key] = data[key]
    return settings


def _sanitize(data: dict) -> dict:
    profiles = {}
    seen_names, used_hotkeys = set(), set()

    raw = data.get("profiles")
    if isinstance(raw, dict):
        for name, settings in raw.items():
            if not isinstance(name, str) or not isinstance(settings, dict):
                continue
            name = name.strip()[:MAX_PROFILE_NAME].strip()
            if not name or name.lower() in seen_names:
                continue
            profile = _sanitize_profile(settings)
            hotkey = profile["hotkey"].lower()
            if hotkey and hotkey in used_hotkeys:
                profile["hotkey"] = ""
            elif hotkey:
                used_hotkeys.add(hotkey)
            seen_names.add(name.lower())
            profiles[name] = profile

    if not profiles:
        profiles[DEFAULT_PROFILE_NAME] = default_profile()

    active = data.get("active_profile")
    if active not in profiles:
        active = next(iter(profiles))
    return {
        "version": CONFIG_VERSION,
        "active_profile": active,
        "profiles": profiles,
        "settings": _sanitize_settings(data.get("settings")),
    }


def load_config() -> dict:
    path = config_path()
    if os.path.exists(path):
        data = _read_json(path)
    elif os.path.exists(LEGACY_CONFIG_PATH):
        data = _read_json(LEGACY_CONFIG_PATH)
        data.setdefault("version", 1)
    else:
        data = {}
    return _sanitize(_migrate(data))


def save_config(config: dict) -> dict:
    config = _sanitize(config)
    path = config_path()
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        os.replace(tmp, path)
    except OSError:
        logger.exception("Could not save config to %s", path)
    return config