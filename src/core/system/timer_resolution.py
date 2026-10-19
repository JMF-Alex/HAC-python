import ctypes
import logging
import sys

logger = logging.getLogger(__name__)


def begin(milliseconds: int = 1) -> bool:
    if sys.platform != "win32":
        return False
    try:
        return ctypes.windll.winmm.timeBeginPeriod(milliseconds) == 0
    except Exception:
        logger.exception("timeBeginPeriod failed")
        return False


def end(milliseconds: int = 1) -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.winmm.timeEndPeriod(milliseconds)
    except Exception:
        logger.exception("timeEndPeriod failed")
