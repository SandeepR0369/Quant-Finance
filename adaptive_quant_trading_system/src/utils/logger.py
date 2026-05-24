"""Logging setup for the project."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file: str = 'logs/project.log'):
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh = RotatingFileHandler(log_file, maxBytes=10_000_00, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)
