from core.constants import FAILSAFE_CORNERS

CORNER_MARGIN = 2


def corner_hit(corner: str, x: int, y: int, width: int, height: int, margin: int = CORNER_MARGIN) -> bool:
    if corner not in FAILSAFE_CORNERS:
        return False
    at_left = -margin <= x <= margin
    at_right = width - 1 - margin <= x <= width - 1 + margin
    at_top = -margin <= y <= margin
    at_bottom = height - 1 - margin <= y <= height - 1 + margin
    return {
        "Top-left": at_left and at_top,
        "Top-right": at_right and at_top,
        "Bottom-left": at_left and at_bottom,
        "Bottom-right": at_right and at_bottom,
    }[corner]