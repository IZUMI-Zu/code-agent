"""
═══════════════════════════════════════════════════════════════
Logging Configuration
═══════════════════════════════════════════════════════════════
"""

import logging
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

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(rich_tracebacks=True, markup=True),
            logging.FileHandler(log_dir / "agent.log", encoding="utf-8"),
        ],
    )

    logger = logging.getLogger(name)
    return logger


# Global logger instance
logger = setup_logger()
