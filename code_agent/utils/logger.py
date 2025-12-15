"""
Logging Configuration
"""

import logging
from datetime import datetime
from pathlib import Path

from rich.logging import RichHandler


def setup_logger(name: str = "code_agent", level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger instance.

    Features:
    - Console output using RichHandler for pretty printing
    - File output for detailed logs
    """

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Generate log filename with date
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"agent_{current_date}.log"

    # Define handlers
    # Console: Only show warnings and errors to avoid messing up the TUI
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
    console_handler.setLevel(logging.WARNING)

    # File: Log everything for debugging
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Includes: Timestamp, Logger Name, Level, Source File:Line, Message
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    # We set the root level to DEBUG so the file handler receives everything
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[console_handler, file_handler],
    )

    # Suppress noisy libraries
    logging.getLogger("markdown_it").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    logger = logging.getLogger(name)
    return logger


# Global logger instance
logger = setup_logger()
