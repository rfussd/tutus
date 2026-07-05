from __future__ import annotations

import logging
import sys


def setup_logger(name: str = "tutus") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "[%(name)s] %(levelname)s %(message)s",
            )
        )
        logger.addHandler(handler)

    return logger


log: logging.Logger = setup_logger("tutus")
