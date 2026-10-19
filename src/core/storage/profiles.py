DEFAULT_PROFILE_NAME = "Default"
MAX_PROFILE_NAME = 24
_HOTKEY_CANDIDATES = tuple(f"F{n}" for n in range(6, 13))


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
