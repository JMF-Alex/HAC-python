def format_duration(seconds: float) -> str:
    total = int(seconds)
    if total < 60:
        return f"{total} s"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}:{secs:02d}"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def clicks_text(count: int) -> str:
    return f"{count:,} click" if count == 1 else f"{count:,} clicks"


def format_number(value) -> str:
    value = float(value)
    return str(int(value)) if value.is_integer() else str(value)


def format_interval(seconds: float) -> str:
    return f"{seconds * 1000:g} ms" if seconds < 1 else f"{seconds:g} s"


def key_label(key: str) -> str:
    if key.startswith("mouse_"):
        return f"{key[6:].capitalize()} mouse"
    return key.upper() if len(key) == 1 else key.capitalize()


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1] + "…"
