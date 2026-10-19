import logging
import os
from logging.handlers import RotatingFileHandler

from core.storage.paths import user_data_dir


def setup_logging():
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    try:
        log_dir = user_data_dir()
        os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(log_dir, "hac.log"), maxBytes=256 * 1024, backupCount=2, encoding="utf-8"
        )
        logging.basicConfig(level=logging.INFO, format=fmt, handlers=[handler])
    except OSError:
        logging.basicConfig(level=logging.INFO, format=fmt)


if __name__ == "__main__":
    setup_logging()
    from gui.app import HACApp

    app = HACApp()
    app.run()
