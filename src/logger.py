"""Centralized logging configuration for InvoiceProcessingAutomationBot.

Provides simultaneous output to console (stdout for CLI & UiPath) and rotating
log files for audit compliance.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import DEFAULT_LOG_FILE, LOGS_DIR


def setup_logger(log_file: Path | str = DEFAULT_LOG_FILE, level: int = logging.INFO) -> logging.Logger:
    """Configures and returns the application logger.

    Args:
        log_file: Path to the output log file.
        level: Minimum logging level (default: logging.INFO).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger("InvoiceProcessingBot")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logger is invoked multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (stdout for terminal & UiPath output capture)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (rotating file handler with 5MB max size, 5 backups)
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
